import logging
import asyncio
import re
import os
import i18n
from datetime import datetime, timedelta
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext, filters
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor
import aiogram.utils.markdown as md
from aiogram.types.message import ContentType

from tw_map import render_map
from tw_db import search_db_entry, delete_db_entry, search_db_own_entry, add_db_entry, init_db, add_db_subscription, search_db_subscriptions, search_db_own_subscriptions, delete_db_subscription

load_dotenv()
i18n.load_path.append('translations')
i18n.set('enable_memoization', True)
i18n.set('fallback', 'en')

def _(key, **kwargs):
    return i18n.t(f'tw_bot.{key}', **kwargs)

def search_i18n_key(text, keys):
    for k in keys:
        if _(k) == text:
            return k
    return None

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.environ.get('TELEGRAM_API_TOKEN'))

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

def format_expires_at(expires):
    expires_str = None
    expires_at = re.search(r"([0-9]{4})([0-9]{2})([0-9]{2})", expires)
    if expires_at.group(1) == '9999':
        expires_str = _('add_expiration_never')
    else:
        expires_str = '%s.%s.%s' % (expires_at.group(3), expires_at.group(2), expires_at.group(1))
    return expires_str

def clean_for_md(s):
    return re.sub(r'([\!\.\(\)\=])', r'\\\g<1>', s)
    
async def show_results(bot, message, results):
    num = 1
    locations = []
    for result in results:
        expires_str = format_expires_at(result[9])
        locations.append((result[5], result[6]))
        await bot.send_message(
            message.chat.id,
            md.text(
                md.text('\\#', md.bold(num)),
                md.text(md.bold(_('type') + ':'), _(result[3]) + ' \\- ' + _(result[4])),
                md.text(md.bold(_('expires_at') + ':'), clean_for_md(expires_str)),
                md.text(md.bold(_('description') + ':')),
                md.text(clean_for_md(result[7])),
                sep='\n',
            ),
            reply_markup=types.ReplyKeyboardRemove(),
            parse_mode='MarkdownV2'#ParseMode.MARKDOWN,
        )
        num += 1
    await types.ChatActions.upload_photo()
    map = await render_map(locations)
    await message.answer_photo(map, _('map_locations'))

async def show_subscriptions(bot, message, results):
    num = 1
    locations = []
    for result in results:
        if result[5] is not None:
            locations.append((result[5], result[6]))
        await bot.send_message(
            message.chat.id,
            md.text(
                md.text('\\#', md.bold(num)),
                md.text(md.bold(_('type') + ':'), _(result[3]) + ' \\- ' + _(result[4])),
                sep='\n',
            ),
            reply_markup=types.ReplyKeyboardRemove(),
            parse_mode='MarkdownV2'#ParseMode.MARKDOWN,
        )
        num += 1
    if len(locations) > 0:
        await types.ChatActions.upload_photo()
        map = await render_map(locations)
        await message.answer_photo(map, _('map_locations'))

@dp.message_handler(state='*', commands=['cancel', 'c'])
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    logging.info('Cancelling state %r', current_state)
    await state.finish()
    i18n.set('locale', message.from_user.locale.language)
    await message.reply(_('cancel_state'), reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(commands=['list', 'l'])
async def cmd_list(message: types.Message, state: FSMContext):
    results = await search_db_own_entry(message.from_user.id)
    i18n.set('locale', message.from_user.locale.language)
    if len(results) > 0:
        await show_results(bot, message, results)
    else:
        await message.answer(_('no_entries_found'))

class DeleteSubscriptionForm(StatesGroup):
    selection = State()

@dp.message_handler(commands=['delete_subscription', 'ds'])
async def cmd_delete_subscription(message: types.Message, state: FSMContext):
    results = await search_db_own_subscriptions(message.from_user.id)
    i18n.set('locale', message.from_user.locale.language)
    #await DeleteSubscriptionForm.selection.set()
    if len(results) > 0:
        await state.update_data(selection=results)
        await show_subscriptions(bot, message, results)
        await DeleteSubscriptionForm.next()
        await message.answer(_('delete_which'))
    else:
        await message.answer(_('no_entries_found'))
        await state.finish()

class DeleteForm(StatesGroup):
    selection = State()

@dp.message_handler(commands=['delete', 'd'])
async def cmd_delete(message: types.Message, state: FSMContext):
    results = await search_db_own_entry(message.from_user.id)
    i18n.set('locale', message.from_user.locale.language)
    #await DeleteForm.selection.set()
    if len(results) > 0:
        await state.update_data(selection=results)
        await show_results(bot, message, results)
        await DeleteForm.next()
        await message.answer(_('delete_which'))
    else:
        await message.answer(_('no_entries_found'))
        await state.finish()

async def process_delete_selection_meta(message: types.Message, state: FSMContext, func):
    i18n.set('locale', message.from_user.locale.language)
    async with state.proxy() as data:
        sel = int(message.text) - 1
        if sel >= 0 and sel < len(data['selection']):
            result = data['selection'][sel]
            result_uid = result[0]
            func(result_uid)
            await message.answer(_('delete_success', index=str(sel + 1)))
            await state.finish()
        else:
            max = len(data['selection'])
            return await message.answer(_('invalid_selection', max=str(max)))

@dp.message_handler(lambda message: message.text.isdigit(), state=DeleteForm.selection)
async def process_delete_selection(message: types.Message, state: FSMContext):
    await process_delete_selection_meta(message, state, lambda uid: asyncio.get_running_loop().create_task(delete_db_entry(uid)))

@dp.message_handler(lambda message: message.text.isdigit(), state=DeleteSubscriptionForm.selection)
async def process_delete_subscription_selection(message: types.Message, state: FSMContext):
    await process_delete_selection_meta(message, state, lambda uid: asyncio.get_running_loop().create_task(delete_db_subscription(uid)))

@dp.message_handler(lambda message: not message.text.isdigit(), state=DeleteForm.selection)
@dp.message_handler(lambda message: not message.text.isdigit(), state=DeleteSubscriptionForm.selection)
async def process_delete_selection_invalid(message: types.Message, state: FSMContext):
    i18n.set('locale', message.from_user.locale.language)
    max = 0
    async with state.proxy() as data:
        max = len(data['selection'])
    return await message.answer(_('invalid_selection', max=str(max)))

class SearchForm(StatesGroup):
    type = State()
    kind = State()
    distance = State()
    location = State()
    selection = State()
    
@dp.message_handler(commands=['search', 's'])
async def cmd_search(message: types.Message):
    i18n.set('locale', message.from_user.locale.language)
    await SearchForm.type.set()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(_('food'), _('thing'), _('clothes'), _('skill'))
    markup.add(_('all'))
    await message.answer(_('search_what_type'), reply_markup=markup)

class SubscribeForm(StatesGroup):
    type = State()
    kind = State()
    distance = State()
    location = State()
    
@dp.message_handler(commands=['subscribe', 'sub', 'add_subscription', 'as'])
async def cmd_subscribe(message: types.Message):
    i18n.set('locale', message.from_user.locale.language)
    await SubscribeForm.type.set()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(_('food'), _('thing'), _('clothes'), _('skill'))
    markup.add(_('all'))
    await message.answer(_('subscribe_what_type'), reply_markup=markup)

async def subscribe_entries(message, data, state):
    await add_db_subscription(message.from_user.id, message.from_user.locale.language, data['type'], data['kind'], data['location'], data['distance'])
    await message.answer(_('subscribe_success'), reply_markup=types.ReplyKeyboardRemove())
    await state.finish()

@dp.message_handler(commands=['list_subscriptions', 'ls'])
async def cmd_list(message: types.Message, state: FSMContext):
    results = await search_db_own_subscriptions(message.from_user.id)
    i18n.set('locale', message.from_user.locale.language)
    if len(results) > 0:
        await show_subscriptions(bot, message, results)
    else:
        await message.answer(_('no_entries_found'))

async def preprocess_search_type(message, state):
    i18n.set('locale', message.from_user.locale.language)
    i18n_key = search_i18n_key(message.text, ['food', 'thing', 'clothes', 'skill', 'all'])
    if not i18n_key:
        return await message.answer(_('invalid_type'))
    await state.update_data(type=i18n_key)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(_('offer'), _('search'))
    markup.add(_('all'))
    return markup

@dp.message_handler(state=SubscribeForm.type)
async def process_subscription_type(message: types.Message, state: FSMContext):
    markup = await preprocess_search_type(message, state)
    await SubscribeForm.next()
    await message.answer(_('subscribe_what_kind'), reply_markup=markup)

@dp.message_handler(state=SearchForm.type)
async def process_search_type(message: types.Message, state: FSMContext):
    markup = await preprocess_search_type(message, state)
    await SearchForm.next()
    await message.answer(_('search_what_kind'), reply_markup=markup)

async def search_entries(message, data, state):
    i18n.set('locale', message.from_user.locale.language)
    results = await search_db_entry(message.from_user.id, data['type'], data['kind'], data['location'], data['distance'])
    if len(results) > 0:
        data['selection'] = results
        await SearchForm.next()
        await message.answer(_('search_found_sth', count=str(len(results))) + ':', reply_markup=types.ReplyKeyboardRemove())
        await show_results(bot, message, results)
        await message.answer(_('search_pick_one'))
    else:
        await message.answer(_('search_no_entries_found'), reply_markup=types.ReplyKeyboardRemove())
        await state.finish()

async def preprocess_search_kind(message, state):
    i18n.set('locale', message.from_user.locale.language)
    i18n_key = search_i18n_key(message.text, ['offer', 'search', 'all'])
    if not i18n_key:
        return await message.answer(_('invalid_kind'))
    await state.update_data(kind=i18n_key)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add('5', '10', '50', '100')
    markup.add(_('search_everywhere'))
    return markup

@dp.message_handler(state=SearchForm.kind)
async def process_search_kind(message: types.Message, state: FSMContext):
    markup = await preprocess_search_kind(message, state)
    await SearchForm.next()
    await message.answer(_('search_distance'), reply_markup=markup)

@dp.message_handler(state=SubscribeForm.kind)
async def process_subscription_kind(message: types.Message, state: FSMContext):
    markup = await preprocess_search_kind(message, state)
    await SubscribeForm.next()
    await message.answer(_('subscribe_distance'), reply_markup=markup)

@dp.message_handler(state=SearchForm.distance)
async def process_search_distance(message: types.Message, state: FSMContext):
    i18n.set('locale', message.from_user.locale.language)
    async with state.proxy() as data:
        if message.text == _('search_everywhere'): 
            data['distance'] = 'search_everywhere'
            data['location'] = None
            await SearchForm.next()
            await search_entries(message, data, state)
        elif message.text.isdigit():
            data['distance'] = message.text        
            await SearchForm.next()
            await message.answer(_('search_location', type=_(data['type'])), reply_markup=types.ReplyKeyboardRemove())
        else:
            return await message.answer(_('invalid_distance'))

@dp.message_handler(state=SubscribeForm.distance)
async def process_subscription_distance(message: types.Message, state: FSMContext):
    i18n.set('locale', message.from_user.locale.language)
    async with state.proxy() as data:
        if message.text == _('search_everywhere'): 
            data['distance'] = 'search_everywhere'
            data['location'] = None
            await SubscribeForm.next()
            await subscribe_entries(message, data, state)
        elif message.text.isdigit():
            data['distance'] = message.text
            await SubscribeForm.next()
            await message.answer(_('subscribe_location', type=_(data['type'])), reply_markup=types.ReplyKeyboardRemove())
        else:
            return await message.answer(_('invalid_distance'))

@dp.message_handler(content_types=ContentType.LOCATION, state=SearchForm.location)
async def process_search_location(message: types.Message, state: FSMContext):
    i18n.set('locale', message.from_user.locale.language)
    async with state.proxy() as data:
        data['location'] = message.location
        await search_entries(message, data, state)

@dp.message_handler(content_types=ContentType.LOCATION, state=SubscribeForm.location)
async def process_subscription_location(message: types.Message, state: FSMContext):
    i18n.set('locale', message.from_user.locale.language)
    async with state.proxy() as data:
        data['location'] = message.location
        await subscribe_entries(message, data, state)

@dp.message_handler(content_types=ContentType.ANY, state=SearchForm.location)
@dp.message_handler(content_types=ContentType.ANY, state=SubscribeForm.location)
async def process_search_location_invalid(message: types.Message, state: FSMContext):
    return await message.answer(_('invalid_location'))

@dp.message_handler(lambda message: message.text.isdigit(), state=SearchForm.selection)
async def process_search_selection(message: types.Message, state: FSMContext):
    i18n.set('locale', message.from_user.locale.language)
    async with state.proxy() as data:
        sel = int(message.text) - 1
        if sel >= 0 and sel < len(data['selection']) + 1:
            result = data['selection'][sel]
            await message.answer(_('search_picked', index=str(sel + 1)) + '\n' + _('search_sent_notification'))
            user = str(message.from_user.id)
            link = f'[{message.from_user.mention}](tg://user?id={user})'
            i18n.set('locale', result[2])
            text = _('search_notification', desc=result[7], link=link)
            await bot.send_message(
                    result[1],
                    text,
                    parse_mode=ParseMode.MARKDOWN,
                )
            await state.finish()
        else:
            max = len(data['selection'])
            return await message.answer(_('invalid_selection', max=str(max)))

@dp.message_handler(lambda message: not message.text.isdigit(), state=SearchForm.selection)
async def process_search_selection_invalid(message: types.Message, state: FSMContext):
    max = 0
    async with state.proxy() as data:
        max = len(data['selection'])
    return await message.answer(_('invalid_selection', max=str(max)))

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
    i18n.set('locale', message.from_user.locale.language)
    markup.add(_('food'), _('thing'), _('clothes'), _('skill'))
    await message.answer(_('add_what_type'), reply_markup=markup)

@dp.message_handler(state=AddForm.type)
async def process_add_type(message: types.Message, state: FSMContext):
    i18n.set('locale', message.from_user.locale.language)
    i18n_key = search_i18n_key(message.text, ['food', 'thing', 'clothes', 'skill'])
    if not i18n_key:
        return await message.answer(_('invalid_type'))
    else:
        await state.update_data(type=i18n_key)
        await AddForm.next()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
        markup.add(_('offer'), _('search'))
        await message.answer(_('add_what_kind'), reply_markup=markup)

@dp.message_handler(state=AddForm.kind)
async def process_add_kind(message: types.Message, state: FSMContext):
    i18n.set('locale', message.from_user.locale.language)
    i18n_key = search_i18n_key(message.text, ['offer', 'search'])
    if not i18n_key:
        return await message.answer(_('invalid_kind'))
    else:   
        await state.update_data(kind=i18n_key)
        await AddForm.next()
        await message.answer(_('add_location', type=message.text), reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(content_types=ContentType.LOCATION, state=AddForm.location)
async def process_add_location(message: types.Message, state: FSMContext):
    i18n.set('locale', message.from_user.locale.language)
    async with state.proxy() as data:
        data['location'] = message.location
        await AddForm.next()
        await message.answer(_('add_describe', type=_(data['type'])))

@dp.message_handler(content_types=ContentType.ANY, state=AddForm.location)
async def process_add_location_invalid(message: types.Message, state: FSMContext):
    return await message.answer(_('invalid_location'))

@dp.message_handler(state=AddForm.description)
async def process_add_description(message: types.Message, state: FSMContext):
    i18n.set('locale', message.from_user.locale.language)
    desc = re.sub(r'[^A-Za-z0-9\.,;:!\(\)\s]', '', message.text)
    await state.update_data(description=desc)
    await AddForm.next()
    await message.answer(_('add_expiration'))

@dp.message_handler(state=AddForm.expires_at)
async def process_add_expires_at(message: types.Message, state: FSMContext):
    i18n.set('locale', message.from_user.locale.language)
    if not re.search(r'^([0-9]{1,2})\.([0-9]{1,2})\.([0-9]{4})$|^([0-9]+)$', message.text) and message.text.lower() != _('add_expiration_never').lower():
        return await message.answer(_('add_invalid_expiration'))

    expires_at = None
    expires_str = 'never'
    if message.text.lower() == _('add_expiration_never').lower():
        expires_at = datetime(9999, 12, 31, 23, 59, 59)
        expires_str = _('add_expiration_never')
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
                return await message.answer(_('add_invalid_expiration'))
            if expires_at < datetime.now():
                return await message.answer(_('add_invalid_future_expiration'))
        expires_str = expires_at.strftime("%d.%m.%Y")
    async with state.proxy() as data:
        await bot.send_message(
            message.chat.id,
            md.text(
                md.text(md.bold(_('add_thanks')), _('details') + ':'),
                md.text(md.bold(_('type') + ':'), _(data['type']) + ' \\- ' + _(data['kind'])),
                md.text(md.bold(_('location') + ':'), clean_for_md(str(data['location'].latitude)) + " / " + clean_for_md(str(data['location'].longitude))),
                md.text(md.bold(_('expires_at') + ':'), clean_for_md(expires_str)),
                md.text(md.bold(_('description') + ':')),
                md.text(clean_for_md(data['description'])),
                sep='\n',
            ),
            reply_markup=types.ReplyKeyboardRemove(),
            parse_mode='MarkdownV2'#ParseMode.MARKDOWN,
        )
        await add_db_entry(message.from_user.id, message.from_user.locale.language, data['type'], data['kind'], data['location'], data['description'], expires_at)
        subscriptions = await search_db_subscriptions(message.from_user.id, data['type'], data['kind'], data['location'])
        user_ids = []
        for sub in subscriptions:
            i18n.set('locale', sub[1])
            user = str(message.from_user.id)
            if not user in user_ids:
                user_ids.append(user)
                link = f'[{message.from_user.mention}](tg://user?id\={user})'
                msg = md.text(
                        md.text(_('subscription_incoming', link=link)),
                        md.text(md.bold(_('details') + ':')),
                        md.text(md.bold(_('type') + ':'), _(data['type']) + ' \\- ' + _(data['kind'])),
                        md.text(md.bold(_('description') + ':')),
                        md.text(clean_for_md(data['description'])),
                        sep='\n',
                    )
                await bot.send_message(
                    sub[0],
                    msg,
                    reply_markup=types.ReplyKeyboardRemove(),
                    parse_mode='MarkdownV2',#ParseMode.MARKDOWN,
                )
                await types.ChatActions.upload_photo()
                map = await render_map([(data['location'].latitude, data['location'].longitude)])
                await bot.send_photo(sub[0], map, _('map_locations'))
    await state.finish()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())

    executor.start_polling(dp, skip_updates=True)