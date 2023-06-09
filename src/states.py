from telegram import ParseMode, ReplyKeyboardRemove

from .admin import is_admin
from .messages import create_confirmation_text
from .models import Location, User
from .keyboards import create_main_keyboard, create_pickup_location_keyboard, \
    create_shipping_keyboard, create_cancel_keyboard, create_time_keyboard, \
    create_confirmation_keyboard, create_phone_number_request_keyboard, create_location_request_keyboard
from .helpers import cart, config, session_client, get_user_session, get_user_id, get_trans, is_vip_customer
from .enums import BOT_STATE_CHECKOUT_SHIPPING, BOT_STATE_CHECKOUT_LOCATION_PICKUP, \
    BOT_STATE_CHECKOUT_LOCATION_DELIVERY, BOT_STATE_CHECKOUT_TIME, BOT_STATE_CHECKOUT_TIME_TEXT, \
    BOT_STATE_CHECKOUT_PHONE_NUMBER_TEXT, BOT_STATE_CHECKOUT_IDENTIFY_STAGE1, BOT_STATE_CHECKOUT_IDENTIFY_STAGE2, \
    BOT_STATE_ORDER_CONFIRMATION, BOT_STATE_INIT, \
    create_photo_question


#
# state entry functions, use them to enter various stages of checkout
# or return to previous states
#


def enter_state_shipping_method(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    update.message.reply_text(text=_('Please choose pickup or delivery:'),
                              reply_markup=create_shipping_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN, )
    return BOT_STATE_CHECKOUT_SHIPPING


def enter_state_courier_location(bot, update, user_data):
    locations = Location.select()
    location_names = [x.title for x in locations]
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    update.message.reply_text(
        text=_('Please choose where do you want to pickup your order:'),
        reply_markup=create_pickup_location_keyboard(_, location_names),
        parse_mode=ParseMode.MARKDOWN, )
    return BOT_STATE_CHECKOUT_LOCATION_PICKUP


def enter_state_location_delivery(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    update.message.reply_text(
        text=_('Please enter delivery address as text or send a location.'),
        reply_markup=create_location_request_keyboard(_),
        parse_mode=ParseMode.MARKDOWN)
    return BOT_STATE_CHECKOUT_LOCATION_DELIVERY


def enter_state_shipping_time(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    update.message.reply_text(text=_('When do you want to pickup your order?'),
                              reply_markup=create_time_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN, )
    return BOT_STATE_CHECKOUT_TIME


def enter_state_shipping_time_text(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    update.message.reply_text(text=_(
        'When do you want your order delivered? Please send the time as text.'),
        reply_markup=create_cancel_keyboard(_),
        parse_mode=ParseMode.MARKDOWN, )
    return BOT_STATE_CHECKOUT_TIME_TEXT


def enter_state_phone_number_text(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    update.message.reply_text(text=_('Please send your phone number.'),
                              reply_markup=create_phone_number_request_keyboard(_),
                              )
    return BOT_STATE_CHECKOUT_PHONE_NUMBER_TEXT


def enter_state_order_confirm(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    is_pickup = user_data['shipping']['method'] == _('🏪 Pickup')
    shipping_data = user_data['shipping']
    total = cart.get_cart_total(user_data)
    delivery_for_vip = config.get_delivery_fee_for_vip()
    product_info = cart.get_products_info(user_data)
    user_data['shipping']['vip'] = is_vip_customer(bot, user_id)
    update.message.reply_text(
        text=create_confirmation_text(user_id,
            is_pickup, shipping_data, total, delivery_for_vip, product_info),
        reply_markup=create_confirmation_keyboard(_),
        parse_mode=ParseMode.MARKDOWN,
    )

    return BOT_STATE_ORDER_CONFIRMATION


def enter_state_init_order_confirmed(bot, update, user_data):
    user_id = get_user_id(update)
    total = cart.get_cart_total(get_user_session(user_id))
    _ = get_trans(user_id)
    user = User.get(telegram_id=user_id)
    bot.send_message(
        update.message.chat_id,
        text=config.get_order_complete_text().format(
            update.effective_user.first_name),
        reply_markup=ReplyKeyboardRemove(),
    )
    bot.send_message(
        update.message.chat_id,
        text='〰〰〰〰〰〰〰〰〰〰〰〰️',
        reply_markup=create_main_keyboard(_, config.get_reviews_channel(), user, is_admin(bot, user_id), total),
    )

    return BOT_STATE_INIT


def enter_state_init_order_cancelled(bot, update, user_data, msg=None):
    user_id = get_user_id(update)
    total = cart.get_cart_total(get_user_session(user_id))
    user_data['cart'] = {}
    user_data['shipping'] = {}
    session_client.json_set(user_id, user_data)
    _ = get_trans(user_id)
    user = User.get(telegram_id=user_id)
    if not msg:
        msg = _('Order cancelled')
    update.message.reply_text(text=msg,
                              reply_markup=ReplyKeyboardRemove(),
                              parse_mode=ParseMode.MARKDOWN, )
    # send menu again as a new message
    bot.send_message(update.message.chat_id,
                     text=config.get_welcome_text().format(
                         update.effective_user.first_name),
                     reply_markup=create_main_keyboard(_, config.get_reviews_channel(), user,
                                                       is_admin(bot, user_id), total))
    return BOT_STATE_INIT
