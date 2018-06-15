#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import io
import textwrap
import random
from telegram import messageentity
from telegram import ParseMode
from telegram import KeyboardButton
from telegram import ReplyKeyboardMarkup
from telegram import ReplyKeyboardRemove
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
from telegram.ext import RegexHandler
from telegram.ext import ConversationHandler
from telegram.ext import CallbackQueryHandler

from telegram.error import TelegramError

import logging

logging.basicConfig(stream=sys.stderr, format='%(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

import gettext
_ = gettext.gettext

cat = gettext.GNUTranslations(open('he.mo', 'rb'))
_ = cat.gettext

from shoppybot_helpers import DBHelper, ConfigHelper, CartHelper

(BOT_STATE_INIT,
 BOT_STATE_CHECKOUT_SHIPPING,
 BOT_STATE_CHECKOUT_LOCATION,
 BOT_STATE_CHECKOUT_LOCATION_PICKUP,
 BOT_STATE_CHECKOUT_LOCATION_DELIVERY,
 BOT_STATE_CHECKOUT_TIME,
 BOT_STATE_CHECKOUT_PHONE_NUMBER_TEXT,
 BOT_STATE_CHECKOUT_TIME_TEXT,
 BOT_STATE_CHECKOUT_IDENTIFY_STAGE1,
 BOT_STATE_CHECKOUT_IDENTIFY_STAGE2,
 BOT_STATE_CHECKOUT_IDENTIFY_STAGE3,
 BOT_STATE_ORDER_CONFIRMATION,

 ADMIN_INIT,
 ADMIN_TXT_PRODUCT_TITLE,
 ADMIN_TXT_PRODUCT_PRICES,
 ADMIN_TXT_PRODUCT_PHOTO,
 ADMIN_TXT_DELETE_PRODUCT,
 ADMIN_TXT_COURIER_NAME,
 ADMIN_TXT_COURIER_LOCATION,
 ADMIN_TXT_DELETE_COURIER) = range(20)

BUTTON_TEXT_PICKUP      = _('🏪 Pickup')
BUTTON_TEXT_DELIVERY    = _('🚚 Delivery')
BUTTON_TEXT_NOW         = _('⏰ Now')
BUTTON_TEXT_SETTIME     = _('📅 Set time')
BUTTON_TEXT_BACK        = _('↩ Back')
BUTTON_TEXT_CONFIRM     = _('✅ Confirm')
BUTTON_TEXT_CANCEL      = _('❌ Cancel')

#
# global variable for on/off
#
BOT_ON = True

db = DBHelper()
config = ConfigHelper()
cart = CartHelper()

#
# bot helper functions
# 

def is_customer(bot, user_id):
    if not config.get_only_for_customers():
        return True

    chat_id = config.get_customers_channel()

    try:
        member = bot.getChatMember(chat_id, user_id)
        if member.status == 'left':
            return False
        else:
            return True
    except TelegramError as e:
        logger.error("Failed to check customer id: %s", e)
        return False

def is_vip_customer(bot, user_id):
    if not config.get_has_vip():
        return False

    chat_id = config.get_vip_customers_channel()
    try:
        member = bot.getChatMember(chat_id, user_id)
        if member.status == 'left':
            return False
        else:
            return True
    except TelegramError as e:
        logger.error("Failed to check vip customer id: %s", e)
        return False


# we assume people in service channel can administrate the bot
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

def create_photo_question():
    q1 = _('👍')
    q2 = _('🤘')
    q3 = _('✌️')
    q4 = _('👌')
    return random.choice([q1, q2, q3, q4])

#
# message templates
#

def create_product_description(product_id, user_data):
    text = _('Product:\n{}').format(db.get_product_title(product_id))
    text += '\n\n'
    text += '〰️'
    text += '\n'
    text += _('<b>Delivery Fee: </b>') + str(config.get_delivery_fee()) + _('$')
    text += '\n'
    text += _('for orders blow 500$')
    text += '\n'
    text += '〰️'
    text += '\n'
    text += _('Price:')
    text += '\n'

    prices = db.get_product_prices(product_id)
    for q, price in prices:
        text += '\n'
        text += _('x {} = ${}').format(q, int(price))

    q = cart.get_product_count(user_data, product_id)
    if q > 0:
        subtotal = cart.get_product_subtotal(user_data, product_id)
        text += '\n'
        text += _('Count: <b>{}</b>').format(q)
        text += '\n'
        text += _('Subtotal: <b>${}</b>').format(int(subtotal))
        text += '\n'

    return text

def create_confirmation_text(user_data):
    is_pickup = False
    if user_data['shipping']['method'] == BUTTON_TEXT_PICKUP:
        is_pickup = True

    text = _('<b>Please confirm your order:</b>')
    text += '\n\n'
    text += '〰〰〰〰〰〰〰〰〰〰〰〰️'
    text += '\n'
    text += _('Items in cart:')
    text += '\n'

    # prices = cart.get_product_ids(user_data)
    for product_id in cart.get_product_ids(user_data):
        text += '\n'
        text += _('Product:\n{}').format(db.get_product_title(product_id))
        text += '\n'
        text += _('x {} = ${}').format(cart.get_product_count(user_data, product_id),
                                       cart.get_product_subtotal(user_data, product_id),
                                       )
        text += '\n'
    text += '〰〰〰〰〰〰〰〰〰〰〰〰️'

    if cart.get_cart_total(user_data) < 500:
        if is_pickup:
            text += '\n\n'
            text += _('Total: <b>${}</b>').format(cart.get_cart_total(user_data))
        else:
            text += '\n\n'
            text += _('<b>Delivery Fee: </b>') + str(config.get_delivery_fee()) + _('$')
            text += '\n'
            text += _('Total: <b>${}</b>').format((cart.get_cart_total(user_data)) + config.get_delivery_fee())
    else:
        text += '\n\n'
        text += _('Total: <b>${}</b>').format(cart.get_cart_total(user_data))


    return text

def create_service_notice(user_data):
    is_pickup = False
    if user_data['shipping']['method'] == BUTTON_TEXT_PICKUP:
        is_pickup = True

    text = _('<b>Order notice:</b>')
    text += '\n\n'
    text += '〰〰〰〰〰〰〰〰〰〰〰〰️'
    text += '\n'
    text += _('Items in cart:')
    text += '\n'

    for product_id in cart.get_product_ids(user_data):
        text += '\n'
        text += _('Product:\n{}').format(db.get_product_title(product_id))
        text += '\n'
        text += _('x {} = ${}').format(cart.get_product_count(user_data, product_id),
                                       cart.get_product_subtotal(user_data, product_id), )
        text += '\n'

    if cart.get_cart_total(user_data) < 500:
        if is_pickup:
            text += '\n\n'
            text += _('Total: <b>${}</b>').format(cart.get_cart_total(user_data))
        else:
            text += '\n\n'
            text += _('<b>Delivery Fee: </b>') + str(config.get_delivery_fee()) + _('$')
            text += '\n'
            text += _('Total: <b>${}</b>').format((cart.get_cart_total(user_data)) + config.get_delivery_fee())
    else:
        text += '\n\n'
        text += _('Total: <b>${}</b>').format(cart.get_cart_total(user_data))
    text += '\n'
    text += '〰〰〰〰〰〰〰〰〰〰〰〰️'

    text += '\n\n'
    text += _('Shipping details:')
    text += '\n'

    shipping_data = user_data['shipping']
    for key, value in shipping_data.items():
        # if key != 'photo_id' and key != 'location' and key != 'stage2_id':
        text += '\n'
        if key == 'photo_question':
            text += _('Photo question: ')
            text += value
        if key == 'method':
            text += _('Pickup/Delivery: ')
            text += value
        if key == 'pickup_location':
            text += _('Pickup location: ')
            text += value
        if key == 'address':
            text += _('Address: ')
            text += value
        if key == 'time':
            text += _('When: ')
            text += value
        if key == 'time_text':
            text += _('Time: ')
            text += value
        if key == 'phone_number':
            text +=_('Phone number: ')
            text += value
        if key == 'vip_costumer':
            text += _('VIP ⭐️')

            #old method
            # text += "{}: {}".format(key, value)

    return text

def create_service_notice_keyboard(user_id, order_id, user_data):
    buttons = []

    if user_data['shipping']['method'] != BUTTON_TEXT_PICKUP:
        return ReplyKeyboardRemove()

    location_name = user_data['shipping']['pickup_location']
    couriers = db.get_couriers_for_location_name(location_name)

    for courier_nickname in couriers:
        buttons.append([
            InlineKeyboardButton(_('Assign @{}').format(courier_nickname), callback_data='courier|{}|{}'.format(user_id, courier_nickname))
        ])

    return InlineKeyboardMarkup(buttons)

#
# keyboard templates
#

def create_product_keyboard(product_id, user_data):
    button_row = []

    if cart.get_product_count(user_data, product_id) > 0:
        button = InlineKeyboardButton(_('➕ Add more'), callback_data='product_add|{}'.format(product_id))
        button_row.append(button)
    else:
        button = InlineKeyboardButton(_('🛍 Add to cart'), callback_data='product_add|{}'.format(product_id))
        button_row.append(button)

    if cart.get_product_count(user_data, product_id) > 0:
        button = InlineKeyboardButton(_('➖ Remove'), callback_data='product_remove|{}'.format(product_id))
        button_row.append(button)

    return InlineKeyboardMarkup([button_row])

def create_main_keyboard():
    main_button_list = [
        [InlineKeyboardButton(_('🏪 Our products'), callback_data='menu_products')],
        [InlineKeyboardButton(_('🛍 Checkout'), callback_data='menu_order')],
        [InlineKeyboardButton(_('⭐ Reviews'), url=config.get_reviews_channel())],
        [InlineKeyboardButton(_('⏰ Working hours'), callback_data='menu_hours')],
        [InlineKeyboardButton(_('☎ Contact info'), callback_data='menu_contact')],
    ]
    return InlineKeyboardMarkup(main_button_list)

def create_shipping_keyboard():
    button_row = [
        [KeyboardButton(BUTTON_TEXT_PICKUP)],
        [KeyboardButton(BUTTON_TEXT_DELIVERY)],
        [KeyboardButton(BUTTON_TEXT_CANCEL)],
    ]
    return ReplyKeyboardMarkup(button_row, resize_keyboard=True)

def create_pickup_location_keyboard():
    locations = db.get_pickup_locations()
    location_names = [x[1] for x in locations]

    button_column = []
    for location_name in location_names:
        button_column.append([KeyboardButton(location_name)])

    button_column.append([KeyboardButton(BUTTON_TEXT_BACK), KeyboardButton(BUTTON_TEXT_CANCEL)])
    return ReplyKeyboardMarkup(button_column, resize_keyboard=True)


def create_time_keyboard():
    button_row = [
        [KeyboardButton(BUTTON_TEXT_NOW)],
        [KeyboardButton(BUTTON_TEXT_SETTIME)],
        [KeyboardButton(BUTTON_TEXT_BACK),
         KeyboardButton(BUTTON_TEXT_CANCEL)],
    ]
    return ReplyKeyboardMarkup(button_row, resize_keyboard=True)

def create_confirmation_keyboard():
    button_row = [
        [KeyboardButton(BUTTON_TEXT_CONFIRM)],
        [KeyboardButton(BUTTON_TEXT_BACK),
         KeyboardButton(BUTTON_TEXT_CANCEL)]
    ]
    return ReplyKeyboardMarkup(button_row, resize_keyboard=True)

def create_cancel_keyboard():
    button_row = [[
        KeyboardButton(BUTTON_TEXT_BACK),
        KeyboardButton(BUTTON_TEXT_CANCEL)],
    ]
    return ReplyKeyboardMarkup(button_row, resize_keyboard=True)

#
# bot handlers
# 

def on_start(bot, update, user_data):
    user_id = update.message.from_user.id
    # TODO: this is awkward, we need a real session manager here
    if 'cart' not in user_data:
        user_data['cart'] = {}
    if 'shipping' not in user_data:
        user_data['shipping'] = {}

    if BOT_ON:
        if is_customer(bot, user_id) or is_vip_customer(bot, user_id):
            logger.info('Starting session for user %s, language: %s',
                update.message.from_user.id,
                update.message.from_user.language_code)
            update.message.reply_text(
                text=config.get_welcome_text().format(update.message.from_user.first_name),
                reply_markup=create_main_keyboard(),
            )
            return BOT_STATE_INIT
        else:
            logger.info('User %s rejected (not a customer)', update.message.from_user.id)
            update.message.reply_text(
                text=_('Sorry {}\nYou are not authorized to use this bot').format(update.message.from_user.first_name),
                reply_markup=None,
                parse_mode=ParseMode.MARKDOWN,
            )
            return ConversationHandler.END
    else:
        update.message.reply_text(
            text=_('Sorry {}, the bot is currently switched off').format(update.message.from_user.first_name),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

def on_menu(bot, update, user_data=None):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if BOT_ON:
        if is_customer(bot, user_id) or is_vip_customer(bot, user_id):
            if data == 'menu_products':
                # the menu disappears
                bot.edit_message_text(
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    text=_('Our products:'),
                    parse_mode=ParseMode.MARKDOWN,
                )

                # send_products to current chat
                for product in db.get_products():
                    product_id, title = product

                    images = db.get_product_images(product_id)

                    if len(images) > 0:
                        image_data = images[0]
                        image_stream = io.BytesIO(image_data)
                        bot.send_photo(query.message.chat_id, photo=image_stream)
                        bot.send_message(
                            query.message.chat_id,
                            text=create_product_description(product_id, user_data),
                            reply_markup=create_product_keyboard(product_id, user_data),
                            parse_mode=ParseMode.HTML,
                        )

                # send menu again as a new message
                bot.send_message(
                    query.message.chat_id,
                    text=config.get_order_text().format(_('#Our_Species:')),
                    reply_markup=create_main_keyboard(),
                    parse_mode=ParseMode.HTML,
                )
            elif data == 'menu_order':
                if cart.is_full(user_data):
                    # we are not using enter_state_... here because it relies on update.message
                    bot.send_message(
                        query.message.chat_id,
                        text=_('Please choose pickup or delivery'),
                        reply_markup=create_shipping_keyboard(),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    query.answer()
                    return BOT_STATE_CHECKOUT_SHIPPING
                else:
                    bot.answer_callback_query(
                        query.id,
                        text=_('Your cart is empty. Please add something to the cart.'),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return BOT_STATE_INIT
            elif data == 'menu_hours':
                bot.edit_message_text(
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    text=config.get_working_hours(),
                    reply_markup=create_main_keyboard(),
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif data == 'menu_contact':
                bot.edit_message_text(
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    text=config.get_contact_info(),
                    reply_markup=create_main_keyboard(),
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif data.startswith('product_add'):
                product_id = int(data.split('|')[1])
                cart.add(user_data, product_id)

                bot.edit_message_text(
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    text=create_product_description(product_id, user_data),
                    reply_markup=create_product_keyboard(product_id, user_data),
                    parse_mode=ParseMode.HTML,
                )
            elif data.startswith('product_remove'):
                product_id = int(data.split('|')[1])
                cart.remove(user_data, product_id)

                bot.edit_message_text(
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    text=create_product_description(product_id, user_data),
                    reply_markup=create_product_keyboard(product_id, user_data),
                    parse_mode=ParseMode.HTML,
                )
            else:
                logger.warn('Unknown query: %s', query.data)
        else:
            logger.info('User %s rejected (not a customer)', user_id)
            bot.send_message(
                query.message.chat_id,
                text=_('Sorry {}\nYou are not authorized to use this bot').format(query.from_user.first_name),
                reply_markup=None,
                parse_mode=ParseMode.HTML,
            )
            return ConversationHandler.END
    else:
        bot.send_message(
            query.message.chat_id,
            text=_('Sorry, the bot is currently switched off').format(query.from_user.first_name),
            reply_markup=None,
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    query.answer()
    # we want to remain in init state here
    return BOT_STATE_INIT

def on_error(bot, update, error):
    logger.error('Error: %s', error)

# will be called when conversation context is lost (e.g. bot is restarted)
# and the user clicks menu buttons
def fallback_query_handler(bot, update, user_data):
    # TODO: this is awkward, we need a real session manager here
    if 'cart' not in user_data:
        user_data['cart'] = {}
    if 'shipping' not in user_data:
        user_data['shipping'] = {}
    return on_menu(bot, update, user_data)


#
# state entry functions, use them to enter various stages of checkout
# or return to previous states
#

def enter_state_shipping_method(bot, update, user_data):
    update.message.reply_text(
        text=_('Please choose pickup or delivery:'),
        reply_markup=create_shipping_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return BOT_STATE_CHECKOUT_SHIPPING

def enter_state_location_pickup(bot, update, user_data):
    update.message.reply_text(
        text=_('Please choose where do you want to pickup your order:'),
        # TODO: markup
        reply_markup=create_pickup_location_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return BOT_STATE_CHECKOUT_LOCATION_PICKUP

def enter_state_location_delivery(bot, update, user_data):
    update.message.reply_text(
        text=_('Please enter delivery address as text or send a location.'),
        reply_markup=create_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return BOT_STATE_CHECKOUT_LOCATION_DELIVERY

def enter_state_shipping_time(bot, update, user_data):
    update.message.reply_text(
        text=_('When do you want to pickup your order?'),
        reply_markup=create_time_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return BOT_STATE_CHECKOUT_TIME

def enter_state_shipping_time_text(bot, update, user_data):
    update.message.reply_text(
        text=_('When do you want your order delivered? Please send the time as text.'),
        reply_markup=create_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return BOT_STATE_CHECKOUT_TIME_TEXT

def enter_state_phone_number_text(bot, update, user_data):
    update.message.reply_text(
        text=_('Please send your phone number.'),
        reply_markup=create_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return BOT_STATE_CHECKOUT_PHONE_NUMBER_TEXT

def enter_state_identify_photo(bot, update, user_data):
    if 'photo_question' not in user_data['shipping']:
        user_data['shipping']['photo_question'] = create_photo_question()
    else:
        user_data['shipping']['photo_question'] = {}
        user_data['shipping']['photo_question'] = create_photo_question()

    text = _('Please provide an identification picture. {}').format(user_data['shipping']['photo_question'])
    update.message.reply_text(
        text=text,
        reply_markup=create_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return BOT_STATE_CHECKOUT_IDENTIFY_STAGE1

def enter_state_identify_stage2(bot, update, user_data):
    update.message.reply_text(
        text=config.get_identification_stage2_question(),
        reply_markup=create_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return BOT_STATE_CHECKOUT_IDENTIFY_STAGE2

def enter_state_identify_stage3(bot, update, user_data):
    update.message.reply_text(
        text=config.get_identification_stage3_question(),
        reply_markup=create_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN,)

    return BOT_STATE_CHECKOUT_IDENTIFY_STAGE3

def enter_state_order_confirm(bot, update, user_data):
    update.message.reply_text(
        text=create_confirmation_text(user_data),
        reply_markup=create_confirmation_keyboard(),
        parse_mode=ParseMode.HTML,
    )
    return BOT_STATE_ORDER_CONFIRMATION

def enter_state_init_order_confirmed(bot, update, user_data):
    bot.send_message(
        update.message.chat_id,
        text=config.get_order_complete_text().format(update.message.from_user.first_name),
        reply_markup=ReplyKeyboardRemove(),
    )
    bot.send_message(
        update.message.chat_id,
        text='〰〰〰〰〰〰〰〰〰〰〰〰️',
        reply_markup=create_main_keyboard(),
    )

    # send menu again as a new message
    # bot.send_message(
    #     update.message.chat_id,
    #     text=_('<b>I am happy to see you again {}😉\n\nWhat would you like to order?</b>'),
    #     reply_markup=create_main_keyboard(),
    #     parse_mode=ParseMode.HTML,
    # )
    return BOT_STATE_INIT

def enter_state_init_order_cancelled(bot, update, user_data):
    update.message.reply_text(
        text=_('<b>Order cancelled</b>'),
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML,
    )
    # send menu again as a new message
    bot.send_message(
        update.message.chat_id,
        text=config.get_welcome_text().format(update.message.from_user.first_name),
        reply_markup=create_main_keyboard(),
    )
    return BOT_STATE_INIT

#
# confirmation handlers
#

def on_shipping_method(bot, update, user_data):
    key = update.message.text

    if key == BUTTON_TEXT_CANCEL:
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif key == BUTTON_TEXT_PICKUP:
        user_data['shipping']['method'] = key
        return enter_state_location_pickup(bot, update, user_data)
    elif key == BUTTON_TEXT_DELIVERY:
        user_data['shipping']['method'] = key
        return enter_state_location_delivery(bot, update, user_data)

def on_shipping_pickup_location(bot, update, user_data):
    key = update.message.text

    if key == BUTTON_TEXT_BACK:
        return enter_state_shipping_method(bot, update, user_data)
    elif key == BUTTON_TEXT_CANCEL:
        return enter_state_init_order_cancelled(bot, update, user_data)
    else:
        user_data['shipping']['pickup_location'] = key
        return enter_state_shipping_time(bot, update, user_data)

def on_shipping_delivery_address(bot, update, user_data):
    key = update.message.text

    if update.message.location:
        location = update.message.location
        user_data['shipping']['location'] = location
        return enter_state_shipping_time(bot, update, user_data)
    else:
        if key == BUTTON_TEXT_BACK:
            return enter_state_shipping_method(bot, update, user_data)
        elif key == BUTTON_TEXT_CANCEL:
            return enter_state_init_order_cancelled(bot, update, user_data)
        else:
            address = update.message.text
            user_data['shipping']['address'] = address
            return enter_state_shipping_time(bot, update, user_data)

def on_checkout_time(bot, update, user_data):
    key = update.message.text

    if key == BUTTON_TEXT_BACK:
        return enter_state_shipping_method(bot, update, user_data)
    elif key == BUTTON_TEXT_CANCEL:
        return  enter_state_init_order_cancelled(bot, update, user_data)
    elif key == BUTTON_TEXT_NOW:
        user_data['shipping']['time'] = key
        if config.get_phone_number_required():
            return enter_state_phone_number_text(bot, update, user_data)
        else:
            if config.get_identification_required():
                return enter_state_identify_photo(bot, update, user_data)
            else:
                return enter_state_order_confirm(bot, update, user_data)
    elif key == BUTTON_TEXT_SETTIME:
        user_data['shipping']['time'] = key
        return enter_state_shipping_time_text(bot, update, user_data)
    else:
        logger.warn("Unknown input %s", key)

def on_shipping_time_text(bot, update, user_data):
    key = update.message.text
    if key == BUTTON_TEXT_BACK:
        return enter_state_shipping_time(bot, update, user_data)
    elif key == BUTTON_TEXT_CANCEL:
        return enter_state_init_order_cancelled(bot, update, user_data)
    else:
        user_data['shipping']['time_text'] = key
        return enter_state_phone_number_text(bot, update, user_data)


    # else:
    #     return enter_state_order_confirm(bot, update, user_data)

def on_phone_number_text(bot, update, user_data):
    key = update.message.text

    if key == BUTTON_TEXT_CANCEL:
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif key == BUTTON_TEXT_BACK:
        return enter_state_shipping_time(bot, update, user_data)
    else:
        phone_number_text = update.message.text
        user_data['shipping']['phone_number'] = phone_number_text
        if config.get_identification_required():
            return enter_state_identify_photo(bot, update, user_data)
        else:
            return enter_state_order_confirm(bot, update, user_data)

def on_shipping_identify_photo(bot, update, user_data):
    text_key = update.message.text
    user_id = update.message.from_user.id

    if text_key == BUTTON_TEXT_CANCEL:
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif text_key == BUTTON_TEXT_BACK:
        if config.get_phone_number_required():
            return enter_state_phone_number_text(bot, update, user_data)
        else:
            return enter_state_shipping_time(bot, update, user_data)
    if update.message.photo:
        photo_file = bot.get_file(update.message.photo[-1].file_id)
        user_data['shipping']['photo_id'] = photo_file.file_id
        if is_vip_customer(bot, user_id):
            vip = _('vip costumer')
            user_data['shipping']['vip_costumer'] = vip
            return enter_state_order_confirm(bot, update, user_data)
        elif config.get_identification_stage2_required():
            return enter_state_identify_stage2(bot, update, user_data)
        else:
            return enter_state_order_confirm(bot, update, user_data)
    else:
        # No photo, ask the user again
        return enter_state_identify_photo(bot, update, user_data)

def on_shipping_identify_stage2(bot, update, user_data):
    key = update.message.text

    if key == BUTTON_TEXT_CANCEL:
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif key == BUTTON_TEXT_BACK:
        return enter_state_identify_photo(bot, update, user_data)

    if update.message.photo:
        photo_file = bot.get_file(update.message.photo[-1].file_id)
        user_data['shipping']['stage2_id'] = photo_file.file_id
        if config.get_identification_stage3_required():
            return enter_state_identify_stage3(bot, update, user_data)
        else:
            return enter_state_order_confirm(bot, update, user_data)
    else:
        # No photo, ask the user again
        return enter_state_identify_stage2(bot, update, user_data)

def on_shipping_identify_stage3(bot, update, user_data):
    key = update.message.text

    if key == BUTTON_TEXT_CANCEL:
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif key == BUTTON_TEXT_BACK:
        return enter_state_identify_stage2(bot, update, user_data)

    if update.message.photo:
        photo_file = bot.get_file(update.message.photo[-1].file_id)
        user_data['shipping']['stage3_id'] = photo_file.file_id
        return enter_state_order_confirm(bot, update, user_data)
    else:
        # No photo, ask the user again
        return enter_state_identify_stage3(bot, update, user_data)

def on_confirm_order(bot, update, user_data):
    key = update.message.text

    # order data
    user_id = update.message.from_user.id
    order_id = None

    is_pickup = False
    if user_data['shipping']['method'] == BUTTON_TEXT_PICKUP:
        is_pickup = True

    if key == BUTTON_TEXT_CONFIRM:
        # ORDER CONFIRMED, send the details to service channel
        bot.send_message(
            config.get_service_channel(),
            text=_('Order confirmed from (@{})').format(update.message.from_user.username),
            parse_mode=ParseMode.MARKDOWN,
        )
        if is_pickup:
            bot.send_message(
                config.get_service_channel(),
                text=create_service_notice(user_data),
                parse_mode=ParseMode.HTML,
            )
        else:
            bot.send_message(
                config.get_service_channel(),
                text=create_service_notice(user_data),
                parse_mode=ParseMode.HTML,
            )
        if 'photo_id' in user_data['shipping']:
            bot.send_photo(
                config.get_service_channel(),
                photo=user_data['shipping']['photo_id'],
                caption=_('Stage 1 Identification - Selfie'),
                parse_mode=ParseMode.MARKDOWN,
            )

        if 'stage2_id' in user_data['shipping']:
            bot.send_photo(
                config.get_service_channel(),
                photo=user_data['shipping']['stage2_id'],
                caption=_('Stage 2 Identification - FB'),
                parse_mode=ParseMode.MARKDOWN,
                )

        if 'stage3_id' in user_data['shipping']:
            bot.send_photo(
                config.get_service_channel(),
                photo=user_data['shipping']['stage3_id'],
                caption=_('Stage 3 Identification - ID'),
                parse_mode=ParseMode.MARKDOWN,
                )

        if 'location' in user_data['shipping']:
            bot.send_location(
                config.get_service_channel(),
                location=user_data['shipping']['location'],
            )

        # clear cart and shipping data
        user_data['cart'] = {}
        user_data['shipping'] = {}

        return enter_state_init_order_confirmed(bot, update, user_data)

    elif key == BUTTON_TEXT_CANCEL:
        # ORDER CANCELLED, send nothing
        # and only clear shipping details
        user_data['shipping'] = {}
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif key == BUTTON_TEXT_BACK:
        if is_vip_customer(bot, user_id):
            return enter_state_identify_photo(bot, update, user_data)
        else:
            if config.get_identification_required():
                if config.get_identification_stage2_required():
                    return enter_state_identify_stage2(bot, update, user_data)
                else:
                    return enter_state_identify_photo(bot, update, user_data)
            elif config.get_phone_number_required():
                return enter_state_phone_number_text(bot, update, user_data)
            else:
                return enter_state_shipping_time(bot, update, user_data)
    else:
        logger.warn("Unknown input %s", key)

def on_cancel(bot, update, user_data):
    return enter_state_init_order_cancelled(bot, update, user_data)

def checkout_fallback_command_handler(bot, update, user_data):
    query = update.callback_query
    data = query.data
    bot.answer_callback_query(query.id, text=_('Cannot process commands when checking out'))


#
# admin states
#

def on_start_admin(bot, update):
    if not is_admin(bot, update.message.from_user.id):
        logger.info('User %s, @%s rejected (not admin)', update.message.from_user.id, update.message.from_user.username)
        update.message.reply_text(
            text=_('Sorry {}, you are not authorized to administrate this bot').format(update.message.from_user.first_name)
        )
        return BOT_STATE_INIT

    msg = "\n".join([
        'Entering admin mode',
        'Use following commands:',
        '/addproduct - add new product',
        '/delproduct - delete product',
        '/addcourier - add courier',
        '/delcourier - delete courier',
        '/on - enable shopping',
        '/off - disable shopping',
    ])
    update.message.reply_text(
        text=msg,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ADMIN_INIT

def on_admin_cmd_add_product(bot, update):
    update.message.reply_text(
        text='Enter new product title',
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ADMIN_TXT_PRODUCT_TITLE

def on_admin_txt_product_title(bot, update, user_data):
    title = update.message.text
    # initialize new product data
    user_data['add_product'] = {}
    user_data['add_product']['title'] = title
    update.message.reply_text(
        text='Enter new product prices one per line in the format *COUNT PRICE*, e.g. *1 10.0*',
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ADMIN_TXT_PRODUCT_PRICES

def on_admin_txt_product_prices(bot, update, user_data):
    prices = update.message.text

    # check that prices are valid
    prices_list = []
    for line in prices.split('\n'):
        try:
            count_str, price_str = line.split()
            count = int(count_str)
            price = float(price_str)
            prices_list.append((count, price))
        except ValueError as e:
            update.message.reply_text(text='Could not read prices, please try again')
            return ADMIN_TXT_PRODUCT_PRICES

    user_data['add_product']['prices'] = prices_list
    update.message.reply_text(
        text='Send the new product photo',
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ADMIN_TXT_PRODUCT_PHOTO

def on_admin_txt_product_photo(bot, update, user_data):
    photo_file = bot.get_file(update.message.photo[-1].file_id)
    stream = io.BytesIO()
    photo_file.download(out=stream)

    title = user_data['add_product']['title']
    prices = user_data['add_product']['prices']
    image_data = stream.getvalue()

    db.add_new_product(title, prices, image_data)

    # clear new product data
    del user_data['add_product']

    update.message.reply_text(text='Product created, type /cancel to leave admin mode')
    logger.info("Product created: %s", title)
    return ADMIN_INIT

def on_admin_cmd_delete_product(bot, update):
    products = db.get_products()
    if len(products) == 0:
        update.message.reply_text(text='No products to delete')
        return ADMIN_INIT
    else:
        products = db.get_products()
        text = 'Choose product ID to delete:'
        for product_id, title in products:
            text += '\n'
            text += '{}. {}'.format(product_id, title)
        update.message.reply_text(text=text)
        return ADMIN_TXT_DELETE_PRODUCT

def on_admin_cmd_bot_on(bot, update):
    global BOT_ON
    BOT_ON = True
    update.message.reply_text(text='Bot switched on')
    return ADMIN_INIT

def on_admin_cmd_bot_off(bot, update):
    global BOT_ON
    BOT_ON = False
    update.message.reply_text(text='Bot switched off')
    return ADMIN_INIT

def on_admin_cmd_add_courier(bot, update):
    update.message.reply_text(text='Enter new courier nickname')
    return ADMIN_TXT_COURIER_NAME

def on_admin_cmd_delete_courier(bot, update):
    text = 'Choose courier ID to delete:'

    for courier_id, nickname in db.get_couriers():
        text += '\n'
        text += '{}. {}'.format(courier_id, nickname)

    update.message.reply_text(text=text)
    return ADMIN_TXT_DELETE_COURIER

def on_admin_txt_delete_product(bot, update):
    product_id = update.message.text
    try:
        int(product_id)
        # get title to check if product is valid
        product_title = db.get_product_title(product_id)
        db.delete_product(product_id)
        update.message.reply_text(text='Product {} - {} is deleted'.format(product_id, product_title))
        logger.info('Product %s - %s is deleted', product_id, product_title)
        return ADMIN_INIT
    except ValueError:
        update.message.reply_text(text='Invalid product id, please enter number')
        return ADMIN_TXT_DELETE_PRODUCT
    except RuntimeError:
        update.message.reply_text(text='Unknown product id, please choose from the list')
        return ADMIN_TXT_DELETE_PRODUCT

def on_admin_txt_courier_name(bot, update, user_data):
    name = update.message.text
    # initialize new courier data
    user_data['add_courier'] = {}
    user_data['add_courier']['name'] = name

    text = 'Enter location ID for this courier (choose number from list below):'

    for location_id, name in db.get_pickup_locations():
        text += '\n'
        text += '{}. {}'.format(location_id, name)

    update.message.reply_text(text=text)
    return ADMIN_TXT_COURIER_LOCATION

def on_admin_txt_courier_location(bot, update, user_data):
    location_id = update.message.text
    user_data['add_courier']['location_id'] = location_id

    # check that location name is valid
    try:
        location_name = db.get_pickup_location_name(location_id)
    except RuntimeError:
        update.message.reply_text(text='Invalid location id, please enter number')
        return ADMIN_TXT_COURIER_LOCATION

    db.add_new_courier(user_data['add_courier']['name'], location_id)

    # clear new courier data
    del user_data['add_courier']

    update.message.reply_text(text='Courier added')
    return ADMIN_INIT

def on_admin_txt_delete_courier(bot, update):
    courier_id = update.message.text

    # check that courier id is valid
    try:
        courier_nickname = db.get_courier_nickname(courier_id)
    except RuntimeError:
        update.message.reply_text(text='Invalid courier id, please enter number')
        return ADMIN_TXT_DELETE_COURIER

    db.delete_courier(courier_id)
    update.message.reply_text(text='Courier deleted')
    return ADMIN_INIT

# additional cancel handler for admin commands
def on_admin_cancel(bot, update):
    update.message.reply_text(
        text='Admin command cancelled, to enter admin mode again type /admin',
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return BOT_STATE_INIT

def on_admin_fallback(bot, update):
    update.message.reply_text(
        text='Unknown input, type /cancel to exit admin mode',
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ADMIN_INIT

#
# handle couriers
#

def service_channel_courier_query_handler(bot, update, user_data):
    query = update.callback_query
    data = query.data
    label, user_id, courier_nickname = data.split('|')

    # tell the user courier is assigned
    bot.send_message(
        user_id,
        text=_('Courier @{} assigned to your order').format(courier_nickname),
        parse_mode=ParseMode.HTML,
    )

    # TODO: might update the couriers keyboard here as well (or not)
    bot.answer_callback_query(query.id, text=_('Courier {} assigned').format(courier_nickname))

#
# main
#

def main():
    user_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', on_start, pass_user_data=True),
                      CommandHandler('admin', on_start_admin),
                      CallbackQueryHandler(fallback_query_handler, pattern='^(menu|product)', pass_user_data=True)],
        states={
            BOT_STATE_INIT: [
                CommandHandler('start', on_start, pass_user_data=True),
                CommandHandler('admin', on_start_admin),
                CallbackQueryHandler(on_menu, pattern='^(menu|product)', pass_user_data=True)
            ],
            BOT_STATE_CHECKOUT_SHIPPING: [
                CallbackQueryHandler(checkout_fallback_command_handler, pass_user_data=True),
                MessageHandler(Filters.text, on_shipping_method, pass_user_data=True),
            ],
            BOT_STATE_CHECKOUT_LOCATION_PICKUP: [
                CallbackQueryHandler(checkout_fallback_command_handler, pass_user_data=True),
                MessageHandler(Filters.text, on_shipping_pickup_location, pass_user_data=True),
            ],
            BOT_STATE_CHECKOUT_LOCATION_DELIVERY: [
                CallbackQueryHandler(checkout_fallback_command_handler, pass_user_data=True),
                MessageHandler(Filters.text | Filters.location, on_shipping_delivery_address, pass_user_data=True),
            ],
            BOT_STATE_CHECKOUT_TIME: [
                CallbackQueryHandler(checkout_fallback_command_handler, pass_user_data=True),
                MessageHandler(Filters.text, on_checkout_time, pass_user_data=True),
            ],
            BOT_STATE_CHECKOUT_TIME_TEXT: [
                CallbackQueryHandler(checkout_fallback_command_handler, pass_user_data=True),
                MessageHandler(Filters.text, on_shipping_time_text, pass_user_data=True),
            ],
            BOT_STATE_CHECKOUT_PHONE_NUMBER_TEXT: [
                CallbackQueryHandler(checkout_fallback_command_handler, pass_user_data=True),
                MessageHandler(Filters.text, on_phone_number_text, pass_user_data=True),
            ],
            BOT_STATE_CHECKOUT_IDENTIFY_STAGE1: [
                CallbackQueryHandler(checkout_fallback_command_handler, pass_user_data=True),
                MessageHandler(Filters.all, on_shipping_identify_photo, pass_user_data=True),
            ],
            BOT_STATE_CHECKOUT_IDENTIFY_STAGE2: [
                CallbackQueryHandler(checkout_fallback_command_handler, pass_user_data=True),
                MessageHandler(Filters.all, on_shipping_identify_stage2, pass_user_data=True),
            ],
            BOT_STATE_CHECKOUT_IDENTIFY_STAGE3: [
                CallbackQueryHandler(checkout_fallback_command_handler, pass_user_data=True),
                MessageHandler(Filters.all, on_shipping_identify_stage3, pass_user_data=True),
            ],
            BOT_STATE_ORDER_CONFIRMATION: [
                CallbackQueryHandler(checkout_fallback_command_handler, pass_user_data=True),
                MessageHandler(Filters.text, on_confirm_order, pass_user_data=True),
            ],

            #
            # admin states
            #
            ADMIN_INIT: [
                CommandHandler('addproduct', on_admin_cmd_add_product),
                CommandHandler('delproduct', on_admin_cmd_delete_product),
                CommandHandler('addcourier', on_admin_cmd_add_courier),
                CommandHandler('delcourier', on_admin_cmd_delete_courier),
                CommandHandler('on', on_admin_cmd_bot_on),
                CommandHandler('off', on_admin_cmd_bot_off),
                CommandHandler('cancel', on_admin_cancel),
                MessageHandler(Filters.all, on_admin_fallback),
            ],
            ADMIN_TXT_PRODUCT_TITLE: [
                MessageHandler(Filters.text, on_admin_txt_product_title, pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_TXT_PRODUCT_PRICES: [
                MessageHandler(Filters.text, on_admin_txt_product_prices, pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_TXT_PRODUCT_PHOTO: [
                MessageHandler(Filters.photo, on_admin_txt_product_photo, pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_TXT_DELETE_PRODUCT: [
                MessageHandler(Filters.text, on_admin_txt_delete_product),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_TXT_COURIER_NAME: [
                MessageHandler(Filters.text, on_admin_txt_courier_name, pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_TXT_COURIER_LOCATION: [
                MessageHandler(Filters.text, on_admin_txt_courier_location, pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_TXT_DELETE_COURIER: [
                MessageHandler(Filters.text, on_admin_txt_delete_courier),
                CommandHandler('cancel', on_admin_cancel),
            ],
        },
        fallbacks=[CommandHandler('cancel', on_cancel, pass_user_data=True),
                   CommandHandler('start', on_start, pass_user_data=True)]
    )

    updater = Updater(config.get_api_token())
    updater.dispatcher.add_handler(user_conversation_handler)
    updater.dispatcher.add_handler(CallbackQueryHandler(service_channel_courier_query_handler,
        pattern='^courier', pass_user_data=True))
    updater.dispatcher.add_error_handler(on_error)
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
