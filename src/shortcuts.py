import datetime
import operator

from telegram import ParseMode, TelegramError, InputMediaPhoto, InputMediaVideo

from .models import Order, OrderPhotos, OrderItem, ProductWarehouse, ChannelMessageData, ProductCount

from .helpers import config, get_trans, logger, get_user_id, get_channel_trans, get_user_session, session_client
from . import keyboards
from . import messages


def make_confirm(bot, update, user_data):
    query = update.callback_query
    data = query.data
    label, order_id, courier_name = data.split('|')
    delete_channel_msg(bot, config.get_service_channel(), query.message.message_id)
    try:
        order = Order.get(id=order_id)
    except Order.DoesNotExist:
        logger.info('Order № {} not found!'.format(order_id))
    else:
        order.confirmed = True
        order.save()

        user_id = order.user.telegram_id
        _ = get_trans(user_id)
        bot.send_message(
            user_id,
            text=_('Courier @{} assigned to your order').format(courier_name),
            parse_mode=ParseMode.MARKDOWN,
        )
        courier_id = order.courier.telegram_id
        user_data = get_user_session(courier_id)
        user_data['courier']['order_id'] = order_id
        session_client.json_set(courier_id, user_data)
        order_data = OrderPhotos.get(order_id=order_id)
        _ = get_trans(courier_id)
        bot.send_message(courier_id,
                         text=order_data.order_text,
                         reply_markup=keyboards.create_courier_order_status_keyboard(_, order_id),
                         parse_mode=ParseMode.MARKDOWN)


def make_unconfirm(bot, update, user_data):
    query = update.callback_query
    data = query.data
    label, order_id, courier_name, answers_ids, assigned_msg_id = data.split('|')
    delete_channel_msg(bot, config.get_service_channel(), query.message.message_id)
    couriers_channel = config.get_couriers_channel()
    for answer_id in answers_ids.split(','):
        delete_channel_msg(bot, couriers_channel, answer_id)
    delete_channel_msg(bot, couriers_channel, assigned_msg_id)
    try:
        order = Order.get(id=order_id)
    except Order.DoesNotExist:
        logger.info('Order № {} not found!'.format(order_id))
    else:
        change_order_products_credits(order, True, order.courier)
        order.courier = None
        order.save()
        _ = get_channel_trans()
        order_data = OrderPhotos.get(order=order)
        msg = _('The admin did not confirm. Please retake '
                'responsibility for order №{}').format(order_id)
        send_channel_msg(bot, msg, couriers_channel, order=order)
        answers_ids = send_order_identification_answers(bot, couriers_channel, order, send_one=True, channel=True)
        answers_ids = ','.join(answers_ids)
        order_info = Order.get(id=order_id)
        order_pickup_state = order_info.shipping_method
        order_location = order_info.location
        if order_location:
            order_location = order_location.title
        keyboard = keyboards.create_service_notice_keyboard(order_id, _, answers_ids, order_location, order_pickup_state)
        send_channel_msg(bot, order_data.order_text, couriers_channel, keyboard, order)


def resend_responsibility_keyboard(bot, update):
    query = update.callback_query
    data = query.data
    order_id = data.split('|')[1]
    try:
        order = Order.get(id=order_id)
    except Order.DoesNotExist:
        logger.info('Order № {} not found!'.format(order_id))
        return
    else:
        change_order_products_credits(order, True, order.courier)
        order.confirmed = False
        order.courier = None
        order.save()
    couriers_channel = config.get_couriers_channel()
    _ = get_channel_trans()
    bot.delete_message(query.message.chat_id,
                       message_id=query.message.message_id)
    order_data = OrderPhotos.get(order_id=order_id)
    msg = _('Order №{} was dropped by courier').format(order_id)
    send_channel_msg(bot, msg, couriers_channel, order=order)
    answers_ids = send_order_identification_answers(bot, couriers_channel, order, send_one=True, channel=True)
    answers_ids = ','.join(answers_ids)

    order_info = Order.get(id=order_id)
    order_pickup_state = order_info.shipping_method
    order_location = order_info.location
    if order_location:
        order_location = order_location.title
    keyboard = keyboards.create_service_notice_keyboard(order_id, _, answers_ids, order_location, order_pickup_state)
    send_channel_msg(bot, order_data.order_text, couriers_channel, keyboard, order)
    query.answer(text=_('Order sent to couriers channel'), show_alert=True)


def bot_send_order_msg(bot, chat_id, message, trans_func, order_id, order_data=None, channel=False):
    order = Order.get(id=order_id)
    if not order_data:
        order_data = OrderPhotos.get(order=order)
    _ = trans_func
    keyboard = keyboards.create_show_order_keyboard(_, order_id)
    if channel:
        msg_id = send_channel_msg(bot, message, chat_id, keyboard, order)
    else:
        order_msg = bot.send_message(chat_id, message, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        msg_id = order_msg['message_id']
    order_data.order_hidden_text = message
    order_data.order_text_msg_id = str(msg_id)
    order_data.save()


def send_order_identification_answers(bot, chat_id, order, send_one=False, channel=False):
    answers = []
    photos_answers = []
    photos = []
    class_map = {'photo': InputMediaPhoto, 'video': InputMediaVideo}
    for answer in order.identification_answers:
        type = answer.stage.type
        content = answer.content
        question = answer.question.content
        if type in ('photo', 'video'):
            media_class = class_map[type]
            content = media_class(content, question)
            photos.append(content)
            photos_answers.append(answer)
        else:
            content = '_{}:_\n' \
                      '{}'.format(question, content)
            answers.append((content, answer))
        if send_one:
            break
    if photos:
        if channel:
            msgs_ids = send_channel_media_group(bot, chat_id, photos, order=order)
        else:
            photo_msgs = bot.send_media_group(chat_id, photos)
            msgs_ids = [msg['message_id'] for msg in photo_msgs]
    else:
        msgs_ids = []
    for ph_id, answer in zip(msgs_ids, photos_answers):
        answer.msg_id = ph_id
        answer.save()
    for content, answer in answers:
        if channel:
            sent_msg_id = send_channel_msg(bot, content, chat_id, order=order)
            answer.msg_id = sent_msg_id
        else:
            msg = bot.send_message(chat_id, content, parse_mode=ParseMode.MARKDOWN)
            sent_msg_id = msg['message_id']
        answer.save()
        msgs_ids.append(str(sent_msg_id))
    return msgs_ids


def send_product_info(bot, product, chat_id, trans):
    if product.group_price:
        product_prices = product.group_price.product_counts
    else:
        product_prices = product.product_counts
    product_prices = ((obj.count, obj.price) for obj in product_prices)
    send_product_media(bot, product, chat_id)
    msg = messages.create_admin_product_description(trans, product.title, product_prices)
    bot.send_message(chat_id,
                     text=msg)


def initialize_calendar(bot, user_data, chat_id, message_id, state, trans, query_id=None):
    _ = trans
    current_date = datetime.date.today()
    year, month = current_date.year, current_date.month
    # if not 'calendar_date' in user_data:
    user_data['calendar_date'] = year, month
    user_data['calendar_state'] = state
    msg = _('Pick year, month or day')
    if query_id:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg,
                              reply_markup=keyboards.create_calendar_keyboard(year, month, _),
                              parse_mode=ParseMode.MARKDOWN)
        bot.answer_callback_query(chat_id=chat_id, callback_query_id=query_id)
    else:
        bot.send_message(text=msg, chat_id=chat_id, reply_markup=keyboards.create_calendar_keyboard(year, month, _),
                         parse_mode=ParseMode.MARKDOWN)


def get_order_subquery(action, val, month, year):
    val = int(val)
    query = []
    subquery = Order.date_created.year == year
    query.append(subquery)
    if action == 'year':
        return query
    query.append(Order.date_created.month == month)
    if action == 'day':
        query.append(Order.date_created.day == val)
    return query


def get_order_count_and_price(*subqueries):
    _ = get_channel_trans()
    orders_count = Order.select().where(*subqueries).count()
    total_price = 0
    delivery_fee = 0
    products_count = {}
    product_text = ''
    count_text = _('count')
    price_text = _('price')
    orders_items = OrderItem.select().join(Order).where(*subqueries)
    for order_item in orders_items:
        total_price += order_item.total_price
        try:
            delivery_fee += order_item.order.location.delivery_fee
        except:
            continue
        title, count, price = order_item.product.title, order_item.count, order_item.total_price
        try:
            if products_count[title]:
                products_count[title][count_text] += count
                products_count[title][price_text] += price
        except KeyError:
            products_count[title] = {count_text: count, price_text: price}
    for x in products_count:
        product_text += _('\n Product: *')
        product_text += x
        product_text += '*\n'
        for y in products_count[x]:
            product_text += y
            product_text += ' = '
            product_text += str(products_count[x][y])
            product_text += '\n'
    return orders_count, total_price, product_text, delivery_fee


def check_order_products_credits(order, trans, courier=None):
    msg = ''
    first_msg = True
    not_defined = False
    for order_item in order.order_items:
        product = order_item.product
        if courier:
            try:
                warehouse = ProductWarehouse.get(product=product, courier=courier)
                warehouse_count = warehouse.count
            except ProductWarehouse.DoesNotExist:
                warehouse = ProductWarehouse(product=product, courier=courier)
                warehouse.save()
        else:
            warehouse_count = product.credits
        product_warehouse = ProductWarehouse.get(product=product)
        product_warehouse_count = product_warehouse.count
        if product_warehouse_count <= 0:
            not_defined = True
            return not_defined
        if order_item.count > warehouse_count:
            _ = trans
            if courier:
                if first_msg:
                    msg += _('You don\'t have enough credits to deliver products:\n')
                    first_msg = False
                msg += _('Product: `{}`\nCount: {}\nCourier credits: {}\n').format(product.title,
                                                                                   order_item.count,
                                                                                   warehouse_count)
            else:
                if first_msg:
                    msg += _('There are not enough credits in warehouse to deliver products:\n')
                    first_msg = False
                msg += _('Product: `{}`\nCount: {}\nWarehouse credits: {}\n').format(product.title,
                                                                                     order_item.count,
                                                                                     warehouse_count)
    return msg


def change_order_products_credits(order, add=False, courier=None):
    if add:
        op = operator.add
    else:
        op = operator.sub
    for order_item in order.order_items:
        product = order_item.product
        if courier:
            warehouse = ProductWarehouse.get(product=product, courier=courier)
            warehouse.count = op(warehouse.count, order_item.count)
            warehouse.save()
        else:
            product.credits = op(product.credits, order_item.count)
            product.save()


def send_product_media(bot, product, chat_id):
    class_map = {'photo': InputMediaPhoto, 'video': InputMediaVideo}
    media_list = []
    for media in product.product_media:
        media_class = class_map[media.file_type]
        file = media_class(media=media.file_id)
        media_list.append(file)
    bot.send_media_group(chat_id, media_list)


def send_channel_msg(bot, msg, chat_id, keyboard=None, order=None):
    params = {
        'chat_id': chat_id, 'text': msg, 'parse_mode': ParseMode.MARKDOWN
    }
    if keyboard:
        params['reply_markup'] = keyboard
    sent_msg = bot.send_message(**params)
    sent_msg_id = str(sent_msg['message_id'])
    ChannelMessageData.create(channel=str(chat_id), msg_id=sent_msg_id, order=order)
    return sent_msg_id


def send_channel_location(bot, chat_id, lat, lng, order=None):
    sent_msg = bot.send_location(chat_id, lat, lng)
    sent_msg_id = str(sent_msg['message_id'])
    ChannelMessageData.create(channel=str(chat_id), msg_id=sent_msg_id, order=order)
    return sent_msg_id


def edit_channel_msg(bot, msg, chat_id, msg_id, keyboard=None, order=None):
    params = {
        'chat_id': chat_id, 'message_id': msg_id, 'text': msg, 'parse_mode': ParseMode.MARKDOWN
    }
    if keyboard:
        params['reply_markup'] = keyboard
    edited_msg = bot.edit_message_text(**params)
    edited_msg_id = str(edited_msg['message_id'])
    chat_id = str(chat_id)
    try:
        msg_data = ChannelMessageData.get(channel=chat_id, msg_id=msg_id)
    except ChannelMessageData.DoesNotExist:
        ChannelMessageData.create(channel=chat_id, msg_id=edited_msg_id, order=order)
    else:
        msg_data.channel = chat_id
        msg_data.msg_id = edited_msg_id
        msg_data.order = order
        msg_data.save()
    return edited_msg_id


def delete_channel_msg(bot, chat_id, msg_id):
    try:
        bot.delete_message(chat_id, msg_id)
    except TelegramError:
        pass
    try:
        msg_row = ChannelMessageData.get(channel=str(chat_id), msg_id=str(msg_id))
    except ChannelMessageData.DoesNotExist:
        pass
    else:
        msg_row.delete_instance()


def send_channel_media_group(bot, chat_id, media, order=None):
    msgs = bot.send_media_group(chat_id, media)
    msgs_ids = [str(msg['message_id']) for msg in msgs]
    chat_id = str(chat_id)
    for msg_id in msgs_ids:
        ChannelMessageData.create(channel=chat_id, msg_id=msg_id, order=order)
    return msgs_ids


def delete_order_channels_msgs(bot, order):
    msgs = ChannelMessageData.select().where(ChannelMessageData.order == order)
    for msg in msgs:
        try:
            bot.delete_message(msg.channel, msg.msg_id)
        except TelegramError:
            pass
        msg.delete_instance()


def get_product_prices_str(trans, product):
    _ = trans
    group_price = product.group_price
    prices_str = _('Current prices:\n')
    if group_price:
        prices_str += _('Product price group:\n_{}_').format(group_price.name)
        prices_str += '\n\n'
        product_counts = ProductCount.select().where(ProductCount.product_group == group_price)
    else:
        product_counts = product.product_counts
    for price in product_counts:
        prices_str += _('x {} = ${}\n').format(price.count, price.price)
    return prices_str
