import datetime

from telegram import ParseMode, InputMediaPhoto
from telegram.ext import ConversationHandler

from .admin import is_admin
from .messages import create_service_notice
from .helpers import cart, config, session_client, get_user_session, \
    get_user_id, get_username, is_vip_customer, set_config_session, get_locale, get_trans, get_config_session
from .keyboards import create_drop_responsibility_keyboard, \
    create_service_notice_keyboard, create_main_keyboard, create_courier_confirmation_keyboard, \
    create_admin_keyboard, create_statistics_keyboard, \
    create_bot_settings_keyboard, create_bot_couriers_keyboard, \
    create_bot_channels_keyboard, create_bot_order_options_keyboard, \
    create_back_button, create_on_off_buttons, create_ban_list_keyboard, create_show_order_keyboard, \
    create_service_channel_keyboard, couriers_choose_keyboard
from .models import User, Courier, Order, OrderItem, Location, CourierLocation, DeliveryMethod, OrderPhotos
from .states import enter_state_init_order_cancelled, enter_state_courier_location, enter_state_shipping_method, \
    enter_state_location_delivery, enter_state_shipping_time, enter_state_phone_number_text, enter_state_identify_photo, \
    enter_state_order_confirm, enter_state_shipping_time_text, enter_state_identify_stage2, \
    enter_state_init_order_confirmed
from .enums import logger, BOT_STATE_INIT, ADMIN_BOT_SETTINGS, ADMIN_ORDER_OPTIONS, \
    ADMIN_TXT_COURIER_NAME, ADMIN_TXT_DELETE_COURIER, ADMIN_CHANNELS, ADMIN_CHANNELS_SELECT_TYPE, \
    ADMIN_CHANNELS_REMOVE, ADMIN_BAN_LIST, BOT_STATE_CHECKOUT_PHONE_NUMBER_TEXT, ADMIN_MENU, \
    ADMIN_STATISTICS, ADMIN_COURIERS, ADMIN_EDIT_WORKING_HOURS, ADMIN_EDIT_CONTACT_INFO, ADMIN_BOT_ON_OFF, \
    ADMIN_BAN_LIST_REMOVE, ADMIN_BAN_LIST_ADD, BOT_STATE_CHECKOUT_LOCATION_DELIVERY


def on_shipping_method(bot, update, user_data):
    key = update.message.text
    user_id = get_user_id(update)
    user_data = get_user_session(user_id)
    _ = get_trans(user_id)
    if key == _('❌ Cancel'):
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif key == _('🏪 Pickup') or key == _('🚚 Delivery'):
        user_data['shipping']['method'] = key
        session_client.json_set(user_id, user_data)
        return enter_state_courier_location(bot, update, user_data)
    else:
        return enter_state_shipping_method(bot, update, user_data)


def on_bot_language_change(bot, update, user_data):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    user_data = get_user_session(user_id)
    _ = get_trans(user_id)
    if data == 'iw' or data == 'en':
        user_data['locale'] = data
        session_client.json_set(user_id, user_data)
        user = User.get(telegram_id=user_id)
        user.locale = data
        user.save()

        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=config.get_welcome_text().format(
                                  query.message.chat.first_name),
                              reply_markup=create_main_keyboard(user_id, config.get_reviews_channel(),
                                                                is_admin(bot, user_id)),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return BOT_STATE_INIT
    else:
        logger.info('Unknown command - {}'.format(data))
        bot.send_message(
            query.message.chat_id,
            text='Unknown command',
            reply_markup=None,
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END


def on_shipping_pickup_location(bot, update, user_data):
    key = update.message.text
    user_id = get_user_id(update)
    user_data = get_user_session(user_id)
    locations = Location.select()
    location_names = [x.title for x in locations]
    _ = get_trans(user_id)
    if key == _('↩ Back'):
        return enter_state_shipping_method(bot, update, user_data)
    elif key == _('❌ Cancel'):
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif any(key in s for s in location_names):
        user_data['shipping']['pickup_location'] = key
        session_client.json_set(user_id, user_data)

        if user_data['shipping']['method'] == _('🚚 Delivery'):
            return enter_state_location_delivery(bot, update, user_data)
        else:
            return enter_state_shipping_time(bot, update, user_data)
    else:
        return enter_state_courier_location(bot, update, user_data)


def on_shipping_delivery_address(bot, update, user_data):
    key = update.message.text
    user_id = get_user_id(update)
    user_data = get_user_session(user_id)
    _ = get_trans(user_id)
    if key == _('↩ Back'):
        return enter_state_shipping_method(bot, update, user_data)
    elif key == _('❌ Cancel'):
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif key == _('✒️Enter location manually'):
        return BOT_STATE_CHECKOUT_LOCATION_DELIVERY
    else:
        try:
            location = update.message.location
        except AttributeError:
            location = update.message.text
        user_data['shipping']['location'] = location
        session_client.json_set(user_id, user_data)
        return enter_state_shipping_time(bot, update, user_data)


def on_checkout_time(bot, update, user_data):
    key = update.message.text
    user_id = get_user_id(update)
    user_data = get_user_session(user_id)
    _ = get_trans(user_id)
    if key == _('↩ Back'):
        return enter_state_shipping_method(bot, update, user_data)
    elif key == _('❌ Cancel'):
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif key == _('⏰ Now'):
        user_data['shipping']['time'] = key
        session_client.json_set(user_id, user_data)

        if config.get_phone_number_required():
            return enter_state_phone_number_text(bot, update, user_data)
        else:
            if config.get_identification_required():
                return enter_state_identify_photo(bot, update, user_data)
            else:
                return enter_state_order_confirm(bot, update, user_data)
    elif key == _('📅 Set time'):
        user_data['shipping']['time'] = key
        session_client.json_set(user_id, user_data)

        return enter_state_shipping_time_text(bot, update, user_data)
    else:
        logger.warn("Unknown input %s", key)
        return enter_state_shipping_time(bot, update, user_data)


def on_shipping_time_text(bot, update, user_data):
    key = update.message.text
    user_id = get_user_id(update)
    user_data = get_user_session(user_id)
    _ = get_trans(user_id)
    if key == _('↩ Back'):
        return enter_state_shipping_time(bot, update, user_data)
    elif key == _('❌ Cancel'):
        return enter_state_init_order_cancelled(bot, update, user_data)
    else:
        user_data['shipping']['time_text'] = key
        session_client.json_set(user_id, user_data)
        return enter_state_phone_number_text(bot, update, user_data)


def on_phone_number_text(bot, update, user_data):
    key = update.message.text
    user_id = get_user_id(update)
    user_data = get_user_session(user_id)
    _ = get_trans(user_id)
    if key == _('❌ Cancel'):
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif key == _('↩ Back'):
        return enter_state_shipping_time(bot, update, user_data)
    elif key == _('✒️Enter phone manually'):
        return BOT_STATE_CHECKOUT_PHONE_NUMBER_TEXT
    else:
        try:
            phone_number_text = update.message.contact.phone_number
        except AttributeError:
            phone_number_text = update.message.text
        user_data['shipping']['phone_number'] = phone_number_text
        session_client.json_set(user_id, user_data)
        user = User.get(telegram_id=user_id)
        user.phone_number = phone_number_text
        user.save()
        if is_vip_customer(bot, user_id):
            user_data['shipping']['vip'] = True
            session_client.json_set(user_id, user_data)

        if config.get_identification_required():
            return enter_state_identify_photo(bot, update, user_data)
        return enter_state_order_confirm(bot, update, user_data)


def on_shipping_identify_photo(bot, update, user_data):
    key = update.message.text
    user_id = get_user_id(update)
    user_data = get_user_session(user_id)
    _ = get_trans(user_id)
    if key == _('❌ Cancel'):
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif key == _('↩ Back'):
        if config.get_phone_number_required():
            return enter_state_phone_number_text(bot, update, user_data)
        else:
            return enter_state_shipping_time(bot, update, user_data)
    if update.message.photo:
        photo_file = bot.get_file(update.message.photo[-1].file_id)
        user_data['shipping']['photo_id'] = photo_file.file_id
        session_client.json_set(user_id, user_data)

        # check if vip and if 2nd id photo needed
        if config.get_identification_stage2_required():
            return enter_state_identify_stage2(bot, update, user_data)
        else:
            return enter_state_order_confirm(bot, update, user_data)
    else:
        # No photo, ask the user again
        return enter_state_identify_photo(bot, update, user_data)


def on_shipping_identify_stage2(bot, update, user_data):
    key = update.message.text
    user_id = get_user_id(update)
    user_data = get_user_session(user_id)
    _ = get_trans(user_id)
    if key == _('❌ Cancel'):
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif key == _('↩ Back'):
        return enter_state_identify_photo(bot, update, user_data)

    if update.message.photo:
        photo_file = bot.get_file(update.message.photo[-1].file_id)
        user_data['shipping']['stage2_id'] = photo_file.file_id
        session_client.json_set(user_id, user_data)

        return enter_state_order_confirm(bot, update, user_data)
    else:
        # No photo, ask the user again

        return enter_state_identify_stage2(bot, update, user_data)


def on_confirm_order(bot, update, user_data):
    key = update.message.text

    # order data
    user_id = get_user_id(update)
    username = get_username(update)
    user_data = get_user_session(user_id)
    locale = get_locale(update)
    _ = get_trans(user_id)
    if key == _('✅ Confirm'):
        shipping_data = user_data['shipping']
        is_pickup = shipping_data['method'] == _('🏪 Pickup')
        product_info = cart.get_products_info(user_data)
        total = cart.get_cart_total(user_data)
        delivery_cost = config.get_delivery_fee()
        delivery_min = config.get_delivery_min()

        try:
            user = User.get(telegram_id=user_id)
        except User.DoesNotExist:
            if not username:
                user = User.create(telegram_id=user_id, locale=locale)
            else:
                user = User.create(telegram_id=user_id, locale=locale, username=username)
        location = Location.get(
            title=shipping_data['pickup_location'])
        order = Order.create(user=user,
                             location=location,
                             shipping_method=DeliveryMethod.DELIVERY.value
                             if shipping_data['method'] == _('🚚 Delivery') else Order.shipping_method.default,
                             shipping_time=shipping_data['time'],
                             )
        order_id = order.id
        cart.fill_order(user_data, order)

        order_data = OrderPhotos(order=order)
        if 'photo_id' in shipping_data:
            order_data.photo_id = shipping_data['photo_id']
        if 'stage2_id' in shipping_data:
            order_data.stage2_id = shipping_data['stage2_id']

        text = create_service_notice(user_id, is_pickup, order_id, product_info, shipping_data,
                                     total, delivery_min, delivery_cost)
        order_data.order_text = text
        order_data.save()

        # ORDER CONFIRMED, send the details to service channel
        txt = _('Order confirmed by\n@{}\n').format(update.message.from_user.username)
        service_channel = config.get_service_channel()

        if 'location' in shipping_data:
            if hasattr(shipping_data['location'], 'latitude'):
                bot.send_location(
                    service_channel,
                    latitude=shipping_data['location']['latitude'],
                    longitude=shipping_data['location']['longitude'],
                )
        else:
            txt += 'From {}\n\n'.format(shipping_data['pickup_location'])

        service_channel = config.get_service_channel()
        bot.send_message(service_channel,
                         text=txt,
                         reply_markup=create_show_order_keyboard(user_id, order_id),
                         parse_mode=ParseMode.HTML,
                         )
        # clear cart and shipping data
        user_data['cart'] = {}
        user_data['shipping'] = {}
        session_client.json_set(user_id, user_data)
        return enter_state_init_order_confirmed(bot, update, user_data)

    elif key == _('❌ Cancel'):
        # ORDER CANCELLED, send nothing
        # and only clear shipping details
        user_data['shipping'] = {}
        session_client.json_set(user_id, user_data)

        return enter_state_init_order_cancelled(bot, update, user_data)
    elif key == _('↩ Back'):
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


def service_channel_sendto_courier_handler(bot, update, user_data):
    query = update.callback_query
    data = query.data
    label, telegram_id, order_id, message_id = data.split('|')
    order = Order.get(id=order_id)
    user_id = order.user.telegram_id
    bot.delete_message(chat_id=update.callback_query.message.chat_id,
                       message_id=update.callback_query.message.message_id, )
    bot.forward_message(chat_id=telegram_id,
                        from_chat_id=query.message.chat_id,
                        message_id=message_id,
                        reply_markup=create_service_notice_keyboard(user_id, order_id))

    query.answer(text='Message sent', show_alert=True)


def on_service_send_order_to_courier(bot, update, user_data):
    query = update.callback_query
    data = query.data
    label, user_id, order_id = data.split('|')
    _ = get_trans(user_id)
    if label == 'order_show':
        order = OrderPhotos.get(order_id=order_id)
        service_channel = config.get_service_channel()
        media = []
        if order.photo_id:
            media.append(InputMediaPhoto(media=order.photo_id,
                                         caption=_('Stage 1 Identification - Selfie')))

        if order.stage2_id:
            media.append(InputMediaPhoto(media=order.stage2_id,
                                         caption=_('Stage 2 Identification - FB')))
        if media:
            bot.send_media_group(service_channel,
                                 media=media)

        bot.delete_message(chat_id=update.callback_query.message.chat_id,
                           message_id=update.callback_query.message.message_id, )
        bot.send_message(
            chat_id=service_channel,
            text=order.order_text,
            parse_mode=ParseMode.HTML,
            reply_markup=create_service_channel_keyboard(user_id, order_id))
    elif label == 'order_hide':
        service_channel = config.get_service_channel()
        username = User.get(telegram_id=user_id).username or '№1'
        txt = _('Order confirmed by\n@{}\n').format(username)
        order = OrderPhotos.get(order_id=order_id)
        bot.delete_message(chat_id=update.callback_query.message.chat_id,
                           message_id=update.callback_query.message.message_id, )
        if order.photo_id:
            bot.delete_message(chat_id=update.callback_query.message.chat_id,
                               message_id=int(update.callback_query.message.message_id) - 1, )
        if order.stage2_id:
            bot.delete_message(chat_id=update.callback_query.message.chat_id,
                               message_id=int(update.callback_query.message.message_id) - 2, )

        bot.send_message(
            chat_id=service_channel,
            text=txt,
            reply_markup=create_show_order_keyboard(user_id, order_id))
    elif label == 'order_send_to_specific_courier':
        couriers = Courier.select(Courier.username, Courier.telegram_id, Courier.location)
        bot.send_message(
            chat_id=config.get_service_channel(),
            text=_('Please choose who to send'),
            reply_markup=couriers_choose_keyboard(couriers, order_id, update.callback_query.message.message_id),
        )
    elif label == 'order_send_to_couriers':

        if config.get_has_courier_option():
            couriers_channel = config.get_couriers_channel()
            order = OrderPhotos.get(order_id=order_id)
            bot.send_message(chat_id=couriers_channel,
                             text=order.order_text,
                             reply_markup=create_service_notice_keyboard(user_id, order_id),
                             parse_mode=ParseMode.HTML,
                             )

            if order.photo_id:
                bot.send_photo(couriers_channel,
                               photo=order.photo_id,
                               caption=_('Stage 1 Identification - Selfie'),
                               parse_mode=ParseMode.MARKDOWN, )

            query.answer(text='Order sent to couriers channel', show_alert=True)
        query.answer(text='You have disabled courier\'s option', show_alert=True)
    elif label == 'order_finished':

        order = OrderPhotos.get(order_id=order_id)
        bot.delete_message(chat_id=update.callback_query.message.chat_id,
                           message_id=update.callback_query.message.message_id, )
        if order.photo_id:
            bot.delete_message(chat_id=update.callback_query.message.chat_id,
                               message_id=int(update.callback_query.message.message_id) - 1, )
        if order.stage2_id:
            bot.delete_message(chat_id=update.callback_query.message.chat_id,
                               message_id=int(update.callback_query.message.message_id) - 2, )
    elif label == 'order_send_to_self':
        usr_id = get_user_id(update)
        bot.forward_message(chat_id=usr_id,
                            from_chat_id=query.message.chat_id,
                            message_id=query.message.message_id,
                            reply_markup=create_service_notice_keyboard(usr_id, order_id))
    elif label == 'order_ban_client':
        usr = User.get(telegram_id=user_id)
        username = usr.username
        banned = config.get_banned_users()
        if username not in banned:
            banned.append(username)
        config_session = get_config_session()
        config_session['banned'] = banned
        set_config_session(config_session)
        user_id = get_user_id(update)
        bot.send_message(chat_id=query.message.chat_id,
                         text='@{} was banned'.format(username),
                         parse_mode=ParseMode.MARKDOWN)
    elif label == 'order_add_to_vip':
        bul = is_vip_customer(bot, user_id)
        if bul:
            query.answer(text='Client is already VIP', show_alert=True)
        else:
            query.answer(text='You should no manually add this user to VIP, '
                              'while we working on API to do it via bot', show_alert=True)
    else:
        logger.info('that part is not handled yet')


def on_cancel(bot, update, user_data):
    return enter_state_init_order_cancelled(bot, update, user_data)


def checkout_fallback_command_handler(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    bot.answer_callback_query(query.id, text=_(
        'Cannot process commands when checking out'))


#
# handle couriers
#

def service_channel_courier_query_handler(bot, update, user_data):
    query = update.callback_query
    data = query.data
    courier_nickname = get_username(update)
    courier_id = get_user_id(update)
    label, user_id, order_id = data.split('|')
    _ = get_trans(user_id)
    try:
        if order_id:
            order = Order.get(id=order_id)
        else:
            raise Order.DoesNotExist()
    except Order.DoesNotExist:
        logger.info('Order №{} not found!'.format(order_id))
    else:
        try:
            courier = Courier.get(telegram_id=courier_id)
        except Courier.DoesNotExist:
            pass

        else:
            try:
                CourierLocation.get(courier=courier, location=order.location)
                order.courier = courier
                order.save()
                bot.delete_message(chat_id=config.get_couriers_channel(),
                                   message_id=query.message.message_id)
                bot.send_message(
                    config.get_couriers_channel(),
                    text=query.message.text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=create_drop_responsibility_keyboard(
                        user_id, courier_nickname, order_id),
                )
                bot.send_message(
                    config.get_service_channel(),
                    text='Courier: {}, apply for order №{}. '
                         'Confirm this?'.format(
                        courier_nickname, order_id),
                    reply_markup=create_courier_confirmation_keyboard(user_id,
                                                                      order_id, courier_nickname),
                )
                bot.answer_callback_query(
                    query.id,
                    text=_('Courier {} assigned').format(courier_nickname))
            except CourierLocation.DoesNotExist:
                bot.send_message(
                    config.get_couriers_channel(),
                    text='{} your location and customer locations are '
                         'different'.format(courier_nickname),
                    parse_mode=ParseMode.HTML
                )


def send_welcome_message(bot, update):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if str(update.message.chat_id) == config.get_couriers_channel():
        users = update.message.new_chat_members
        for user in users:
            if user:
                bot.send_message(
                    config.get_couriers_channel(),
                    text=_('Hello `@{}`\nID number `{}`').format(
                        user.username, user.id),
                    parse_mode=ParseMode.MARKDOWN)


def on_settings_menu(bot, update):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    total = cart.get_cart_total(get_user_session(user_id))
    _ = get_trans(user_id)
    if data == 'settings_statistics':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('📈 Statistics'),
                              reply_markup=create_statistics_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_STATISTICS
    elif data == 'settings_bot':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('⚙ Bot settings'),
                              reply_markup=create_bot_settings_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)

        query.answer()
        return ADMIN_BOT_SETTINGS

    elif data == 'settings_back':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=config.get_welcome_text().format(
                                  update.callback_query.from_user.first_name),
                              reply_markup=create_main_keyboard(user_id,
                                                                config.get_reviews_channel(),
                                                                is_admin(bot, user_id), total),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return BOT_STATE_INIT
    else:
        logger.info('Unknown command - {}'.format(data))
        bot.send_message(
            query.message.chat_id,
            text=_('Unknown command'),
            reply_markup=None,
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END


def on_statistics_menu(bot, update):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if data == 'statistics_back':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('⚙️ Settings'),
                              reply_markup=create_admin_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_MENU
    elif data == 'statistics_all_sells':
        orders_count = Order.select().where(Order.confirmed == True).count()
        total_price = 0
        orders_items = OrderItem.select().join(Order).where(
            Order.confirmed == True)
        for order_item in orders_items:
            total_price += order_item.count * order_item.total_price
        message = _('Total confirmed orders\n\ncount: {}\ntotal cost: {}').format(
            orders_count, total_price)
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=message,
                              reply_markup=create_statistics_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_STATISTICS
    elif data == 'statistics_couriers':
        msg = ''
        couriers = Courier.select()
        for courier in couriers:
            orders_count = Order.select().where(Order.courier == courier,
                                                Order.confirmed == True).count()
            total_price = 0
            orders_items = OrderItem.select().join(Order).where(
                Order.confirmed == True, Order.courier == courier)
            for order_item in orders_items:
                total_price += order_item.count * order_item.total_price
            msg += _('Courier: `@{}`\nOrders: {}, orders cost {}').format(
                courier.username, orders_count, total_price)
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_statistics_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_STATISTICS
    elif data == 'statistics_locations':
        msg = ''
        locations = Location.select()
        for location in locations:
            orders_count = Order.select().where(Order.location == location,
                                                Order.confirmed == True).count()
            total_price = 0
            orders_items = OrderItem.select().join(Order).where(
                Order.confirmed == True, Order.location == location)
            for order_item in orders_items:
                total_price += order_item.count * order_item.total_price
            msg += _('Location: {}\nOrders: {}, orders cost {}').format(
                location.title, orders_count, total_price)
            msg += '\n\n'
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_statistics_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_STATISTICS
    elif data == 'statistics_yearly':
        now = datetime.datetime.now()
        orders_count = Order.select().where(Order.date_created.year == now.year,
                                            Order.confirmed == True).count()
        total_price = 0
        orders_items = OrderItem.select().join(Order).where(
            Order.confirmed == True, Order.date_created.year == now.year)
        for order_item in orders_items:
            total_price += order_item.count * order_item.total_price
        msg = _('Orders: {}, orders cost {}').format(
            orders_count, total_price)
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_statistics_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_STATISTICS
    elif data == 'statistics_monthly':
        now = datetime.datetime.now()
        orders_count = Order.select().where(Order.date_created.year == now.month,
                                            Order.confirmed == True).count()
        total_price = 0
        orders_items = OrderItem.select().join(Order).where(
            Order.confirmed == True, Order.date_created.year == now.month)
        for order_item in orders_items:
            total_price += order_item.count * order_item.total_price
        msg = _('Orders: {}, orders cost {}').format(
            orders_count, total_price)
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_statistics_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_STATISTICS
    elif data == 'statistics_user':
        msg = ''
        users = User.select()
        for user in users:
            orders_count = Order.select().where(Order.user == user,
                                                Order.confirmed == True).count()
            total_price = 0
            orders_items = OrderItem.select().join(Order).where(
                Order.confirmed == True, Order.location == user)
            for order_item in orders_items:
                total_price += order_item.count * order_item.total_price
            msg += '\nUser: @{}, orders: {}, orders cost {}'.format(
                user.username, orders_count, total_price)
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_statistics_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_STATISTICS

    return ConversationHandler.END


def on_bot_settings_menu(bot, update):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if data == 'bot_settings_back':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('⚙️ Settings'),
                              reply_markup=create_admin_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_MENU

    elif data == 'bot_settings_couriers':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('🛵 Couriers'),
                              reply_markup=create_bot_couriers_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_COURIERS
    elif data == 'bot_settings_channels':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('✉️ Channels'),
                              reply_markup=create_bot_channels_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_CHANNELS
    elif data == 'bot_settings_order_options':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('💳 Order options'),
                              reply_markup=create_bot_order_options_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_ORDER_OPTIONS
    elif data == 'bot_settings_edit_working_hours':
        msg = _('Now:\n\n`{}`\n\n').format(config.get_working_hours())
        msg += _('Type new working hours')
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_back_button(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_EDIT_WORKING_HOURS
    elif data == 'bot_settings_ban_list':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text='Ban list',
                              reply_markup=create_ban_list_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_BAN_LIST
    elif data == 'bot_settings_edit_contact_info':
        msg = _('Now:\n\n`{}`\n\n').format(config.get_contact_info())
        msg += _('Type new contact info')
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_back_button(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_EDIT_CONTACT_INFO
    elif data == 'bot_settings_bot_on_off':
        bot_status = config.get_bot_on_off()
        bot_status = _('ON') if bot_status else _('OFF')
        msg = _('Bot status: {}').format(bot_status)
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_on_off_buttons(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_BOT_ON_OFF

    elif data == 'bot_settings_reset_all_data':
        set_config_session({})
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text='Config options were deleted',
                              reply_markup=create_bot_settings_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_BOT_SETTINGS

    return ConversationHandler.END


def on_admin_couriers(bot, update):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if data == 'bot_couriers_back':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('⚙ Bot settings'),
                              reply_markup=create_bot_settings_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_BOT_SETTINGS
    elif data == 'bot_couriers_view':
        msg = ''
        couriers = Courier.select()
        for courier in couriers:
            locations = CourierLocation.filter(courier=courier)
            locations = [item.location.title for item in locations]
            msg += _('name:\n`@{}`\n').format(courier.username)
            msg += _('courier ID:\n`{}`\n').format(courier.id)
            msg += _('telegram ID:\n`{}`\n').format(courier.telegram_id)
            msg += _('locations:\n{}\n').format(locations)
            # msg += _('locale:\n`{}`').format(courier.locale)
            msg += '~~~~~~\n\n'
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_bot_couriers_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_COURIERS
    elif data == 'bot_couriers_add':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('Enter new courier nickname'),
                              parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_back_button(user_id)
                              ),

        return ADMIN_TXT_COURIER_NAME
    elif data == 'bot_couriers_delete':

        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('Choose courier ID to delete'),
                              parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_back_button(user_id)
                              )

        return ADMIN_TXT_DELETE_COURIER

    return ConversationHandler.END


def on_admin_channels(bot, update):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if data == 'bot_channels_back':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('⚙ Bot settings'),
                              reply_markup=create_bot_settings_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_BOT_SETTINGS
    elif data == 'bot_channels_view':
        # msg = u'Reviews channel: {}'.format(config.get_reviews_channel())
        msg = _('Service channel ID:\n`{}`\n\n').format(config.get_service_channel())
        msg += _('Customer channel:\n`@{}`\n\n').format(config.get_customers_channel())
        msg += _('Vip customer channel ID:\n`{}`\n\n').format(
            config.get_vip_customers_channel())
        msg += _('Courier group ID:\n`{}`\n\n').format(config.get_couriers_channel())

        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_bot_channels_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_CHANNELS
    elif data == 'bot_channels_add':
        types = [_('Service Channel'), _('Customer Channel'), _('Vip Customer Channel'), _('Courier Channel')]
        msg = ''
        for i, channel_type in enumerate(types, start=1):
            msg += '\n{} - {}'.format(i, channel_type)
        msg += _('\n\nSelect channel type')
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_back_button(user_id)
                              )

        return ADMIN_CHANNELS_SELECT_TYPE
    elif data == 'bot_channels_remove':
        types = [_('Service Channel'), _('Customer Channel'), _('Vip Customer Channel'), _('Couriers Channel')]
        msg = ''
        for i, channel_type in enumerate(types, start=1):
            msg += '\n{} - {}'.format(i, channel_type)
        msg += _('\n\nSelect channel type')
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_back_button(user_id)
                              )

        return ADMIN_CHANNELS_REMOVE

    return ConversationHandler.END


def on_admin_ban_list(bot, update):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if data == 'bot_ban_list_back':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('⚙ Bot settings'),
                              reply_markup=create_bot_settings_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_BOT_SETTINGS
    elif data == 'bot_ban_list_view':
        banned = config.get_banned_users()
        banned = ['@{}'.format(ban) for ban in banned]
        msg = ', '.join(banned)
        msg = 'Banned users: {}'.format(msg)
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_ban_list_keyboard(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return ADMIN_BAN_LIST
    elif data == 'bot_ban_list_remove':
        msg = 'Type username: @username or username'
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_back_button(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        return ADMIN_BAN_LIST_REMOVE
    elif data == 'bot_ban_list_add':
        msg = 'Type username: @username or username'
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_back_button(user_id),
                              parse_mode=ParseMode.MARKDOWN)
        return ADMIN_BAN_LIST_ADD

    return ConversationHandler.END
