import logging

import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext, filters
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.types.message import ContentType
import aiosqlite
import asyncio
from datetime import datetime, timedelta
import re
import staticmaps
import cairo
import s2sphere
import io
from dotenv import load_dotenv
import os

load_dotenv()

# https://github.com/flopp/py-staticmaps/blob/master/examples/custom_objects.py
class TextLabel(staticmaps.Object):
    def __init__(self, latlng: s2sphere.LatLng, text: str) -> None:
        staticmaps.Object.__init__(self)
        self._latlng = latlng
        self._text = text
        self._margin = 4
        self._arrow = 16
        self._font_size = 12

    def latlng(self) -> s2sphere.LatLng:
        return self._latlng

    def bounds(self) -> s2sphere.LatLngRect:
        return s2sphere.LatLngRect.from_point(self._latlng)

    def extra_pixel_bounds(self) -> staticmaps.PixelBoundsT:
        # Guess text extents.
        tw = len(self._text) * self._font_size * 0.5
        th = self._font_size * 1.2
        w = max(self._arrow, tw + 2.0 * self._margin)
        return (int(w / 2.0), int(th + 2.0 * self._margin + self._arrow), int(w / 2), 0)

    def render_pillow(self, renderer: staticmaps.PillowRenderer) -> None:
        x, y = renderer.transformer().ll2pixel(self.latlng())
        x = x + renderer.offset_x()

        tw, th = renderer.draw().textsize(self._text)
        w = max(self._arrow, tw + 2 * self._margin)
        h = th + 2 * self._margin

        path = [
            (x, y),
            (x + self._arrow / 2, y - self._arrow),
            (x + w / 2, y - self._arrow),
            (x + w / 2, y - self._arrow - h),
            (x - w / 2, y - self._arrow - h),
            (x - w / 2, y - self._arrow),
            (x - self._arrow / 2, y - self._arrow),
        ]

        renderer.draw().polygon(path, fill=(255, 255, 255, 255))
        renderer.draw().line(path, fill=(255, 0, 0, 255))
        renderer.draw().text((x - tw / 2, y - self._arrow - h / 2 - th / 2), self._text, fill=(0, 0, 0, 255))

    def render_cairo(self, renderer: staticmaps.CairoRenderer) -> None:
        x, y = renderer.transformer().ll2pixel(self.latlng())

        ctx = renderer.context()
        ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)

        ctx.set_font_size(self._font_size)
        x_bearing, y_bearing, tw, th, _, _ = ctx.text_extents(self._text)

        w = max(self._arrow, tw + 2 * self._margin)
        h = th + 2 * self._margin

        path = [
            (x, y),
            (x + self._arrow / 2, y - self._arrow),
            (x + w / 2, y - self._arrow),
            (x + w / 2, y - self._arrow - h),
            (x - w / 2, y - self._arrow - h),
            (x - w / 2, y - self._arrow),
            (x - self._arrow / 2, y - self._arrow),
        ]

        ctx.set_source_rgb(1, 1, 1)
        ctx.new_path()
        for p in path:
            ctx.line_to(*p)
        ctx.close_path()
        ctx.fill()

        ctx.set_source_rgb(1, 0, 0)
        ctx.set_line_width(1)
        ctx.new_path()
        for p in path:
            ctx.line_to(*p)
        ctx.close_path()
        ctx.stroke()

        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(1)
        ctx.move_to(x - tw / 2 - x_bearing, y - self._arrow - h / 2 - y_bearing - th / 2)
        ctx.show_text(self._text)
        ctx.stroke()

    def render_svg(self, renderer: staticmaps.SvgRenderer) -> None:
        x, y = renderer.transformer().ll2pixel(self.latlng())

        # guess text extents
        tw = len(self._text) * self._font_size * 0.5
        th = self._font_size * 1.2

        w = max(self._arrow, tw + 2 * self._margin)
        h = th + 2 * self._margin

        path = renderer.drawing().path(
            fill="#ffffff",
            stroke="#ff0000",
            stroke_width=1,
            opacity=1.0,
        )
        path.push(f"M {x} {y}")
        path.push(f" l {self._arrow / 2} {-self._arrow}")
        path.push(f" l {w / 2 - self._arrow / 2} 0")
        path.push(f" l 0 {-h}")
        path.push(f" l {-w} 0")
        path.push(f" l 0 {h}")
        path.push(f" l {w / 2 - self._arrow / 2} 0")
        path.push("Z")
        renderer.group().add(path)

        renderer.group().add(
            renderer.drawing().text(
                self._text,
                text_anchor="middle",
                dominant_baseline="central",
                insert=(x, y - self._arrow - h / 2),
                font_family="sans-serif",
                font_size=f"{self._font_size}px",
                fill="#000000",
            )
        )

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.environ.get('TELEGRAM_API_TOKEN'))

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

async def render_map(locations):
    context = staticmaps.Context()
    context.set_tile_provider(staticmaps.tile_provider_OSM)

    num = 1
    for loc in locations:
        poi = staticmaps.create_latlng(loc[0], loc[1])
        context.add_object(TextLabel(poi, str(num)))
        num += 1
    
    image = context.render_cairo(800, 500)
    png_bytes = io.BytesIO()
    image.write_to_png(png_bytes)
    png_bytes.flush()
    png_bytes.seek(0)
    return png_bytes

def format_expires_at(expires):
    expires_str = None
    expires_at = re.search(r"([0-9]{4})([0-9]{2})([0-9]{2})", expires)
    if expires_at.group(1) == '9999':
        expires_str = 'never'
    else:
        expires_str = '%s.%s.%s' % (expires_at.group(3), expires_at.group(2), expires_at.group(1))
    return expires_str

async def show_results(bot, message, results):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardRemove()
    num = 1
    locations = []
    for result in results:
        expires_str = format_expires_at(result[8])
        locations.append((result[4], result[5]))
        await bot.send_message(
            chat_id,
            md.text(
                md.text('#', md.bold(num)),
                md.text('Type:', md.bold(result[2])),
                md.text('Kind:', md.bold(result[3])),
                md.text('Expires at:', md.bold(expires_str)),
                md.text('Description:'),
                md.text(md.bold(result[6])), #todo send dots unescaped, those are interpreted as MD -.-
                sep='\n',
            ),
            reply_markup=markup,
            parse_mode=ParseMode.MARKDOWN,
        )
        num += 1
    map = await render_map(locations)
    await message.reply_photo(map, "Result locations")

@dp.message_handler(state='*', commands=['cancel', 'c'])
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    logging.info('Cancelling state %r', current_state)
    await state.finish()
    await message.reply('Cancelled.', reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(commands=['list', 'l'])
async def cmd_list(message: types.Message, state: FSMContext):
    results = await search_own_db(message.from_user.id)
    if len(results) > 0:
        await show_results(bot, message, results)
    else:
        await message.reply("Could not find any entries.")

class DeleteForm(StatesGroup):
    selection = State()

@dp.message_handler(commands=['delete', 'd'])
async def cmd_delete(message: types.Message, state: FSMContext):
    results = await search_own_db(message.from_user.id)
    if len(results) > 0:
        async with state.proxy() as data:
            data['selection'] = results
        await show_results(bot, message, results)
        await DeleteForm.next()
        await message.reply("Which entry do you want to delete?")
    else:
        await message.reply("Could not find any entries.")
        await state.finish()

@dp.message_handler(lambda message: message.text.isdigit(), state=DeleteForm.selection)
async def process_delete_selection(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        sel = int(message.text) - 1
        if sel >= 0 and sel < len(data['selection']) + 1:
            result = data['selection'][sel]
            result_uid = result[0]
            await delete_from_db(result_uid)
            await bot.send_message(
                    message.chat.id,
                    md.text(
                        md.text('Entry #', md.bold(str(sel + 1)), ' was successfully deleted.'),
                        sep='\n',
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
            await state.finish()
        else:
            max = len(data['selection'])
            return await message.reply("Bad selection index. Insert a number from 1 to " + str(max))

@dp.message_handler(lambda message: not message.text.isdigit(), state=DeleteForm.selection)
async def process_delete_selection_invalid(message: types.Message, state: FSMContext):
    max = 0
    async with state.proxy() as data:
        max = len(data['selection'])
    return await message.reply("Bad selection index. Insert a number from 1 to " + str(max))

class SearchForm(StatesGroup):
    type = State()
    kind = State()
    distance = State()
    location = State()
    selection = State()
    
@dp.message_handler(commands=['search', 's'])
async def cmd_search(message: types.Message):
    await SearchForm.type.set()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("Food", "Thing", "Skill")
    markup.add("All")
    await message.reply("What type of thing do you want to search?", reply_markup=markup)

@dp.message_handler(state=SearchForm.type)
async def process_search_type(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['type'] = message.text
    
    await SearchForm.next()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("Offer", "Search")
    markup.add("All")
    await message.reply("Do you search for an offer?", reply_markup=markup)

@dp.message_handler(lambda message: message.text not in ["Food", "Skill", "Thing", "All"], state=SearchForm.type)
async def process_search_type_invalid(message: types.Message):
    return await message.reply("Bad type. Choose your type from the keyboard.")

async def do_search_entries(message, data, state):
    markup = types.ReplyKeyboardRemove()
    results = await search_db(message.from_user.id, data['type'], data['kind'], data['location'], data['distance'])
    if len(results) > 0:
        data['selection'] = results
        await SearchForm.next()
        await bot.send_message(
                message.chat.id,
                md.text(
                    md.text("Found %s entries! Details:" % len(results)),
                    sep='\n',
                ),
                reply_markup=markup,
                parse_mode=ParseMode.MARKDOWN,
            )
        await show_results(bot, message, results)
        await message.reply("Pick one by entering its #.")
    else:
        await bot.send_message(
            message.chat.id,
            md.text(
                md.text('Found nothing! Consider creating a search entry.'),
                sep='\n',
            ),
            reply_markup=markup,
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.finish()

@dp.message_handler(state=SearchForm.kind)
async def process_search_kind(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['kind'] = message.text
    await SearchForm.next()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("Everywhere")
    markup.add("5", "10", "50", "100")
    await message.reply("Do you want to search within a specific distance (in kilometers)?", reply_markup=markup)

@dp.message_handler(lambda message: message.text not in ["Offer", "Search", "All"], state=SearchForm.kind)
async def process_search_kind_invalid(message: types.Message):
    return await message.reply("Bad offer type. Choose your offer type from the keyboard.")

@dp.message_handler(state=SearchForm.distance)
async def process_search_distance(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['distance'] = message.text
        if message.text == 'Everywhere':
            data['location'] = None
            await SearchForm.next()
            await do_search_entries(message, data, state)
        else:
            await SearchForm.next()
            await message.reply("Where are you searching for %s?" % data['type'], reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda message: not message.text.isdigit() or message != 'Everywhere', state=SearchForm.distance)
async def process_search_distance_invalid(message: types.Message, state: FSMContext):
    return await message.reply("Bad distance. Please enter a number of kilometers.")

@dp.message_handler(content_types=ContentType.LOCATION, state=SearchForm.location)
async def process_search_location(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['location'] = message.location
        await do_search_entries(message, data, state)

@dp.message_handler(lambda message: message.text.isdigit(), state=SearchForm.selection)
async def process_search_selection(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        sel = int(message.text) - 1
        if sel >= 0 and sel < len(data['selection']) + 1:
            result = data['selection'][sel]
            await bot.send_message(
                message.chat.id,
                md.text(
                    md.text('You picked #',  md.bold(str(sel + 1))),
                    md.text('I sent a notification to the user that entered that offer.', ),
                    sep='\n',
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
            user = str(message.from_user.id)
            link = f'[{message.from_user.mention}](tg://user?id={user})'
            text = f'{result[6]} was selected by user {link}'
            await bot.send_message(
                    result[1],
                    text,
                    parse_mode=ParseMode.MARKDOWN,
                )
            await state.finish()
        else:
            max = len(data['selection'])
            return await message.reply("Bad selection index. Insert a number from 1 to " + str(max))

@dp.message_handler(lambda message: not message.text.isdigit(), state=SearchForm.selection)
async def process_search_selection_invalid(message: types.Message, state: FSMContext):
    max = 0
    async with state.proxy() as data:
        max = len(data['selection'])
    return await message.reply("Bad selection index. Insert a number from 1 to " + str(max))

class AddForm(StatesGroup):
    type = State()
    kind = State()
    location = State()
    description = State()
    expires_at = State()

@dp.message_handler(commands=['add', 'a'])
async def cmd_add(message: types.Message):
    await AddForm.type.set()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("Food", "Thing", "Skill")
    await message.reply("What type of thing do you want to share?", reply_markup=markup)

@dp.message_handler(state=AddForm.kind)
async def process_add_kind(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['kind'] = message.text
    await AddForm.next()
    await message.reply("Where is that %s?" % message.text, reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda message: message.text not in ["Offer", "Search"], state=AddForm.kind)
async def process_add_kind_invalid(message: types.Message):
    return await message.reply("Bad offer type. Choose your offer type from the keyboard.")

@dp.message_handler(state=AddForm.type)
async def process_add_type(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['type'] = message.text
    await AddForm.next()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("Offer", "Search")
    await message.reply("Do you want to offer it or are you searching?", reply_markup=markup)

@dp.message_handler(lambda message: message.text not in ["Food", "Skill", "Thing"], state=AddForm.type)
async def process_add_type_invalid(message: types.Message):
    return await message.reply("Bad type. Choose your type from the keyboard.")

@dp.message_handler(content_types=ContentType.LOCATION, state=AddForm.location)
async def process_add_location(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['location'] = message.location
    #await state.update_data(location=)
    await AddForm.next()
    await message.reply("Please describe %s." % data['type'])

@dp.message_handler(content_types=ContentType.ANY, state=AddForm.location)
async def process_add_location_invalid(message: types.Message, state: FSMContext):
    return await message.reply("Bad location. Please share a location.")

@dp.message_handler(state=AddForm.description)
async def process_add_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['description'] = message.text
    await AddForm.next()
    await message.reply("Please enter a expiration date in DD.MM.YYYY format or a number of days or 'never'.")

@dp.message_handler(filters.Regexp('^([0-9]{1,2})\.([0-9]{1,2})\.([0-9]{4})$|^([0-9]+)$|^never$|^Never$'), state=AddForm.expires_at)
async def process_add_expires_at(message: types.Message, state: FSMContext):
    expires_at = None
    expires_str = 'never'
    if message.text == 'never':
        expires_at = datetime(9999, 12, 31, 23, 59, 59)
    else:
        timespan = re.search(r"^([0-9]+)$", message.text)
        if timespan:
            expires_at = datetime.now() + timedelta(days = int(timespan.group(1)))
        else:
            res = re.search(r"([0-9]{1,2})\.([0-9]{1,2})\.([0-9]{4})", message.text)
            yyyy = int(res.group(3))
            mm = int(res.group(2))
            dd = int(res.group(1))
            try:
                expires_at = datetime(yyyy, mm, dd, 23, 59, 59)
            except ValueError:
                await message.reply("Please enter a valid expiration date in DD.MM.YYYY format or a number of days or 'never'.")
                return
            if expires_at < datetime.now():
                await message.reply("Please enter a valid future expiration date in DD.MM.YYYY format or a number of days or 'never'.")
                return
        expires_str = expires_at.strftime("%d.%m.%Y")
    async with state.proxy() as data:
        markup = types.ReplyKeyboardRemove()
        await bot.send_message(
            message.chat.id,
            md.text(
                md.text('Thanks for sharing! Details:'),
                md.text('Type:', md.bold(data['type'])),
                md.text('Kind:', md.bold(data['kind'])),
                md.text('Location:', md.bold(data['location'])),
                md.text('Expires at:', md.bold(expires_str)),
                md.text('Description:', md.bold(data['description'])),
                sep='\n',
            ),
            reply_markup=markup,
            parse_mode=ParseMode.MARKDOWN,
        )
        await add_db_entry(message.from_user.id, data['type'], data['kind'], data['location'], data['description'], expires_at)
    await state.finish()

@dp.message_handler(state=AddForm.expires_at)
async def process_add_expires_at_invalid(message: types.Message, state: FSMContext):
    return await message.reply("Bad date. Please enter it in DD.MM.YYYY format or a number of days or 'never'.")

DB = 'db.sqlite'

async def search_db(user_id, type, kind, location, distance):
    curdate = str(datetime.now().strftime('%Y%m%d'))
    query = "SELECT * FROM geteilt where expires_at > " + curdate
    query += " AND user_id <> " + str(user_id) 
    if type != 'All':
        query += " AND type = " + type
    if kind != 'All':
        query += " AND kind = " + kind

    if location is not None:
        dist = int(distance) * 1000
        query += " AND (PtDistWithin(geteilt.latlng, PointFromText('POINT(" + str(location.longitude) + " " + str(location.latitude) + ")', 4326), " + str(dist) + ")=TRUE)"
        
    query += ";"
    res = []
    async with aiosqlite.connect(DB) as db:
        await db.enable_load_extension(True)
        await db.load_extension('mod_spatialite')
        async with db.execute(query) as cursor:
            async for row in cursor:
                res.append(row)
    return res

async def delete_from_db(entry_uid):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM geteilt WHERE id = " + str(entry_uid) + ";")
        await db.commit()

async def search_own_db(user_id):
    query = "SELECT * FROM geteilt where user_id = " + str(user_id) + ";"
    res = []
    async with aiosqlite.connect(DB) as db:
        async with db.execute(query) as cursor:
            async for row in cursor:
                res.append(row)
    return res

async def add_db_entry(user_id, type, kind, location, description, expires_at):
    currentDateTime = datetime.now().strftime('%Y%m%d')
    async with aiosqlite.connect(DB) as db:
        await db.enable_load_extension(True)
        await db.execute("SELECT load_extension('mod_spatialite');")
        last_row = None
        async with db.execute("INSERT INTO geteilt(user_id, type, kind, lat, lng, desc, inserted_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?);", 
                (user_id, type, kind, location.latitude, location.longitude, 
                description, currentDateTime, str(expires_at.strftime('%Y%m%d')))) as cursor:
            last_row = cursor.lastrowid
        await db.execute("UPDATE geteilt SET latlng = PointFromText('POINT(" + str(location.longitude) + " " + str(location.latitude) + ")', 4326) WHERE id = " + str(last_row) + ";")
        await db.commit()

async def check_point_col_exists(db):
    point_col_exists = False
    async with db.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'geteilt';") as cursor:
        async for row in cursor:
            point_col_exists = 'POINT' in row[0]
    return point_col_exists

async def init_db():
    async with aiosqlite.connect(DB) as db:
        point_col_exists = await check_point_col_exists(db)
        if not point_col_exists:
            await db.enable_load_extension(True)
            await db.execute("SELECT load_extension('mod_spatialite');")
            await db.execute("SELECT InitSpatialMetaData();")
            await db.execute("""CREATE TABLE IF NOT EXISTS geteilt (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type VARCHAR(10),
                kind VARCHAR(10),
                lat FLOAT,
                lng FLOAT,
                desc TEXT,
                inserted_at text,
                expires_at text
                );""")
            await db.execute("SELECT AddGeometryColumn('geteilt', 'latlng', 4326, 'POINT', 'XY');")
            await db.execute("SELECT CreateSpatialIndex('geteilt', 'latlng');")
            await db.commit()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())

    executor.start_polling(dp, skip_updates=True)
