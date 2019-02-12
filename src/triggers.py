import random
import re

from telegram import ParseMode
from telegram.ext import ConversationHandler

from .admin import is_admin
from .messages import create_service_notice, create_product_description, create_cart_details_msg
from .helpers import cart, config, session_client, get_user_session, \
    get_user_id, get_username, is_vip_customer, set_config_session, get_locale, get_trans, get_config_session, \
    get_channel_trans
from .keyboards import create_courier_assigned_keyboard, \
    create_service_notice_keyboard, create_main_keyboard, create_courier_confirmation_keyboard, \
    create_admin_keyboard, create_statistics_keyboard, \
    create_bot_settings_keyboard, create_bot_couriers_keyboard, \
    create_bot_channels_keyboard, create_bot_order_options_keyboard, \
    create_back_button, create_on_off_buttons, create_ban_list_keyboard, create_show_order_keyboard, \
    create_service_channel_keyboard, couriers_choose_keyboard, create_are_you_sure_keyboard, \
    create_courier_order_status_keyboard, create_admin_order_status_keyboard, general_select_one_keyboard, \
    create_calendar_keyboard, create_my_orders_keyboard, create_my_order_keyboard, create_bot_language_keyboard, \
    create_product_keyboard, create_ping_client_keyboard, create_add_courier_keyboard, create_cancel_keyboard, \
    create_cancel_order_confirm, create_reset_all_data_keyboard
from .models import User, Courier, Order, OrderItem, Location, CourierLocation, DeliveryMethod, OrderPhotos, \
    ProductCategory, Product, IdentificationStage, OrderIdentificationAnswer, IdentificationQuestion
from .states import enter_state_init_order_cancelled, enter_state_courier_location, enter_state_shipping_method, \
    enter_state_location_delivery, enter_state_shipping_time, enter_state_phone_number_text, \
    enter_state_order_confirm, enter_state_shipping_time_text, \
    enter_state_init_order_confirmed
from . import enums

from . import shortcuts


def cancel_process(bot, update):
    user_id = get_user_id(update)

    if is_admin(bot, user_id):
        enums.logger.info('Admin Cancel order process - From admin_id: %s, username: @%s',
                          update.effective_user.id,
                          update.effective_user.username)
    else:
        enums.logger.info('Cancel order process - From user_id: %s, username: @%s',
                          update.effective_user.id,
                          update.effective_user.username)


def on_my_orders(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    data = query.data
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    if data == 'back':
        user = User.get(telegram_id=user_id)
        total = cart.get_cart_total(get_user_session(user_id))
        user_data = get_user_session(user_id)
        products_info = cart.get_products_info(user_data)
        if products_info:
            msg = create_cart_details_msg(user_id, products_info)
        else:
            msg = config.get_welcome_text().format(update.effective_user.first_name)
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=msg,
                              reply_markup=create_main_keyboard(_, config.get_reviews_channel(), user, is_admin(bot, user_id), total),
                              parse_mode=ParseMode.MARKDOWN)
        return enums.BOT_STATE_INIT
    elif data == 'by_date':
        state = enums.BOT_STATE_MY_ORDER_DATE
        shortcuts.initialize_calendar(bot, user_data, chat_id, message_id, state, _, query.id)
        return state
    elif data == 'last_order':
        user = User.get(telegram_id=user_id)
        last_order = Order.select().where(Order.user == user).order_by(Order.date_created.desc()).get()
        msg = _('Order №{}').format(last_order.id)
        keyboard = create_my_order_keyboard(last_order.id, not last_order.delivered and not last_order.canceled, _)
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg,
                              reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.BOT_STATE_MY_LAST_ORDER


def on_my_order_date(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action, val = query.data.split('|')
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    if action == 'ignore':
        return enums.BOT_STATE_MY_ORDER_DATE
    elif action == 'back':
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=_('📖 My Orders'),
                              reply_markup=create_my_orders_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.BOT_STATE_MY_ORDERS
    elif action in ('day', 'month', 'year'):
        year, month = user_data['calendar_date']
        queries = shortcuts.get_order_subquery(action, val, month, year)
        user = User.get(telegram_id=user_id)
        queries.append(Order.user == user)
        orders = Order.select().where(*queries)
        if len(orders) == 1:
            order = orders[0]
            msg = _('Order №{}').format(order.id)
            keyboard = create_my_order_keyboard(order.id, not order.delivered and not order.canceled, _)
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg,
                                  reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
            query.answer()
            return enums.BOT_STATE_MY_LAST_ORDER
        else:
            orders_data = [(order.id, order.date_created.strftime('%d/%m/%Y')) for order in orders]
            orders = [(_('Order №{} {}').format(order_id, order_date), order_id) for order_id, order_date in orders_data]
            user_data['my_orders_by_date'] = orders_data
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=_('Select order'),
                                  reply_markup=general_select_one_keyboard(_, orders),
                                  parse_mode=ParseMode.MARKDOWN)
            query.answer()
            return enums.BOT_STATE_MY_ORDER_SELECT


def on_my_order_select(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action, val = query.data.split('|')
    chat_id, message_id = query.message.chat_id, query.message.message_id
    if action == 'back':
        state = enums.BOT_STATE_MY_ORDER_DATE
        shortcuts.initialize_calendar(bot, user_data, chat_id, message_id, state, _, query.id)
        return state
    elif action == 'page':
        current_page = int(val)
        orders = [(_('Order №{} {}').format(order_id, order_date), order_id) for order_id, order_date in user_data['my_orders_by_date']]
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=_('Select order:'),
                              reply_markup=general_select_one_keyboard(_, orders, current_page),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.BOT_STATE_MY_ORDER_SELECT
    else:
        order = Order.get(id=val)
        msg = _('Order №{}').format(order.id)
        keyboard = create_my_order_keyboard(order.id, not order.delivered and not order.canceled, _)
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg,
                              reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.BOT_STATE_MY_LAST_ORDER


def on_my_last_order(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action, val = query.data.split('|')
    chat_id, message_id = query.message.chat_id, query.message.message_id
    if action == 'back':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('📖 My Orders'),
                              reply_markup=create_my_orders_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.BOT_STATE_MY_ORDERS
    order_id = int(val)
    order = Order.get(id=order_id)
    if action == 'cancel':
        if not order.delivered and not order.canceled:
            msg = _('Are you sure?')
            mapping = {'yes': 'yes|{}'.format(order_id), 'no': 'no|{}'.format(order_id)}
            bot.edit_message_text(msg, chat_id, message_id, parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=create_are_you_sure_keyboard(_, mapping))
            query.answer()
            return enums.BOT_STATE_MY_LAST_ORDER_CANCEL
        else:
            query.answer(text=_('Cannot cancel - order was delivered'), show_alert=True)
            return enums.BOT_STATE_MY_LAST_ORDER
    elif action == 'show':
        order_data = OrderPhotos.get(order=order)
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=order_data.order_text,
                              reply_markup=create_my_order_keyboard(order_id, not order.delivered, _),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.BOT_STATE_MY_LAST_ORDER


def on_my_last_order_cancel(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    username = get_username(update)
    _ = get_trans(user_id)
    action, val = query.data.split('|')
    chat_id, msg_id = query.message.chat_id, query.message.message_id
    order = Order.get(id=val)
    if action == 'yes':
        order.confirmed = True
        order.canceled = True
        order.delivered = True
        order.save()
        service_chat = config.get_service_channel()
        channel_trans = get_channel_trans()
        msg = channel_trans('Order was cancelled by user')
        shortcuts.bot_send_order_msg(bot, service_chat, msg, channel_trans, order.id, channel=True)
        enums.logger.info('Order № %s was cancelled by user: @%s', order.id, username)
        msg = _('Order №{} was cancelled by the client @{}').format(order.id, username)
    elif action == 'no':
        msg = _('Order №{}').format(order.id)
    bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=msg,
                          reply_markup=create_my_order_keyboard(order.id, not order.delivered, _),
                          parse_mode=ParseMode.MARKDOWN)
    query.answer()
    return enums.BOT_STATE_MY_LAST_ORDER


def on_shipping_method(bot, update, user_data):
    key = update.message.text
    user_id = get_user_id(update)
    user_data = get_user_session(user_id)
    _ = get_trans(user_id)
    if key == _('❌ Cancel'):
        cancel_process(bot, update)
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif key == _('🏪 Pickup') or key == _('🚚 Delivery'):
        user_data['shipping']['method'] = key
        session_client.json_set(user_id, user_data)
        if not Location.select().exists():
            return enter_state_location_delivery(bot, update, user_data)
        else:
            return enter_state_courier_location(bot, update, user_data)
    else:
        return enter_state_shipping_method(bot, update, user_data)


def on_bot_language_change(bot, update, user_data):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    user_data = get_user_session(user_id)
    if data == 'iw' or data == 'en':
        user_data['locale'] = data
        session_client.json_set(user_id, user_data)
        user = User.get(telegram_id=user_id)
        user.locale = data
        user.save()
        _ = get_trans(user_id)
        user_data = get_user_session(user_id)
        products_info = cart.get_products_info(user_data)
        if products_info:
            msg = create_cart_details_msg(user_id, products_info)
        else:
            msg = config.get_welcome_text().format(update.effective_user.first_name)
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_main_keyboard(_, config.get_reviews_channel(), user,
                                                                is_admin(bot, user_id)),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.BOT_STATE_INIT
    else:
        enums.logger.info('Unknown command - {}'.format(data))
        bot.send_message(
            query.message.chat_id,
            text='Unknown command',
            reply_markup=None,
            parse_mode=ParseMode.MARKDOWN,
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
        cancel_process(bot, update)
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
        cancel_process(bot, update)
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif key == _('✒️Enter location manually'):
        return enums.BOT_STATE_CHECKOUT_LOCATION_DELIVERY
    else:
        try:
            location = update.message.location
            loc = {'latitude': location['latitude'], 'longitude': location['longitude']}
            location = loc
            user_data['shipping']['geo_location'] = location
        except TypeError:
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
        cancel_process(bot, update)
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif key == _('⏰ Now'):
        user_data['shipping']['time'] = key
        session_client.json_set(user_id, user_data)

        if config.get_phone_number_required():
            return enter_state_phone_number_text(bot, update, user_data)
        else:
            identification_stages = IdentificationStage.filter(active=True)
            if is_vip_customer(bot, user_id):
                identification_stages = identification_stages.filter(vip_required=True)
            if len(identification_stages):
                first_stage = identification_stages[0]
                questions = first_stage.identification_questions
                question = random.choice(list(questions))
                user_data['order_identification'] = {'passed_ids': [], 'current_id': first_stage.id, 'current_q_id': question.id, 'answers': []}
                session_client.json_set(user_id, user_data)
                msg = question.content
                bot.send_message(update.message.chat_id, msg, reply_markup=create_cancel_keyboard(_),
                                 parse_mode=ParseMode.MARKDOWN)
                return enums.BOT_STATE_CHECKOUT_IDENTIFY
            else:
                return enter_state_order_confirm(bot, update, user_data)
    elif key == _('📅 Set time'):
        user_data['shipping']['time'] = key
        session_client.json_set(user_id, user_data)

        return enter_state_shipping_time_text(bot, update, user_data)
    else:
        enums.logger.warn("Unknown input %s", key)
        return enter_state_shipping_time(bot, update, user_data)


def on_shipping_time_text(bot, update, user_data):
    key = update.message.text
    user_id = get_user_id(update)
    user_data = get_user_session(user_id)
    _ = get_trans(user_id)
    if key == _('↩ Back'):
        return enter_state_shipping_time(bot, update, user_data)
    elif key == _('❌ Cancel'):
        cancel_process(bot, update)
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
        cancel_process(bot, update)
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif key == _('↩ Back'):
        return enter_state_shipping_time(bot, update, user_data)
    elif key == _('✒️Enter phone manually'):
        return enums.BOT_STATE_CHECKOUT_PHONE_NUMBER_TEXT
    else:
        try:
            phone_number_text = update.message.contact.phone_number
        except AttributeError:
            phone_number_text = update.message.text
            match = re.search(r'(\+?\d{1,3})?\d{7,13}', phone_number_text)
            if not match:
                error_msg = _('✒️ Please enter correct phone number')
                bot.send_message(update.message.chat_id, error_msg)
                return enums.BOT_STATE_CHECKOUT_PHONE_NUMBER_TEXT

        user_data['shipping']['phone_number'] = phone_number_text
        session_client.json_set(user_id, user_data)
        user = User.get(telegram_id=user_id)
        user.phone_number = phone_number_text
        user.save()
        identification_stages = IdentificationStage.filter(active=True)
        if is_vip_customer(bot, user_id):
            identification_stages = identification_stages.filter(vip_required=True)
        else:
            identification_stages = identification_stages.filter(vip_required=False)
        if len(identification_stages):
            first_stage = identification_stages[0]
            questions = first_stage.identification_questions
            question = random.choice(list(questions))
            user_data['order_identification'] = {'passed_ids': [], 'current_id': first_stage.id, 'current_q_id': question.id,'answers': []}
            session_client.json_set(user_id, user_data)
            msg = question.content
            bot.send_message(update.message.chat_id, msg, reply_markup=create_cancel_keyboard(_),
                             parse_mode=ParseMode.MARKDOWN)
            return enums.BOT_STATE_CHECKOUT_IDENTIFY
        return enter_state_order_confirm(bot, update, user_data)


def on_identify_general(bot, update, user_data):
    key = update.message.text
    user_id = get_user_id(update)
    user_data = get_user_session(user_id)
    _ = get_trans(user_id)
    data = user_data['order_identification']
    if key == _('❌ Cancel'):
        cancel_process(bot, update)
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif key == _('↩ Back'):
        passed_ids = data['passed_ids']
        if passed_ids:
            prev_stage, prev_q = passed_ids.pop()
            data['current_id'] = prev_stage
            data['current_q_id'] = prev_q
            session_client.json_set(user_id, user_data)
            msg = IdentificationQuestion.get(id=prev_q).content
            bot.send_message(update.message.chat_id, msg, reply_markup=create_cancel_keyboard(_),
                             parse_mode=ParseMode.MARKDOWN)
            return enums.BOT_STATE_CHECKOUT_IDENTIFY
        elif config.get_phone_number_required():
            return enter_state_phone_number_text(bot, update, user_data)
        else:
            return enter_state_shipping_time(bot, update, user_data)
    current_id = data['current_id']
    current_stage = IdentificationStage.get(id=current_id)
    if current_stage.type in ('photo', 'video'):
        try:
            if current_stage.type == 'photo':
                answer = update.message.photo
                answer = answer[-1].file_id
            else:
                answer = update.message.video
                answer = answer.file_id
        except (IndexError, AttributeError):
            text = _(current_stage.type)
            msg = _('_Please upload a {} as an answer_').format(text)
            bot.send_message(update.message.chat_id, msg, reply_markup=create_cancel_keyboard(_),
                             parse_mode=ParseMode.MARKDOWN)
            return enums.BOT_STATE_CHECKOUT_IDENTIFY
    else:
        answer = key
    current_q_id = data['current_q_id']
    data['answers'].append((current_id, current_q_id, answer))
    passed_ids = data['passed_ids']
    passed_ids.append((current_id, current_q_id))
    passed_stages_ids = [v[0] for v in passed_ids]
    stages_left = IdentificationStage.select().where(IdentificationStage.active == True & IdentificationStage.id.not_in(passed_stages_ids))
    if is_vip_customer(bot, user_id):
        stages_left = stages_left.filter(vip_required=True)
        user_data['shipping']['vip'] = True
    session_client.json_set(user_id, user_data)
    if stages_left:
        next_stage = stages_left[0]
        questions = next_stage.identification_questions
        question = random.choice(list(questions))
        data['current_id'] = next_stage.id
        data['current_q_id'] = question.id
        session_client.json_set(user_id, user_data)
        msg = question.content
        bot.send_message(update.message.chat_id, msg, reply_markup=create_cancel_keyboard(_),
                         parse_mode=ParseMode.MARKDOWN)
        return enums.BOT_STATE_CHECKOUT_IDENTIFY
    else:
        return enter_state_order_confirm(bot, update, user_data)


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
        delivery_for_vip = config.get_delivery_fee_for_vip()
        try:
            user = User.get(telegram_id=user_id)
            if username != user.username:
                user.username = username
                user.save()
        except User.DoesNotExist:
            if not username:
                user = User.create(telegram_id=user_id, locale=locale)
            else:
                user = User.create(telegram_id=user_id, locale=locale, username=username)
        pickup_location = shipping_data.get('pickup_location')
        if pickup_location:
            location = Location.get(
                title=pickup_location)
        else:
            location = None
        order = Order.create(user=user,
                             location=location,
                             shipping_method=DeliveryMethod.DELIVERY.value
                             if shipping_data['method'] == _('🚚 Delivery') else Order.shipping_method.default,
                             shipping_time=shipping_data['time'],
                             )
        _ = get_channel_trans()
        customer_username = user.username
        order_id = order.id
        enums.logger.info('New order confirmed  - Order №%s, From user_id %s, username: @%s',
                          order_id,
                          update.effective_user.id,
                          update.effective_user.username)
        text = create_service_notice(_, is_pickup, order_id, customer_username, product_info, shipping_data,
                                     total, delivery_for_vip)
        if 'order_identification' in user_data:
            for stage_id, q_id, answer in user_data['order_identification']['answers']:
                stage = IdentificationStage.get(id=stage_id)
                question = IdentificationQuestion.get(id=q_id)
                OrderIdentificationAnswer.create(stage=stage, question=question, order=order, content=answer)

        # ORDER CONFIRMED, send the details to service channel
        user_name = order.user.username
        if location:
            location = location.title
        else:
            location = '-'
        txt = _('Order №{}, Location {}\nUser @{}').format(order_id, location, user_name)
        service_channel = config.get_service_channel()

        shipping_geo_location = shipping_data.get('geo_location')
        coordinates = None
        if shipping_geo_location:
            coordinates = '|'.join(map(str, shipping_geo_location.values())) + '|'

        cart.fill_order(user_data, order)
        order_data = OrderPhotos(order=order, coordinates=coordinates, order_text=text)
        shortcuts.bot_send_order_msg(bot, service_channel, txt, _, order_id, order_data, channel=True)
        user_data['cart'] = {}
        user_data['shipping'] = {}
        session_client.json_set(user_id, user_data)
        return enter_state_init_order_confirmed(bot, update, user_data)

    elif key == _('❌ Cancel'):
        # ORDER CANCELLED, send nothing
        # and only clear shipping details
        user_data['shipping'] = {}
        try:
            del user_data['order_identification']
        except KeyError:
            pass
        session_client.json_set(user_id, user_data)
        cancel_process(bot, update)
        return enter_state_init_order_cancelled(bot, update, user_data)
    elif key == _('↩ Back'):
        identification_stages = IdentificationStage.filter(active=True)
        if len(identification_stages):
            last_stage_id = user_data['order_identification']['current_id']
            last_stage = IdentificationStage.get(id=last_stage_id)
            last_q_id = user_data['order_identification']['current_q_id']
            last_question = IdentificationQuestion.get(id=last_q_id)
            msg = last_question.content
            bot.send_message(update.message.chat_id, msg, reply_markup=create_cancel_keyboard(_),
                             parse_mode=ParseMode.MARKDOWN)
            return enums.BOT_STATE_CHECKOUT_IDENTIFY
        elif config.get_phone_number_required():
            return enter_state_phone_number_text(bot, update, user_data)
        else:
            return enter_state_shipping_time(bot, update, user_data)
    else:
        enums.logger.warn("Unknown input %s", key)


def service_channel_sendto_courier_handler(bot, update, user_data):
    query = update.callback_query
    data = query.data
    label, telegram_id, order_id, message_id = data.split('|')
    order = Order.get(id=order_id)
    user_id = get_user_id(update)
    _ = get_channel_trans()
    courier = Courier.get(telegram_id=telegram_id)
    msg = shortcuts.check_order_products_credits(order, _, courier)
    if msg:
        bot.send_message(user_id, msg, parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return
    order.confirmed = True
    order.courier = Courier.get(telegram_id=telegram_id)
    shortcuts.change_order_products_credits(order, courier=order.courier)
    order.save()
    user_data = get_user_session(telegram_id)
    user_data['courier']['order_id'] = order_id
    session_client.json_set(telegram_id, user_data)
    order_data = OrderPhotos.get(order=order)
    shortcuts.delete_channel_msg(bot, update.callback_query.message.chat_id, update.callback_query.message.message_id)
    _ = get_trans(telegram_id)
    bot.send_message(chat_id=telegram_id,
                     text=order_data.order_text,
                     reply_markup=create_courier_order_status_keyboard(_, order_id),
                     parse_mode=ParseMode.MARKDOWN)
    query.answer(text=_('Message sent'), show_alert=True)


def on_service_send_order_to_courier(bot, update, user_data):
    query = update.callback_query
    data = query.data
    label, order_id = data.split('|')
    chat_id, msg_id = query.message.chat_id, query.message.message_id
    if label == 'order_show':
        order_data = OrderPhotos.get(order_id=order_id)
        _ = get_channel_trans()
        order = Order.get(id=order_id)
        shortcuts.send_order_identification_answers(bot, chat_id, order, channel=True)
        try:
            shortcuts.delete_channel_msg(bot, chat_id, msg_id)
        except Exception as e:
            enums.logger.exception("Failed to delete message\nException: " + str(e))
        if order_data.coordinates:
            lat, long, msg_id = order_data.coordinates.split('|')
            coords_msg_id = shortcuts.send_channel_location(bot, chat_id, lat, long)
            order_data.coordinates = lat + '|' + long + '|' + coords_msg_id
        keyboard = create_service_channel_keyboard(_, order_id)
        msg_id = shortcuts.send_channel_msg(bot, order_data.order_text, chat_id, keyboard, order)
        order_data.order_text_msg_id = msg_id
        order_data.save()
    elif label == 'order_hide':
        _ = get_channel_trans()
        order_data = OrderPhotos.get(order_id=order_id)
        if order_data.order.canceled is True:
            txt = _('Order №{} was cancelled by the client @{}').format(order_data.order_id, order_data.order.user.username)
        else:
            txt = order_data.order_hidden_text
        shortcuts.delete_channel_msg(bot, chat_id, msg_id)
        if order_data.coordinates:
            coord1, coord2, msg_id = order_data.coordinates.split('|')
            shortcuts.delete_channel_msg(bot, chat_id, msg_id)
        for answer in order_data.order.identification_answers:
            answer_msg_id = answer.msg_id
            if answer_msg_id:
                shortcuts.delete_channel_msg(bot, chat_id, msg_id)

        shortcuts.bot_send_order_msg(bot, update.callback_query.message.chat_id, txt, _, order_id, order_data.order, channel=True)

    elif label == 'order_send_to_specific_courier':
        _ = get_channel_trans()
        order = Order.get(id=order_id)
        if order.delivered:
            msg = _('Order is delivered. Cannot send it to couriers again.')
            query.answer(text=msg, show_alert=True)
            return
        couriers = Courier.select(Courier.username, Courier.telegram_id, Courier.location)
        msg = _('Please choose who to send')
        keyboard = couriers_choose_keyboard(_, couriers, order_id, update.callback_query.message.message_id)
        shortcuts.send_channel_msg(bot, msg, config.get_service_channel(), keyboard, order)
        query.answer()
    elif label == 'order_send_to_couriers':
        _ = get_channel_trans()
        if config.get_has_courier_option():
            order = Order.get(id=order_id)
            _ = get_channel_trans()
            if order.delivered:
                msg = _('Order is delivered. Cannot send it to couriers again.')
                query.answer(text=msg, show_alert=True)
            else:
                couriers_channel = config.get_couriers_channel()
                order_data = OrderPhotos.get(order_id=order_id)
                answers_ids = shortcuts.send_order_identification_answers(bot, couriers_channel, order, send_one=True, channel=True)
                if len(answers_ids) > 1:
                    answers_ids = ','.join(answers_ids)
                order_info = Order.get(id=order_id)
                order_pickup_state = order_info.shipping_method
                order_location = order_info.location
                if order_location:
                    order_location = order_location.title
                keyboard = create_service_notice_keyboard(order_id, _, answers_ids, order_location, order_pickup_state)
                shortcuts.send_channel_msg(bot, order_data.order_text, couriers_channel, keyboard, order)
                query.answer(text=_('Order sent to couriers channel'), show_alert=True)

        query.answer(text=_('You have disabled courier\'s option'), show_alert=True)
    elif label == 'order_finished':
        order = Order.get(id=order_id)
        if not order.delivered:
            _ = get_channel_trans()
            not_delivered_msg = _('Order cannot be finished because it was not delivered yet')
            query.answer(text=not_delivered_msg, show_alert=True)
        else:
            shortcuts.delete_order_channels_msgs(bot, order)
    elif label == 'order_cancel':
        order = Order.get(id=order_id)
        _ = get_channel_trans()
        if order.canceled:
            msg = _('Order is cancelled already')
            query.answer(text=msg, show_alert=True)
        else:
            msg = _('Are you sure?')
            keyboard = create_cancel_order_confirm(_, order_id)
            shortcuts.send_channel_msg(update.callback_query.message.chat_id, msg, keyboard, order)
            query.answer()
    elif label == 'order_send_to_self':
        order = Order.get(id=order_id)
        _ = get_channel_trans()
        if order.delivered:
            msg = _('Order is delivered. Cannot send it to couriers again.')
            query.answer(text=msg, show_alert=True)
            return
        usr_id = get_user_id(update)
        order = Order.get(id=order_id)
        _ = get_trans(usr_id)
        order_data = OrderPhotos.get(order=order)
        order.courier = User.get(telegram_id=usr_id)
        order.confirmed = True
        order.save()
        bot.send_message(chat_id=usr_id,
                         text=order_data.order_text,
                         reply_markup=create_admin_order_status_keyboard(_, order_id),
                         parse_mode=ParseMode.MARKDOWN)
        query.answer(text=_('Message sent'), show_alert=True)
    elif label == 'order_ban_client':
        order = Order.get(id=order_id)
        usr = order.usr
        username = usr.username
        banned = config.get_banned_users()
        if username not in banned:
            banned.append(username)
        config_session = get_config_session()
        config_session['banned'] = banned
        set_config_session(config_session)
        usr_id = get_user_id(update)
        _ = get_trans(usr_id)
        msg = _('@{} was banned').format(username)
        shortcuts.send_channel_msg(bot, msg, query.message.chat_id, order=order)
    elif label == 'order_add_to_vip':
        order = Order.get(id=order_id)
        user_id = order.user.telegram_id
        _ = get_trans(user_id)
        bul = is_vip_customer(bot, user_id)
        if bul:
            query.answer(text=_('Client is already VIP'), show_alert=True)
        else:
            query.answer(text=_('You should no manually add this user to VIP, '
                                'while we working on API to do it via bot'), show_alert=True)
    else:
        enums.logger.info('that part is not handled yet')


def cancel_order_confirm(bot, update):
    query = update.callback_query
    chat_id, msg_id = query.message.chat_id, query.message.message_id
    _ = get_channel_trans()
    action, order_id = query.data.split('|')
    if action == 'cancel_order_no':
        shortcuts.delete_channel_msg(bot, chat_id, msg_id)
    if action in ('cancel_order_yes', 'cancel_order_delete'):
        order = Order.get(Order.id == order_id)
        order.canceled = True
        order.confirmed = True
        order.delivered = True
        order.save()
        shortcuts.delete_channel_msg(bot, chat_id, msg_id)
    if action == 'cancel_order_delete':
        shortcuts.delete_order_channels_msgs(bot, order)


def delete_message(bot, update):
    query = update.callback_query
    chat_id, msg_id = query.message.chat_id, query.message.message_id
    shortcuts.delete_channel_msg(bot, chat_id, msg_id)
    query.answer()


def on_cancel(bot, update, user_data):
    return enter_state_init_order_cancelled(bot, update, user_data)


def checkout_fallback_command_handler(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    bot.answer_callback_query(query.id,
                              text=_('Cannot process commands when checking out'),
                              show_alert=True)


def service_channel_courier_query_handler(bot, update, user_data):
    query = update.callback_query
    data = query.data
    courier_nickname = get_username(update)
    courier_id = get_user_id(update)
    label, order_id, answers_ids = data.split('|')
    _ = get_channel_trans()
    try:
        if order_id:
            order = Order.get(id=order_id)
        else:
            raise Order.DoesNotExist()
    except Order.DoesNotExist:
        enums.logger.info('Order №{} not found!'.format(order_id))
    else:
        try:
            courier = Courier.get(telegram_id=courier_id)
        except Courier.DoesNotExist:
            query.answer(
                text=_('Courier: {}\nID: {}\nCourier not found, please contact admin').format(courier_nickname, courier_id),
                show_alert=True)
        else:
            if order.location:
                try:
                    CourierLocation.get(courier=courier, location=order.location)
                except CourierLocation.DoesNotExist:
                    query.answer(
                        text=_('{}\n your location and customer locations are different').format(courier_nickname),
                        show_alert=True)
                    return
            courier_trans = get_trans(courier_id)
            msg = shortcuts.check_order_products_credits(order, courier_trans, courier)
            if msg is str:
                bot.send_message(courier_id, msg, parse_mode=ParseMode.MARKDOWN)
                query.answer(text=_('Can\'t take responsibility for order'), show_alert=True)
                return
            order.courier = courier
            order.save()
            if not msg:
                shortcuts.change_order_products_credits(order, courier=courier)
            couriers_channel = config.get_couriers_channel()
            shortcuts.delete_channel_msg(bot, couriers_channel, query.message.message_id)
            keyboard = create_courier_assigned_keyboard(courier_nickname, order_id, _)
            assigned_msg_id = shortcuts.send_channel_msg(bot, query.message.text, couriers_channel, keyboard, order)
            msg = _('Courier: @{}, apply for order №{}.\nConfirm this?').format(courier_nickname, order_id)
            keyboard = create_courier_confirmation_keyboard(order_id, courier_nickname, _, answers_ids, assigned_msg_id)
            shortcuts.send_channel_msg(bot, msg, config.get_service_channel(), keyboard, order)
            bot.answer_callback_query(query.id, text=_('Courier {} assigned').format(courier_nickname), show_alert=True)


def send_welcome_message(bot, update):
    user_id = get_user_id(update)
    _ = get_channel_trans()
    if str(update.message.chat_id) == config.get_couriers_channel():
        users = update.message.new_chat_members
        for user in users:
            if user:
                try:
                    Courier.get(telegram_id=user.id)
                except Courier.DoesNotExist:
                    Courier.create(username=user.username, telegram_id=user.id, is_active=False)
                msg = _('Hello `@{}`').format(user.username)
                shortcuts.send_channel_msg(bot, msg, config.get_couriers_channel())


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
                              reply_markup=create_statistics_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_STATISTICS
    elif data == 'settings_bot':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('⚙ Bot settings'),
                              reply_markup=create_bot_settings_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)

        query.answer()
        return enums.ADMIN_BOT_SETTINGS

    elif data == 'settings_back':
        user = User.get(telegram_id=user_id)
        user_data = get_user_session(user_id)
        products_info = cart.get_products_info(user_data)
        if products_info:
            msg = create_cart_details_msg(user_id, products_info)
        else:
            msg = config.get_welcome_text().format(update.effective_user.first_name)
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_main_keyboard(_,
                                                                config.get_reviews_channel(),
                                                                user,
                                                                is_admin(bot, user_id), total),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.BOT_STATE_INIT
    else:
        enums.logger.info('Unknown command - {}'.format(data))
        bot.send_message(
            query.message.chat_id,
            text=_('Unknown command'),
            reply_markup=None,
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END


def on_statistics_general(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action, val = query.data.split('|')
    chat_id, message_id = query.message.chat_id, query.message.message_id
    if action == 'back':
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=_('📈 Statistics'),
                              reply_markup=create_statistics_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_STATISTICS
    elif action == 'ignore':
        return enums.ADMIN_STATISTICS_GENERAL
    else:
        year, month = user_data['calendar_date']
        subquery = shortcuts.get_order_subquery(action, val, month, year)
        count, price = shortcuts.get_order_count_and_price((Order.delivered == True), (Order.canceled == False), *subquery)
        cancel_count, cancel_price = shortcuts.get_order_count_and_price((Order.canceled == True), *subquery)
        message = _(
            'Total confirmed orders\nCount: {}\nTotal cost: {}₪\n\nTotal canceled orders\nCount: {}\nTotal cost: {}₪'
        ).format(count, price, cancel_count, cancel_price)
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=message,
                              reply_markup=create_statistics_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_STATISTICS


def on_statistics_courier_select(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action, val = query.data.split('|')
    chat_id, message_id = query.message.chat_id, query.message.message_id
    if action == 'back':
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=_('📈 Statistics'),
                              reply_markup=create_statistics_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_STATISTICS
    elif action == 'page':
        current_page = int(val)
        couriers = Courier.select(Courier.username, Courier.id).where(Courier.is_active == True).tuples()
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=_('Select a courier:'),
                              reply_markup=general_select_one_keyboard(_, couriers, current_page),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_STATISTICS_COURIERS
    else:
        user_data['statistics'] = {'courier_id': val}
        state = enums.ADMIN_STATISTICS_COURIERS_DATE
        shortcuts.initialize_calendar(bot, user_data, chat_id, message_id, state, _, query.id)
        return state


def on_statistics_couriers(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action, val = query.data.split('|')
    chat_id, message_id = query.message.chat_id, query.message.message_id
    try:
        courier_id = user_data['statistics']['courier_id']
    except KeyError:
        action = 'back'
    if action == 'back':
        couriers = Courier.select(Courier.username, Courier.id).where(Courier.is_active == True).tuples()
        msg = _('Select a courier:')
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=msg, reply_markup=general_select_one_keyboard(_, couriers),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_STATISTICS_COURIERS
    elif action == 'ignore':
        return enums.ADMIN_STATISTICS_COURIERS_DATE
    else:
        courier = Courier.get(id=courier_id)
        year, month = user_data['calendar_date']
        subquery = shortcuts.get_order_subquery(action, val, month, year)
        count, price = shortcuts.get_order_count_and_price(
            (Order.delivered == True), (Order.canceled == False), (Order.courier == courier), *subquery)
        cancel_count, cancel_price = shortcuts.get_order_count_and_price(
            (Order.canceled == True), (Order.courier == courier) * subquery)
        message = _(
            'Courier @{}\nOrders count: {}\nTotal cost: {}₪\n\nTotal canceled orders\nCount: {}\nTotal cost: {}₪'
        ).format(courier.username, count, price, cancel_count, cancel_price)
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=message,
                              reply_markup=create_statistics_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_STATISTICS


def on_statistics_locations_select(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action, val = query.data.split('|')
    chat_id, message_id = query.message.chat_id, query.message.message_id
    if action == 'back':
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=_('📈 Statistics'),
                              reply_markup=create_statistics_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_STATISTICS
    elif action == 'page':
        current_page = int(val)
        locations = Location.select(Location.title, Location.id).tuples()
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=_('Select location:'),
                              reply_markup=general_select_one_keyboard(_, locations, current_page),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_STATISTICS_LOCATIONS
    else:
        user_data['statistics'] = {'location_id': val}
        state = enums.ADMIN_STATISTICS_LOCATIONS_DATE
        shortcuts.initialize_calendar(bot, user_data, chat_id, message_id, state, _, query.id)
        return state


def on_statistics_locations(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action, val = query.data.split('|')
    chat_id, message_id = query.message.chat_id, query.message.message_id
    try:
        location_id = user_data['statistics']['location_id']
    except KeyError:
        action = 'back'
    if action == 'back':
        locations = Location.select(Location.title, Location.id).tuples()
        msg = _('Select location:')
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=msg, reply_markup=general_select_one_keyboard(_, locations),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_STATISTICS_LOCATIONS
    elif action == 'ignore':
        return enums.ADMIN_STATISTICS_LOCATIONS_DATE
    else:
        location = Location.get(id=location_id)
        year, month = user_data['calendar_date']
        subquery = shortcuts.get_order_subquery(action, val, month, year)
        count, price = shortcuts.get_order_count_and_price((Order.delivered == True),(Order.canceled == False),
                                                           (Order.location == location), *subquery)
        cancel_count, cancel_price = shortcuts.get_order_count_and_price(
            (Order.canceled == True), (Order.location == location) *subquery)
        message = _(
            'Location `{}`\nOrders count: {}\nTotal cost: {}₪\n\nTotal canceled orders\nCount: {}\nTotal cost: {}₪'
        ).format(location.title, count, price, cancel_count, cancel_price)
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=message,
                              reply_markup=create_statistics_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_STATISTICS


def on_statistics_username(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if query and query.data == 'back':
        msg = _('📈 Statistics')
        bot.edit_message_text(msg, query.message.chat_id, query.message.message_id,
                              reply_markup=create_statistics_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_STATISTICS
    username = update.message.text
    users_ids = list(User.select(User.id).where(User.username == username))
    chat_id, message_id = update.message.chat_id, update.message.message_id
    if not users_ids:
        msg = _('User `{}` was not found').format(username)
        bot.send_message(chat_id=chat_id,
                              text=msg, reply_markup=create_statistics_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_STATISTICS
    else:
        user_data['statistics'] = {'users_ids': users_ids}
        state = enums.ADMIN_STATISTICS_USER_DATE
        shortcuts.initialize_calendar(bot, user_data, chat_id, message_id, state, _)
        return state


def on_statistics_user(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action, val = query.data.split('|')
    chat_id, message_id = query.message.chat_id, query.message.message_id
    try:
        user_ids = user_data['statistics']['users_ids']
    except KeyError:
        action = 'back'
    if action == 'back':
        msg = _('Enter username:')
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, reply_markup=create_back_button(_))
        return enums.ADMIN_STATISTICS_USER
    elif action == 'ignore':
        return enums.ADMIN_STATISTICS_USER_DATE
    else:
        users = User.filter(User.id.in_(user_ids))
        text = ''
        year, month = user_data['calendar_date']
        subquery = shortcuts.get_order_subquery(action, val, month, year)
        for user in users:
            count, price = shortcuts.get_order_count_and_price((Order.delivered == True),
                                                               (Order.canceled == False),
                                                               (Order.user == user), *subquery)
            cancel_count, cancel_price = shortcuts.get_order_count_and_price((Order.canceled == True), *subquery)
            message = _(
                'User @{}\n\nOrders count: {}\nTotal cost: {}₪\n\nTotal canceled orders:\n\nCount: {}\nTotal cost: {}₪'
            ).format(user.username, count, price, cancel_count, cancel_price)
            text += message
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text,
                              reply_markup=create_statistics_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_STATISTICS


def on_statistics_menu(bot, update, user_data):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    if data == 'statistics_back':
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=_('⚙️ Settings'),
                              reply_markup=create_admin_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_MENU
    elif data == 'statistics_general':
        state = enums.ADMIN_STATISTICS_GENERAL
        shortcuts.initialize_calendar(bot, user_data, chat_id, message_id, state, _, query.id)
        return state
    elif data == 'statistics_couriers':
        couriers = Courier.select(Courier.username, Courier.id).where(Courier.is_active == True).tuples()
        msg = _('Select a courier:')
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=msg, reply_markup=general_select_one_keyboard(_, couriers),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_STATISTICS_COURIERS
    elif data == 'statistics_locations':
        locations = Location.select().exists()
        if not locations:
            msg = _('You don\'t have locations')
            query.answer(text=msg, show_alert=True)
            return enums.ADMIN_STATISTICS
        else:
            locations = Location.select(Location.title, Location.id).tuples()
            msg = _('Select location:')
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=msg, reply_markup=general_select_one_keyboard(_, locations),
                                  parse_mode=ParseMode.MARKDOWN)
            query.answer()
            return enums.ADMIN_STATISTICS_LOCATIONS
    elif data == 'statistics_user':
        msg = _('Enter username:')
        bot.delete_message(chat_id, message_id)
        bot.send_message(chat_id=chat_id, text=msg, reply_markup=create_back_button(_))
        query.answer()
        return enums.ADMIN_STATISTICS_USER


def on_bot_settings_menu(bot, update):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id, message_id = query.message.chat_id, query.message.message_id
    if data == 'bot_settings_back':
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=_('⚙️ Settings'),
                              reply_markup=create_admin_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_MENU

    elif data == 'bot_settings_couriers':
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=_('🛵 Couriers'),
                              reply_markup=create_bot_couriers_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_COURIERS
    elif data == 'bot_settings_channels':
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=_('✉️ Channels'),
                              reply_markup=create_bot_channels_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_CHANNELS
    elif data == 'bot_settings_order_options':
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=_('💳 Order options'),
                              reply_markup=create_bot_order_options_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_ORDER_OPTIONS
    elif data == 'bot_settings_edit_working_hours':
        msg = _('Now:\n\n`{}`\n\n').format(config.get_working_hours())
        msg += _('Type new working hours')
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=msg,
                              reply_markup=create_back_button(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_EDIT_WORKING_HOURS
    elif data == 'bot_settings_ban_list':
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text='Ban list',
                              reply_markup=create_ban_list_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_BAN_LIST
    elif data == 'bot_settings_edit_contact_info':
        msg = _('Now:\n\n`{}`\n\n').format(config.get_contact_info())
        msg += _('Type new contact info')
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=msg,
                              reply_markup=create_back_button(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_EDIT_CONTACT_INFO
    elif data == 'bot_settings_bot_on_off':
        bot_status = config.get_bot_on_off()
        bot_status = _('BOT ON') if bot_status else _('BOT OFF')
        msg = _('Bot status: {}').format(bot_status)
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=msg,
                              reply_markup=create_on_off_buttons(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_BOT_ON_OFF

    elif data == 'bot_settings_reset_all_data':
        if is_admin(bot, user_id):
            msg = _('You are about to delete your database, session and all messages in channels. Is that correct?')
            bot.edit_message_text(chat_id=chat_id,
                                  message_id=message_id,
                                  text=msg,
                                  reply_markup=create_reset_all_data_keyboard(_),
                                  parse_mode=ParseMode.MARKDOWN)
            query.answer()
            return enums.ADMIN_BOT_RESET_DATA
        else:
            query.answer('This function works only for admin')
            return enums.ADMIN_BOT_SETTINGS

    return ConversationHandler.END


def on_admin_couriers(bot, update):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    if data == 'bot_couriers_back':
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=_('⚙ Bot settings'),
                              reply_markup=create_bot_settings_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_BOT_SETTINGS
    elif data == 'bot_couriers_view':
        couriers = Courier.select(Courier.username, Courier.id).where(Courier.is_active == True).tuples()
        if not couriers:
            query.answer(_('You don\'t have couriers'), show_alert=True)
            return enums.ADMIN_COURIERS
        msg = _('Select a courier:')
        bot.edit_message_text(msg, chat_id, message_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=general_select_one_keyboard(_, couriers))
        query.answer()
        return enums.ADMIN_COURIERS_SHOW
    elif data == 'bot_couriers_add':
        couriers = Courier.select(Courier.username, Courier.id).where(Courier.is_active == False).tuples()
        if not couriers:
            msg = _('There\'s no couriers to add')
            query.answer(msg, show_alert=True)
            return enums.ADMIN_COURIERS
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=_('Select a courier to add'),
                              reply_markup=general_select_one_keyboard(_, couriers),
                              parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_COURIER_ADD
    elif data == 'bot_couriers_delete':
        couriers = Courier.select(Courier.username, Courier.id).where(Courier.is_active == True).tuples()
        if not couriers:
            msg = _('There\'s not couriers to delete')
            query.answer(msg, show_alert=True)
            return enums.ADMIN_COURIERS
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('Select a courier to delete'),
                              parse_mode=ParseMode.MARKDOWN,
                              reply_markup=general_select_one_keyboard(_, couriers)
                              )

        return enums.ADMIN_COURIER_DELETE

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
                              reply_markup=create_bot_settings_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_BOT_SETTINGS
    elif data == 'bot_channels_view':
        msg = _('Reviews channel:\n`{}`\n\n').format(config.get_reviews_channel())
        msg += _('Service channel ID:\n`{}`\n\n').format(config.get_service_channel())
        msg += _('Customer channel:\n`@{}`\n\n').format(config.get_customers_channel())
        msg += _('Vip customer channel ID:\n`{}`\n\n').format(
            config.get_vip_customers_channel())
        msg += _('Courier group ID:\n`{}`\n\n').format(config.get_couriers_channel())

        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_bot_channels_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_CHANNELS
    elif data == 'bot_channels_add':
        types = [_('Reviews Channel'), _('Service Channel'), _('Customer Channel'),
                 _('Vip Customer Channel'), _('Courier Channel')]
        msg = ''
        for i, channel_type in enumerate(types, start=1):
            msg += '\n{} - {}'.format(i, channel_type)
        msg += _('\n\nSelect channel type')
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_back_button(_)
                              )

        return enums.ADMIN_CHANNELS_SELECT_TYPE
    elif data == 'bot_channels_remove':
        types = [_('Reviews Channel'), _('Service Channel'), _('Customer Channel'),
                 _('Vip Customer Channel'), _('Couriers Channel')]
        msg = ''
        for i, channel_type in enumerate(types, start=1):
            msg += '\n{} - {}'.format(i, channel_type)
        msg += _('\n\nSelect channel type')
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_back_button(_)
                              )

        return enums.ADMIN_CHANNELS_REMOVE
    elif data == 'bot_channels_language':
        msg = _('🈚︎ Select language:')
        bot.edit_message_text(msg, query.message.chat_id, query.message.message_id,
                              parse_mode=ParseMode.MARKDOWN, reply_markup=create_bot_language_keyboard(_))
        query.answer()
        return enums.ADMIN_CHANNELS_LANGUAGE
    return ConversationHandler.END


def on_admin_channels_language(bot, update):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if data in ('iw', 'en'):
        config_session = get_config_session()
        config_session['channels_language'] = data
        set_config_session(config_session)
        msg = _('✉️ Channels')
        bot.edit_message_text(msg, query.message.chat_id, query.message.message_id,
                              reply_markup=create_bot_channels_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_CHANNELS


def on_admin_ban_list(bot, update):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if data == 'bot_ban_list_back':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('⚙ Bot settings'),
                              reply_markup=create_bot_settings_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_BOT_SETTINGS
    elif data == 'bot_ban_list_view':
        banned = config.get_banned_users()
        banned = ['@{}'.format(ban) for ban in banned]
        msg = ', '.join(banned)
        msg = 'Banned users: {}'.format(msg)
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_ban_list_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_BAN_LIST
    elif data == 'bot_ban_list_remove':
        msg = 'Type username: @username or username'
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_back_button(_),
                              parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_BAN_LIST_REMOVE
    elif data == 'bot_ban_list_add':
        msg = 'Type username: @username or username'
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_back_button(_),
                              parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_BAN_LIST_ADD

    return ConversationHandler.END


def on_courier_action_to_confirm(bot, update, user_data):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action, order_id = data.split('|')
    callback_mapping = {
        'yes': 'yes|{}'.format(order_id),
        'no': 'no|{}'.format(order_id)
    }
    msg = _('Are you sure?')
    user_data['courier_menu_msg_to_delete'] = query.message.message_id
    bot.send_message(
        chat_id=query.message.chat_id,
        text=msg,
        reply_markup=create_are_you_sure_keyboard(_, callback_mapping)
    )
    query.answer()
    if action == 'confirm_courier_order_delivered':
        return enums.COURIER_STATE_CONFIRM_ORDER
    elif action == 'confirm_courier_report_client':
        return enums.COURIER_STATE_CONFIRM_REPORT


def on_courier_ping_choice(bot, update, user_data):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action, order_id = data.split('|')
    chat_id, msg_id = query.message.chat_id, query.message.message_id
    msg = _('📞 Ping Client')
    user_data['courier_ping_admin'] = action == 'ping_client_admin'
    user_data['courier_ping_order_id'] = order_id
    bot.send_message(chat_id, msg, reply_markup=create_ping_client_keyboard(_))
    query.answer()
    return enums.COURIER_STATE_PING


def on_courier_ping_client(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action = query.data
    chat_id, msg_id = query.message.chat_id, query.message.message_id
    if action == 'back':
        bot.delete_message(chat_id, msg_id)
        query.answer()
        return enums.COURIER_STATE_INIT
    order_id = user_data['courier_ping_order_id']
    order = Order.get(id=order_id)
    if order.client_notified:
        msg = _('Client was notified already')
        query.answer(msg)
        bot.delete_message(chat_id, msg_id)
        return enums.COURIER_STATE_INIT
    if action == 'now':
        user_id = order.user.telegram_id
        _ = get_trans(user_id)
        msg = _('Courier has arrived to deliver your order.')
        bot.send_message(chat_id=user_id,
                         text=msg)
        query.answer()
        order.client_notified = True
        order.save()
        bot.delete_message(chat_id, msg_id)
        del user_data['courier_ping_order_id']
        del user_data['courier_ping_admin']
        return enums.COURIER_STATE_INIT
    elif action == 'soon':
        msg = _('Enter number of minutes left')
        bot.edit_message_text(msg, chat_id, msg_id, reply_markup=create_back_button(_))
        query.answer()
        return enums.COURIER_STATE_PING_SOON


def on_courier_ping_client_soon(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        upd_msg = update.callback_query.message
        msg = _('📞 Ping Client')
        bot.edit_message_text(msg, upd_msg.chat_id, upd_msg.message_id, reply_markup=create_ping_client_keyboard(_))
        update.callback_query.answer()
        return enums.COURIER_STATE_PING
    chat_id = update.message.chat_id
    try:
        time = int(update.message.text)
    except ValueError:
        msg = _('Enter number of minutes left (number is accepted)')
        bot.send_message(chat_id, msg, reply_markup=create_back_button(_))
        return enums.COURIER_STATE_PING_SOON
    else:
        order_id = user_data['courier_ping_order_id']
        order = Order.get(id=order_id)
        courier_msg = _('Client has been notified')
        if user_data['courier_ping_admin']:
            keyboard = create_admin_order_status_keyboard(_, order_id)
        else:
            keyboard = create_courier_order_status_keyboard(_, order_id)
        user_id = order.user.telegram_id
        _ = get_trans(user_id)
        msg = _('Courier will arrive in {} minutes.').format(time)
        bot.send_message(chat_id=user_id,
                         text=msg)
        order.save()
        bot.send_message(chat_id, courier_msg, reply_markup=keyboard)
        del user_data['courier_ping_order_id']
        del user_data['courier_ping_admin']
        return enums.COURIER_STATE_INIT


def on_courier_confirm_order(bot, update, user_data):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    action, order_id = data.split('|')
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    if action == 'yes':
        order = Order.get(id=order_id)
        order.delivered = True
        order.save()
        courier_msg = _('Order №{} is completed!').format(order_id)
        _ = get_channel_trans()
        try:
            courier = Courier.get(telegram_id=user_id)
            msg = _('Order №{} was delivered by courier @{}\n').format(order.id, courier.username)
        except Courier.DoesNotExist:
            user = User.get(telegram_id=user_id)
            msg = _('Order №{} was delivered by admin {}\n').format(order.id, user.username)
        msg += _('Order can be finished now.')
        delete_msg_id = user_data['courier_menu_msg_to_delete']
        bot.delete_message(chat_id, delete_msg_id)
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=courier_msg,
                              parse_mode=ParseMode.MARKDOWN)
        service_channel = config.get_service_channel()
        shortcuts.bot_send_order_msg(bot, service_channel, msg, _, order_id, channel=True)
        return enums.COURIER_STATE_INIT
    elif action == 'no':
        bot.delete_message(chat_id=chat_id,
                           message_id=message_id)
        return enums.COURIER_STATE_INIT


def on_courier_confirm_report(bot, update):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    action, order_id = data.split('|')
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    if action == 'yes':
        msg = _('Please enter report reason')
        bot.delete_message(chat_id=chat_id,
                           message_id=message_id)
        bot.send_message(chat_id =chat_id,
                         text=msg,
                         reply_markup=create_back_button(_)
                         )
        return enums.COURIER_STATE_REPORT_REASON
    elif action == 'no':
        bot.delete_message(chat_id=chat_id,
                           message_id=message_id)
        return enums.COURIER_STATE_INIT


def on_courier_enter_reason(bot, update):
    data = update.message.text
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    order_id = get_user_session(user_id)['courier']['order_id']
    order_data = OrderPhotos.get(order_id=order_id)
    chat_id = update.message.chat_id
    courier_msg = _('User was reported!')
    bot.send_message(chat_id, text=courier_msg)
    bot.send_message(chat_id=chat_id,
                     text=order_data.order_text,
                     reply_markup=create_courier_order_status_keyboard(_, order_id),
                     parse_mode=ParseMode.MARKDOWN)
    reported_username = Order.get(id=order_id).user.username
    courier_username = Courier.get(telegram_id=user_id).username
    _ = get_channel_trans()
    report_msg = _('Order №{}:\n'
                               'Courier {} has reported {}\n'
                               'Reason: {}').format(order_id, courier_username, reported_username, data)
    service_channel = config.get_service_channel()
    shortcuts.bot_send_order_msg(bot, service_channel, report_msg, _, order_id, channel=True)
    return enums.COURIER_STATE_INIT


def on_courier_cancel_reason(bot, update):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
    return enums.COURIER_STATE_INIT


def on_admin_drop_order(bot, update):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action, order_id = query.data.split('|')
    order = Order.get(id=order_id)
    shortcuts.change_order_products_credits(order, True)
    order.courier = None
    order.save()
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    bot.delete_message(chat_id, message_id)
    msg = _('Order №{} was dropped!').format(order.id)
    bot.send_message(chat_id, msg)


def on_product_categories(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    user_data = get_user_session(user_id)
    _ = get_trans(user_id)
    chat_id, message_id = query.message.chat_id, query.message.message_id
    try:
        action, val = query.data.split('|')
    except ValueError:
        action = query.data
    if action == 'page':
        categories = ProductCategory.select(ProductCategory.title, ProductCategory.id).tuples()
        keyboard = general_select_one_keyboard(_, categories, int(val))
        bot.edit_message_text(_('Please select a category'), chat_id, message_id,
                              reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.PRODUCT_CATEGORIES
    user = User.get(telegram_id=user_id)
    total = cart.get_cart_total(get_user_session(user_id))
    if action == 'select':
        cat = ProductCategory.get(id=val)
        msg = _('Category `{}` products:').format(cat.title)
        bot.edit_message_text(msg, chat_id, message_id, parse_mode=ParseMode.MARKDOWN)
        # send_products to current chat
        for product in Product.filter(category=cat, is_active=True):
            product_count = cart.get_product_count(
                user_data, product.id)
            subtotal = cart.get_product_subtotal(
                user_data, product.id)
            product_title, prices = cart.product_full_info(
                user_data, product.id)
            shortcuts.send_product_media(bot, product, chat_id)
            bot.send_message(chat_id,
                             text=create_product_description(
                                 user_id,
                                 product_title, prices,
                                 product_count, subtotal),
                             reply_markup=create_product_keyboard(_,
                                                                  product.id, user_data, cart),
                             parse_mode=ParseMode.MARKDOWN,
                             timeout=20, )
        user = User.get(telegram_id=user_id)
        total = cart.get_cart_total(get_user_session(user_id))
        user_data = get_user_session(user_id)
        products_info = cart.get_products_info(user_data)
        if products_info:
            msg = create_cart_details_msg(user_id, products_info)
        else:
            msg = config.get_order_text()
        main_msg = bot.send_message(chat_id,
                         text=msg,
                         reply_markup=create_main_keyboard(_,
                                                           config.get_reviews_channel(),
                                                           user,
                                                           is_admin(bot, user_id), total),
                         parse_mode=ParseMode.MARKDOWN)
        user_data['menu_id'] = main_msg['message_id']
        session_client.json_set(user_id, user_data)
    elif action == 'back':
        user_data = get_user_session(user_id)
        products_info = cart.get_products_info(user_data)
        if products_info:
            msg = create_cart_details_msg(user_id, products_info)
        else:
            msg = config.get_order_text()
        bot.edit_message_text(msg, chat_id, message_id,
                              reply_markup=create_main_keyboard(_,
                                                                config.get_reviews_channel(),
                                                                user,
                                                                is_admin(bot, user_id), total),
                              parse_mode=ParseMode.MARKDOWN
                              )
    query.answer()
    return enums.BOT_STATE_INIT


def on_calendar_change(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    try:
        saved_date = user_data['calendar_date']
        calendar_state = user_data['calendar_state']
    except KeyError:
        msg = _('Failed to get calendar date, please initialize calendar again.')
        bot.send_message(msg, chat_id)
    else:
        data = query.data
        year, month = saved_date
        msg = _('Pick year, month or day')
        if data == 'calendar_next_year':
            year += 1
        elif data == 'calendar_previous_year':
            year -= 1
        elif data == 'calendar_next_month':
            month += 1
            if month > 12:
                month = 1
                year += 1
        elif data == 'calendar_previous_month':
            month -= 1
            if month < 1:
                month = 12
                year -= 1
        if year < 1:
            year = 1
        user_data['calendar_date'] = year, month
        bot.edit_message_text(chat_id=chat_id, message_id=query.message.message_id,
                              text=msg, reply_markup=create_calendar_keyboard(year, month, _))
        query.answer()
        return calendar_state

