import io

from telegram import ParseMode
from telegram import ReplyKeyboardRemove
from telegram.error import TelegramError
from telegram.ext import ConversationHandler

from .enums import logger, BOT_STATE_INIT, ADMIN_BOT_SETTINGS, ADMIN_ADD_DELIVERY_FEE, ADMIN_TXT_PRODUCT_TITLE, \
    ADMIN_ORDER_OPTIONS, ADMIN_ADD_DISCOUNT, ADMIN_EDIT_IDENTIFICATION, \
    ADMIN_EDIT_RESTRICTION, ADMIN_EDIT_WELCOME_MESSAGE, ADMIN_EDIT_ORDER_DETAILS, ADMIN_EDIT_FINAL_MESSAGE, \
    ADMIN_TXT_PRODUCT_PRICES, ADMIN_TXT_PRODUCT_PHOTO, ADMIN_INIT, ADMIN_TXT_COURIER_NAME, ADMIN_TXT_DELETE_COURIER, \
    ADMIN_TXT_COURIER_ID, ADMIN_COURIERS, ADMIN_TXT_COURIER_LOCATION, ADMIN_CHANNELS, ADMIN_CHANNELS_ADDRESS, \
    ADMIN_CHANNELS_SELECT_TYPE, ADMIN_CHANNELS_REMOVE, ADMIN_BAN_LIST, ADMIN_LOCATIONS, ADMIN_TXT_ADD_LOCATION, \
    ADMIN_TXT_DELETE_LOCATION, ADMIN_PRODUCTS, ADMIN_PRODUCT_ADD, ADMIN_PRODUCT_LAST_ADD, ADMIN_DELETE_PRODUCT
from .helpers import session_client, get_config_session, get_user_id, set_config_session, config, get_trans
from .models import Product, ProductCount, Courier, Location, CourierLocation
from .keyboards import create_back_button, create_bot_couriers_keyboard, create_bot_channels_keyboard, \
    create_bot_settings_keyboard, create_bot_order_options_keyboard, \
    create_ban_list_keyboard, create_courier_locations_keyboard, create_bot_locations_keyboard, \
    create_locations_keyboard, create_bot_products_keyboard, create_bot_product_add_keyboard, \
    create_select_products_chunk_keyboard

from . import shortcuts

from . import messages


def is_admin(bot, user_id):
    chat_id = config.get_service_channel()

    try:
        member = bot.getChatMember(chat_id, user_id)
        if member.status == 'left':
            return False
        else:
            return True
    except TelegramError as e:
        logger.error("Failed to check admin id: %s", e)
        return False


def on_start_admin(bot, update):
    user_id = get_user_id(update)
    if not is_admin(bot, user_id):
        _ = get_trans(user_id)
        logger.info(_('User %s, @%s rejected (not admin)'),
                    update.message.from_user.id,
                    update.message.from_user.username)
        update.message.reply_text(text=_(
            'Sorry {}, you are not authorized to administrate this bot').format(
            update.message.from_user.first_name))
        return BOT_STATE_INIT


def on_admin_cmd_add_product(bot, update):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    update.message.reply_text(
        text=_('Enter new product title'),
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ADMIN_TXT_PRODUCT_TITLE


def on_admin_order_options(bot, update):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if data == 'bot_order_options_back':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('⚙ Bot settings'),
                              reply_markup=create_bot_settings_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_BOT_SETTINGS
    if data == 'bot_order_options_product':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('🏪 Products'),
                              reply_markup=create_bot_products_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_PRODUCTS
    elif data == 'bot_order_options_discount':
        bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            text=('Enter discount like:\n'
                  '50 > 500: all deals above 500$ will be -100$\n'
                  '10% > 500: all deals above 500% will be -10%\n'
                  'Current discount: {}'.format(config.get_discount())),
            reply_markup=create_back_button(_),
            parse_mode=ParseMode.MARKDOWN,
        )
        query.answer()
        return ADMIN_ADD_DISCOUNT
    elif data == 'bot_order_options_delivery_fee':
        bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            text=(
                _('Enter delivery fee:\nOnly works on delivery\n\nCurrent fee: {}').format(config.get_delivery_fee())),
            reply_markup=create_back_button(_),
            parse_mode=ParseMode.MARKDOWN,
        )
        query.answer()
        return ADMIN_ADD_DELIVERY_FEE
    elif data == 'bot_order_options_add_locations':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('🎯 Locations'),
                              reply_markup=create_bot_locations_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_LOCATIONS
    elif data == 'bot_order_options_identify':
        first = config.get_identification_required()
        second = config.get_identification_stage2_required()
        question = config.get_identification_stage2_question()
        first = 'Enabled' if first else 'Disabled'
        second = 'Enabled' if second else 'Disabled'
        msg = 'First stage: {}\n' \
              'Second stage: {}\n' \
              'Identification question:{}\n' \
              'Enter like this: 0/1 0/1 text (first, second, question)' \
              ''.format(first, second, question)
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_back_button(_),
                              parse_mode=ParseMode.MARKDOWN)
        return ADMIN_EDIT_IDENTIFICATION
    elif data == 'bot_order_options_restricted':
        only_for_customers = 'Enabled' if config.get_only_for_customers() \
            else 'Disabled'
        only_for_vip_customers = 'Enabled' if config.get_vip_customers() \
            else 'Disabled'
        msg = 'Only for customers option: {}\n' \
              'Vip customers option: {}\n' \
              'Type new rules: 0/1 0/1 (customers, vip customers)'.format(only_for_customers, only_for_vip_customers)
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_back_button(_),
                              parse_mode=ParseMode.MARKDOWN)
        return ADMIN_EDIT_RESTRICTION
    elif data == 'bot_order_options_welcome':
        msg = _('Type new welcome message.\n')
        msg += _('Current message:\n\n{}').format(config.get_welcome_text())
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_back_button(_),
                              parse_mode=ParseMode.MARKDOWN)
        return ADMIN_EDIT_WELCOME_MESSAGE
    elif data == 'bot_order_options_details':
        msg = _('Type new order details message.\n')
        msg += _('Current message:\n\n{}').format(config.get_order_text())
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_back_button(_),
                              parse_mode=ParseMode.MARKDOWN)
        return ADMIN_EDIT_ORDER_DETAILS
    elif data == 'bot_order_options_final':
        msg = _('Type new final message.\n')
        msg += _('Current message:\n\n{}').format(config.get_order_complete_text())
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_back_button(_),
                              parse_mode=ParseMode.MARKDOWN)
        return ADMIN_EDIT_FINAL_MESSAGE

    return ConversationHandler.END

def on_admin_products(bot, update):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    if data == 'bot_products_back':
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text = _('💳 Order options'),
                              reply_markup=create_bot_order_options_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_ORDER_OPTIONS
    elif data == 'bot_products_view':
        bot.delete_message(chat_id=chat_id,
                           message_id=message_id)
        bot.send_message(chat_id=chat_id,
                         text=_('Active products:'))
        for product in Product.filter(is_active=True):
            shortcuts.send_product_info(bot, product, chat_id, _)
        bot.send_message(chat_id=query.message.chat_id,
                              text=_('🏪 Products'),
                              reply_markup=create_bot_products_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        return ADMIN_PRODUCTS
    elif data == 'bot_products_add':
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=_('➕ Add product'),
                              reply_markup=create_bot_product_add_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_PRODUCT_ADD
    elif data == 'bot_products_remove':
        products = Product.select(Product.title, Product.id).where(Product.is_active == True).tuples()
        if not products:
            query.answer('No products to delete')
            return ADMIN_PRODUCTS
        msg = 'Select a product which you want to remove:'
        if len(products) <= 50:
            products_keyboad = create_select_products_chunk_keyboard(_, products, 'bot_delete_product_select',
                                                                     'bot_delete_product_back')
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=_(msg),
                                  reply_markup=products_keyboad, parse_mode=ParseMode.MARKDOWN)
        else:
            shortcuts.send_chunks(bot, products, chat_id, 'bot_delete_product_select', 'bot_delete_product_back',
                                  msg, _)
        return ADMIN_DELETE_PRODUCT


def on_admin_delete_product(bot, update):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action, product_id = data.split('|')
    if action == 'bot_delete_product_select':
        try:
            product = Product.get(id=int(product_id))
        except Product.DoesNotExist:
            msg = _('Product doesn\'t exist')
        else:
            product.is_active = False
            product.save()
            msg = _('Product has been removed!')
        query.answer(text=msg)
    bot.edit_message_text(chat_id=query.message.chat_id,
                          message_id=query.message.message_id,
                          text=_('🏪 Products'),
                          reply_markup=create_bot_products_keyboard(_),
                          parse_mode=ParseMode.MARKDOWN)
    return ADMIN_PRODUCTS


def on_admin_product_add(bot, update):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    if data == 'bot_product_back':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('🏪 Products'),
                              reply_markup=create_bot_products_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_PRODUCTS
    elif data == 'bot_product_new':
        bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=_('Enter new product title'),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_back_button(_),
            )
        return ADMIN_TXT_PRODUCT_TITLE
    elif data == 'bot_product_last':
        # inactive_products = Product.filter(is_active=False)
        inactive_products = Product.select(Product.title, Product.id).where(Product.is_active == False).tuples()
        if not inactive_products:
            msg = _('You don\'t have last products')
            query.answer(text=msg)
            return ADMIN_PRODUCT_ADD
        msg = 'Select a product which you want to activate again:'
        if len(inactive_products) <= 50:
            products_keyboad = create_select_products_chunk_keyboard(_, inactive_products, 'bot_last_product_select',
                                                                     'bot_last_product_back')
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=_(msg),
                                  reply_markup=products_keyboad, parse_mode=ParseMode.MARKDOWN)
        else:
            shortcuts.send_chunks(bot, inactive_products, chat_id, 'bot_last_product_select', 'bot_last_product_back',
                                  msg, _)
        return ADMIN_PRODUCT_LAST_ADD


def on_admin_product_last_select(bot, update):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action, product_id = data.split('|')
    if action == 'bot_last_product_select':
        try:
            product = Product.get(id=int(product_id))
        except Product.DoesNotExist:
            msg = _('Product doesn\'t exist')
        else:
            product.is_active = True
            product.save()
            msg = _('Product has been added!')
        query.answer(text=msg)
    bot.edit_message_text(_('➕ Add product'), query.message.chat_id, query.message.message_id,
                          reply_markup=create_bot_product_add_keyboard(_), parse_mode=ParseMode.MARKDOWN)
    return ADMIN_PRODUCT_ADD





def on_admin_txt_product_title(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        query = update.callback_query
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('➕ Add product'),
                              reply_markup=create_bot_product_add_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        return ADMIN_PRODUCT_ADD

    title = update.message.text
    # initialize new product data
    user_data['add_product'] = {}
    user_data['add_product']['title'] = title
    update.message.reply_text(
        text=_('Enter new product prices\none per line in the format\n*COUNT PRICE*, e.g. *1 10*'),
        reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.MARKDOWN,
    )
    return ADMIN_TXT_PRODUCT_PRICES


def on_admin_txt_product_prices(bot, update, user_data):
    prices = update.message.text
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    # check that prices are valid
    prices_list = []
    for line in prices.split('\n'):
        try:
            count_str, price_str = line.split()
            count = int(count_str)
            price = float(price_str)
            prices_list.append((count, price))
        except ValueError as e:
            update.message.reply_text(
                text=_('Could not read prices, please try again'))
            return ADMIN_TXT_PRODUCT_PRICES

    user_data['add_product']['prices'] = prices_list
    update.message.reply_text(
        text=_('Send the new product photo'),
        reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.MARKDOWN,
    )
    return ADMIN_TXT_PRODUCT_PHOTO


def on_admin_txt_product_photo(bot, update, user_data):
    photo_file = bot.get_file(update.message.photo[-1].file_id)
    stream = io.BytesIO()
    photo_file.download(out=stream)

    title = user_data['add_product']['title']
    prices = user_data['add_product']['prices']
    image_data = stream.getvalue()

    product = Product.create(title=title, image=image_data)
    for count, price in prices:
        ProductCount.create(product=product, price=price, count=count)

    # clear new product data
    del user_data['add_product']
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = update.message.chat_id
    bot.send_message(chat_id=chat_id,
                     text=_('New Product Created\n✅'))
    bot.send_message(chat_id=chat_id,
                     text=_('🏪 Products'),
                     reply_markup=create_bot_products_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return ADMIN_PRODUCTS


def on_admin_cmd_delete_product(bot, update):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    products = Product.select(Product.title, Product.id).where(Product.is_active == True)
    if not products:
        update.message.reply_text(text='No products to delete')
        return ADMIN_INIT
    else:
        shortcuts.send_chunks(bot, products, chat_id, 'bot_delete_product_select', 'bot_delete_product_back',
                              'Select a product which you want to activate again:', _)
        return ADMIN_DELETE_PRODUCT


def on_admin_cmd_bot_on(bot, update):
    global BOT_ON
    BOT_ON = True
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    update.message.reply_text(text=_('Bot switched on'))
    return ADMIN_INIT


def on_admin_cmd_bot_off(bot, update):
    global BOT_ON
    BOT_ON = False
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    update.message.reply_text(text=_('Bot switched off'))
    return ADMIN_INIT


def on_admin_cmd_add_courier(bot, update):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    update.message.reply_text(text=_('Enter new courier nickname'))
    return ADMIN_TXT_COURIER_NAME


def on_admin_cmd_delete_courier(bot, update):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    text = _('Choose courier ID to delete:')

    for courier in Courier.select():
        text += '\n'
        text += '{}. {}'.format(courier.id, courier.username)

    update.message.reply_text(text=text)
    return ADMIN_TXT_DELETE_COURIER


# def on_admin_txt_delete_product(bot, update, user_data):
#     user_id = get_user_id(update)
#     _ = get_trans(user_id)
#     if update.callback_query and update.callback_query.data == 'back':
#         query = update.callback_query
#         bot.edit_message_text(chat_id=query.message.chat_id,
#                               message_id=query.message.message_id,
#                               text=_('💳 Order options'),
#                               reply_markup=create_bot_order_options_keyboard(_),
#                               parse_mode=ParseMode.MARKDOWN)
#         return ADMIN_ORDER_OPTIONS
#     product_id = update.message.text
#     try:
#         # get title to check if product is valid
#         product = Product.get(id=product_id)
#         product_title = product.title
#         product.is_active = False
#         product.save()
#         update.message.reply_text(
#             text=_('Product {} - {} was deleted').format(product_id, product_title))
#         logger.info('Product %s - %s was deleted', product_id, product_title)
#         update.message.reply_text(
#             text=_('💳 Order options'),
#             reply_markup=create_bot_order_options_keyboard(_),
#             parse_mode=ParseMode.MARKDOWN,
#         )
#         return ADMIN_ORDER_OPTIONS
#     except Product.DoesNotExist:
#         update.message.reply_text(
#             text='Invalid product id, please enter number')
#         return ADMIN_TXT_DELETE_PRODUCT


def on_admin_txt_courier_name(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        query = update.callback_query
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('🛵 Couriers'),
                              reply_markup=create_bot_couriers_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        return ADMIN_COURIERS

    name = update.message.text
    # initialize new courier data
    user_data['add_courier'] = {}
    user_data['add_courier']['name'] = name
    text = _('Enter courier telegram_id')
    update.message.reply_text(text=text)
    return ADMIN_TXT_COURIER_ID


def on_admin_txt_courier_id(bot, update, user_data):
    telegram_id = update.message.text
    user_data['add_courier']['telegram_id'] = telegram_id
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if 'location_ids' not in user_data['add_courier']:
        user_data['add_courier']['location_ids'] = []
    location_ids = user_data['add_courier']['location_ids']

    text = _('Choose locations for new courier')
    locations = []
    for location in Location:
        is_picked = False
        if location.id in location_ids:
            is_picked = True
        locations.append((location.title, location.id, is_picked))

    update.message.reply_text(
        text=text,
        reply_markup=create_courier_locations_keyboard(_, locations)
    )

    return ADMIN_TXT_COURIER_LOCATION


def on_admin_btn_courier_location(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query.data == 'location_end':
        location_ids = user_data['add_courier']['location_ids']
        username = user_data['add_courier']['name']
        telegram_id = user_data['add_courier']['telegram_id']
        # check that location name is valid
        locations = Location.filter(id__in=location_ids)
        try:
            Courier.get(username=username, telegram_id=telegram_id)
            query.message.reply_text(text='Courier with username @{} '
                                          'already added'.format(username))
        except Courier.DoesNotExist:
            courier = Courier.create(username=username, telegram_id=telegram_id)
            for location in locations:
                CourierLocation.create(courier=courier, location=location)
            # clear new courier data
            del user_data['add_courier']
            bot.send_message(chat_id=query.message.chat_id,
                             text=_('Courier added'),
                             reply_markup=create_bot_couriers_keyboard(_),
                             parse_mode=ParseMode.MARKDOWN)
            return ADMIN_COURIERS

        bot.send_message(chat_id=query.message.chat_id,
                         text=_('🛵 Couriers'),
                         reply_markup=create_bot_couriers_keyboard(_),
                         parse_mode=ParseMode.MARKDOWN)

        return ADMIN_COURIERS

    location_id = update.callback_query.data
    location_ids = user_data['add_courier']['location_ids']
    if location_id in location_ids:
        location_ids = [l_id for l_id in location_ids if location_id != l_id]
        text = 'Location removed'
    else:
        location_ids.append(location_id)
        text = 'Location added'
    user_data['add_courier']['location_ids'] = location_ids

    locations = []
    for location in Location:
        is_picked = False
        if str(location.id) in location_ids:
            is_picked = True
        locations.append((location.title, location.id, is_picked))

    bot.edit_message_text(chat_id=query.message.chat_id,
                          message_id=query.message.message_id,
                          text=text,
                          reply_markup=create_courier_locations_keyboard(_, locations),
                          parse_mode=ParseMode.MARKDOWN)

    return ADMIN_TXT_COURIER_LOCATION


def on_admin_txt_delete_courier(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        query = update.callback_query
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('🛵 Couriers'),
                              reply_markup=create_bot_couriers_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        return ADMIN_COURIERS

    courier_id = update.message.text

    # check that courier id is valid
    try:
        courier = Courier.get(id=courier_id)
    except Courier.DoesNotExist:
        update.message.reply_text(
            text='Invalid courier id, please enter correct id')
        return ADMIN_TXT_DELETE_COURIER

    courier.delete_instance()
    bot.send_message(chat_id=update.message.chat_id,
                     text=_('Courier deleted'),
                     reply_markup=create_bot_couriers_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return ADMIN_COURIERS


def on_admin_txt_location(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('🎯 Locations'),
                              reply_markup=create_bot_locations_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        return ADMIN_LOCATIONS

    location_user_txt = update.message.text
    # initialize new Location data
    user_data['add_location'] = {}
    user_data['add_location']['title'] = location_user_txt
    try:
        # Check if location exists
        Location.get(title=location_user_txt)
        update.message.reply_text(text='Location: `{}` '
                                       'already added'.format(location_user_txt),
                                  reply_markup=create_bot_locations_keyboard(_),
                                  parse_mode=ParseMode.MARKDOWN
                                  )
        return ADMIN_LOCATIONS

    except Location.DoesNotExist:
        Location.create(title=location_user_txt)

        del user_data['add_location']
        bot.send_message(chat_id=update.message.chat_id,
                         message_id=update.message.message_id,
                         text=_('new location added'),
                         reply_markup=create_bot_locations_keyboard(_),
                         parse_mode=ParseMode.MARKDOWN)
        return ADMIN_LOCATIONS


def on_admin_txt_delete_location(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        query = update.callback_query
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('🎯 Locations'),
                              reply_markup=create_bot_locations_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        return ADMIN_LOCATIONS
    lct = update.callback_query.data
    try:
        location = Location.get(title=lct)
        location.delete_instance()
    except Location.DoesNotExist:
        update.message.reply_text(
            text='Invalid Location title, please enter correct title')
        return ADMIN_TXT_DELETE_LOCATION

    query = update.callback_query
    bot.send_message(chat_id=query.message.chat_id,
                     text='Location deleted',
                     reply_markup=create_bot_locations_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return ADMIN_LOCATIONS


def on_admin_locations(bot, update):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if data == 'bot_locations_back':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('💳 Order options'),
                              reply_markup=create_bot_order_options_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_ORDER_OPTIONS
    elif data == 'bot_locations_view':
        user_id = get_user_id(update)
        _ = get_trans(user_id)
        locations = Location.select()
        location_names = [x.title for x in locations]
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('Your locations:\n\n{}').format(location_names),
                              reply_markup=create_bot_locations_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_LOCATIONS
    elif data == 'bot_locations_add':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('Enter new location'),
                              parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_back_button(_)
                              ),
        query.answer()
        return ADMIN_TXT_ADD_LOCATION
    elif data == 'bot_locations_delete':
        locations = Location.select()
        location_names = [x.title for x in locations]

        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('Choose location to delete'),
                              parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_locations_keyboard(location_names, _)
                              )
        query.answer()
        return ADMIN_TXT_DELETE_LOCATION

    return ConversationHandler.END

# additional cancel handler for admin commands
def on_admin_cancel(bot, update):
    update.message.reply_text(
        text='Admin command cancelled, to enter admin mode again type /admin',
        reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.MARKDOWN,
    )
    return BOT_STATE_INIT


def on_admin_fallback(bot, update):
    update.message.reply_text(
        text='Unknown input, type /cancel to exit admin mode',
        reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.MARKDOWN,
    )
    return ADMIN_INIT


def set_welcome_message(bot, update):
    update.callback_query.message.reply_text(
        text='Enter new welcome text',
        parse_mode=ParseMode.MARKDOWN,
    )


def new_welcome_message(bot, update):
    new_text = update.message.text
    session = get_config_session()
    session['welcome_text'] = new_text
    session_client.json_set('config', session)
    return on_start_admin(bot, update)


def on_admin_select_channel_type(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        query = update.callback_query
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('✉️ Channels'),
                              reply_markup=create_bot_channels_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        return ADMIN_CHANNELS

    channel_type = int(update.message.text)
    if channel_type in range(1, 5):
        user_data['add_channel'] = {}
        user_data['add_channel']['channel_type'] = channel_type - 1
        update.message.reply_text(
            text='Enter channel address',
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_CHANNELS_ADDRESS

    types = ['Reviews', 'Service', 'Customer', 'Vip customer', 'Courier']
    msg = ''
    for i, channel_type in enumerate(types, start=1):
        msg += '\n{} - {}'.format(i, channel_type)
    msg += '\nSelect channel type'
    update.message.reply_text(
        text=msg,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ADMIN_CHANNELS_SELECT_TYPE


def on_admin_add_channel_address(bot, update, user_data):
    types = ['reviews_channel', 'service_channel', 'customers_channel',
             'vip_customers_channel', 'couriers_channel']
    channel_address = update.message.text
    channel_type = user_data['add_channel']['channel_type']
    config_session = get_config_session()
    config_session[types[channel_type]] = channel_address
    set_config_session(config_session)
    user_data['add_channel'] = {}
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    bot.send_message(chat_id=update.message.chat_id,
                     text=_('✉️ Channels'),
                     reply_markup=create_bot_channels_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return ADMIN_CHANNELS


def on_admin_remove_channel(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        query = update.callback_query
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('✉️ Channels'),
                              reply_markup=create_bot_channels_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        return ADMIN_CHANNELS

    types = ['reviews_channel', 'service_channel', 'customers_channel',
             'vip_customers_channel', 'couriers_channel']
    channel_type = int(update.message.text)
    if channel_type in range(1, 5):
        config_session = get_config_session()
        config_session[types[channel_type - 1]] = None
        set_config_session(config_session)
        bot.send_message(chat_id=update.message.chat_id,
                         text='Channel was removed',
                         reply_markup=create_bot_channels_keyboard(_),
                         parse_mode=ParseMode.MARKDOWN)
        return ADMIN_CHANNELS

    types = ['Reviews', 'Service', 'Customer', 'Vip customer', 'Courier']
    msg = ''
    for i, channel_type in enumerate(types, start=1):
        msg += '\n{} - {}'.format(i, channel_type)
    msg += '\nSelect channel type'
    update.message.reply_text(
        text=msg,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ADMIN_CHANNELS_REMOVE


def on_admin_edit_working_hours(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        option_back_function(
            bot, update, create_bot_settings_keyboard(_),
            'Bot settings')
        return ADMIN_BOT_SETTINGS
    user_id = get_user_id(update)
    new_working_hours = update.message.text
    config_session = get_config_session()
    config_session['working_hours'] = new_working_hours
    set_config_session(config_session)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Working hours was changed',
                     reply_markup=create_bot_settings_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return ADMIN_BOT_SETTINGS


def on_admin_edit_contact_info(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        option_back_function(
            bot, update, create_bot_settings_keyboard(_),
            'Bot settings')
        return ADMIN_BOT_SETTINGS
    user_id = get_user_id(update)
    contact_info = update.message.text
    config_session = get_config_session()
    config_session['contact_info'] = contact_info
    set_config_session(config_session)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Contact info was changed',
                     reply_markup=create_bot_settings_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return ADMIN_BOT_SETTINGS


def on_admin_add_discount(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        option_back_function(
            bot, update, create_bot_order_options_keyboard(_),
            'Order options')
        return ADMIN_ORDER_OPTIONS
    # user_id = get_user_id(update)
    discount = update.message.text
    config_session = get_config_session()
    config_session['discount'] = discount
    set_config_session(config_session)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Discount was changed',
                     reply_markup=create_bot_order_options_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return ADMIN_ORDER_OPTIONS


def on_admin_add_delivery(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        option_back_function(
            bot, update, create_bot_order_options_keyboard(_),
            'Order options')
        return ADMIN_ORDER_OPTIONS
    # user_id = get_user_id(update)
    delivery = update.message.text
    cleaned_data = [int(i.strip()) for i in delivery.split('>')]
    config_session = get_config_session()
    config_session['delivery_fee'] = cleaned_data[0]
    if len(cleaned_data) == 2:
        config_session['delivery_min'] = cleaned_data[1]
    else:
        config_session['delivery_min'] = 0
    set_config_session(config_session)

    bot.send_message(chat_id=update.message.chat_id,
                     text='Delivery fee was changed',
                     reply_markup=create_bot_order_options_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return ADMIN_ORDER_OPTIONS


def on_admin_bot_on_off(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if query.data == 'back':
        option_back_function(
            bot, update, create_bot_settings_keyboard(_),
            'Bot settings')
        return ADMIN_BOT_SETTINGS
    status = query.data == 'on'
    config_session = get_config_session()
    config_session['bot_on_off'] = status
    set_config_session(config_session)
    bot.send_message(chat_id=query.message.chat_id,
                     message_id=query.message.chat_id,
                     text='Bot status was changed',
                     reply_markup=create_bot_settings_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return ADMIN_BOT_SETTINGS


def option_back_function(bot, update, return_fnc, return_title):
    query = update.callback_query
    bot.edit_message_text(chat_id=query.message.chat_id,
                          message_id=query.message.message_id,
                          text=return_title,
                          reply_markup=return_fnc,
                          parse_mode=ParseMode.MARKDOWN)


def on_admin_edit_welcome_message(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        option_back_function(
            bot, update, create_bot_order_options_keyboard(_),
            'Order options')
        return ADMIN_ORDER_OPTIONS
    # user_id = get_user_id(update)
    welcome_message = update.message.text
    config_session = get_config_session()
    config_session['welcome_text'] = welcome_message
    set_config_session(config_session)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Welcome message was changed',
                     reply_markup=create_bot_order_options_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return ADMIN_ORDER_OPTIONS


def on_admin_edit_order_message(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        option_back_function(
            bot, update, create_bot_order_options_keyboard(_),
            'Order options')
        return ADMIN_ORDER_OPTIONS
    # user_id = get_user_id(update)
    order_message = update.message.text
    config_session = get_config_session()
    config_session['order_text'] = order_message
    set_config_session(config_session)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Order message was changed',
                     reply_markup=create_bot_order_options_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return ADMIN_ORDER_OPTIONS


def on_admin_edit_final_message(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        option_back_function(
            bot, update, create_bot_order_options_keyboard(_),
            'Order options')
        return ADMIN_ORDER_OPTIONS
    final_message = update.message.text
    config_session = get_config_session()
    config_session['order_complete_text'] = final_message
    set_config_session(config_session)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Final message was changed',
                     reply_markup=create_bot_order_options_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return ADMIN_ORDER_OPTIONS


def on_admin_edit_identification(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        option_back_function(
            bot, update, create_bot_order_options_keyboard(_),
            'Order options')
        return ADMIN_ORDER_OPTIONS

    message = update.message.text.split(maxsplit=2)
    first, second, question = message
    config_session = get_config_session()
    config_session['identification_required'] = first
    config_session['identification_stage2_required'] = second
    config_session['identification_stage2_question'] = question
    set_config_session(config_session)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Identification was changed',
                     reply_markup=create_bot_order_options_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return ADMIN_ORDER_OPTIONS


def on_admin_edit_restriction(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        option_back_function(
            bot, update, create_bot_order_options_keyboard(_),
            'Order options')
        return ADMIN_ORDER_OPTIONS

    message = update.message.text.split(maxsplit=1)
    first, second = message
    config_session = get_config_session()
    config_session['only_for_customers'] = first
    config_session['vip_customers'] = second
    set_config_session(config_session)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Restriction options are changed',
                     reply_markup=create_bot_order_options_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return ADMIN_ORDER_OPTIONS


def on_admin_add_ban_list(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        option_back_function(
            bot, update, create_ban_list_keyboard(_),
            'Ban list')
        return ADMIN_BAN_LIST

    username = update.message.text.replace('@', '').replace(' ', '')
    banned = config.get_banned_users()
    if username not in banned:
        banned.append(username)
    config_session = get_config_session()
    config_session['banned'] = banned
    set_config_session(config_session)
    # user_id = get_user_id(update)
    bot.send_message(chat_id=update.message.chat_id,
                     text='@{} was banned'.format(username),
                     reply_markup=create_ban_list_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return ADMIN_BAN_LIST


def on_admin_remove_ban_list(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        option_back_function(
            bot, update, create_ban_list_keyboard(_),
            'Ban list')
        return ADMIN_BAN_LIST

    username = update.message.text.replace('@', '').replace(' ', '')
    banned = config.get_banned_users()
    banned = [ban for ban in banned if ban != username]
    config_session = get_config_session()
    config_session['banned'] = banned
    set_config_session(config_session)
    # user_id = get_user_id(update)
    bot.send_message(chat_id=update.message.chat_id,
                     text='@{} was unbanned'.format(username),
                     reply_markup=create_ban_list_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return ADMIN_BAN_LIST
