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
import asyncio
from datetime import datetime, timedelta
import re
from dotenv import load_dotenv
import os
from tw_map import render_map
from tw_db import search_own_db, delete_from_db, search_db, add_db_entry, init_db

load_dotenv()

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.environ.get('TELEGRAM_API_TOKEN'))

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

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
    await types.ChatActions.upload_photo()
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
        # async with state.proxy() as data:
        #     data['selection'] = results
        await state.update_data(selection=results)
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
    await state.update_data(type=message.text)
    await SearchForm.next()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("Offer", "Search")
    markup.add("All")
    await message.reply("Do you search for an offer?", reply_markup=markup)

@dp.message_handler(lambda message: message.text not in ["Food", "Skill", "Thing", "All"], state=SearchForm.type)
async def process_search_type_invalid(message: types.Message):
    return await message.reply("Bad type. Choose your type from the keyboard.")

async def do_search_entries(message, data, state):
    results = await search_db(message.from_user.id, data['type'], data['kind'], data['location'], data['distance'])
    if len(results) > 0:
        data['selection'] = results
        await SearchForm.next()
        await message.reply("Found %s entries! Details:" % len(results))
        await show_results(bot, message, results)
        await message.reply("Pick one by entering its #.")
    else:
        await message.reply("Found nothing! Consider creating a search entry.")
        await state.finish()

@dp.message_handler(state=SearchForm.kind)
async def process_search_kind(message: types.Message, state: FSMContext):
    await state.update_data(kind=message.text)
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
    await state.update_data(kind=message.text)
    await AddForm.next()
    await message.reply("Where is that %s?" % message.text, reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda message: message.text not in ["Offer", "Search"], state=AddForm.kind)
async def process_add_kind_invalid(message: types.Message):
    return await message.reply("Bad offer type. Choose your offer type from the keyboard.")

@dp.message_handler(state=AddForm.type)
async def process_add_type(message: types.Message, state: FSMContext):
    await state.update_data(type=message.text)
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
        await AddForm.next()
        await message.reply("Please describe %s." % data['type'])

@dp.message_handler(content_types=ContentType.ANY, state=AddForm.location)
async def process_add_location_invalid(message: types.Message, state: FSMContext):
    return await message.reply("Bad location. Please share a location.")

@dp.message_handler(state=AddForm.description)
async def process_add_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
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

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())

    executor.start_polling(dp, skip_updates=True)
