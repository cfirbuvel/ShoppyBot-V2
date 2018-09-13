from telegram import ParseMode, TelegramError
import io
import datetime
import operator

from .models import Order, OrderPhotos, OrderItem, ProductWarehouse

from .helpers import config, get_trans, logger, get_user_id, get_channel_trans, get_user_session, session_client
# from .keyboards import create_service_notice_keyboard, create_courier_order_status_keyboard
from . import keyboards
from . import messages


def make_confirm(bot, update, user_data):
    query = update.callback_query
    data = query.data
    label, order_id, courier_name = data.split('|')
    bot.delete_message(config.get_service_channel(),
                       message_id=query.message.message_id)
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
            parse_mode=ParseMode.HTML,
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
                         parse_mode=ParseMode.HTML)



def make_unconfirm(bot, update, user_data):
    query = update.callback_query
    data = query.data
    label, order_id, courier_name, photo_msg_id, assigned_msg_id = data.split('|')
    bot.delete_message(config.get_service_channel(),
                       message_id=query.message.message_id)
    couriers_channel = config.get_couriers_channel()
    bot.delete_message(couriers_channel,
                       message_id=photo_msg_id)
    bot.delete_message(couriers_channel,
                       message_id=assigned_msg_id)
    try:
        order = Order.get(id=order_id)
    except Order.DoesNotExist:
        logger.info('Order № {} not found!'.format(order_id))
    else:
        # user_id = order.user.telegram_id
        change_order_products_credits(order, True, order.courier)
        order.courier = None
        order.save()
        _ = get_channel_trans()
        order_data = OrderPhotos.get(order=order)
        bot.send_message(couriers_channel,
                         text='The admin did not confirm. Please retake '
                              'responsibility for order №{}'.format(order_id),
                         )
        photo_msg_id = ''
        if order_data.photo_id:
            photo_id, msg_id = order_data.photo_id.split('|')
            photo_msg = bot.send_photo(couriers_channel,
                                       photo=photo_id,
                                       caption=_('Stage 1 Identification - Selfie'),
                                       parse_mode=ParseMode.MARKDOWN, )
            photo_msg_id = photo_msg['message_id']

        bot.send_message(chat_id=couriers_channel,
                         text=order_data.order_text,
                         reply_markup=keyboards.create_service_notice_keyboard(order_id, _, photo_msg_id),
                         parse_mode=ParseMode.HTML,
                         )


def resend_responsibility_keyboard(bot, update):
    query = update.callback_query
    data = query.data
    order_id = data.split('|')[1]
    # user_id = get_user_id(update)
    try:
        order = Order.get(id=order_id)
    except Order.DoesNotExist:
        logger.info('Order № {} not found!'.format(order_id))
    else:
        change_order_products_credits(order, True, order.courier)
        order.confirmed = False
        order.courier = None
        order.save()
    couriers_channel = config.get_couriers_channel()
    _ = get_channel_trans()
    bot.delete_message(query.message.chat_id,
                       message_id=query.message.message_id)
    order = OrderPhotos.get(order_id=order_id)
    bot.send_message(chat_id=couriers_channel,
                     text='Order №{} was dropped by courier'.format(order_id))
    photo_msg_id = ''
    if order.photo_id:
        photo_id, msg_id = order.photo_id.split('|')
        photo_msg = bot.send_photo(couriers_channel,
                       photo=photo_id,
                       caption=_('Stage 1 Identification - Selfie'),
                       parse_mode=ParseMode.MARKDOWN, )
        photo_msg_id = photo_msg['message_id']
    bot.send_message(chat_id=couriers_channel,
                     text=order.order_text,
                     reply_markup=keyboards.create_service_notice_keyboard(order_id, _, photo_msg_id),
                     parse_mode=ParseMode.HTML,
                     )

    query.answer(text='Order sent to couriers channel', show_alert=True)

def bot_send_order_msg(bot, chat_id, message, trans_func, order_id, order_data=None):
    if not order_data:
        order_data = OrderPhotos.get(order_id=order_id)
    _ = trans_func
    order_msg = bot.send_message(chat_id,
                         text=message,
                         reply_markup=keyboards.create_show_order_keyboard(_, order_id))
    order_data.order_hidden_text = message
    order_data.order_text_msg_id = str(order_msg['message_id'])
    order_data.save()


def send_product_info(bot, product, chat_id, trans):
    product_prices = ((obj.count, obj.price) for obj in product.product_counts)
    image_data = product.image
    image_stream = io.BytesIO(image_data)
    bot.send_photo(chat_id,
                   photo=image_stream)
    msg = messages.create_admin_product_description(trans, product.title, product_prices)
    bot.send_message(chat_id,
                     text=msg)

def initialize_calendar(bot, user_data, chat_id, message_id, state, trans, query_id=None):
    _ = trans
    current_date = datetime.date.today()
    year, month = current_date.year, current_date.month
    if not 'calendar_date' in user_data:
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
    # if action == 'year':
    query = []
    subquery = Order.date_created.year == year
    query.append(subquery)
    if action == 'year':
        return query
    #if action == 'month':
    query.append(Order.date_created.month == month)
    if action == 'day':
        query.append(Order.date_created.day == val)
    return query

def get_order_count_and_price(*subqueries):
    orders_count = Order.select().where(*subqueries).count()
    total_price = 0
    orders_items = OrderItem.select().join(Order).where(*subqueries)
    for order_item in orders_items:
        total_price += order_item.count * order_item.total_price
    return orders_count, total_price

def check_order_products_credits(order, trans, courier=None):
    msg = ''
    first_msg = True
    for order_item in order.order_items:
        product = order_item.product
        if courier:
            warehouse = ProductWarehouse.get(product=product, courier=courier)
            warehouse_count = warehouse.count
        else:
            warehouse_count = product.credits
        if order_item.count > warehouse_count:
            _ = trans
            if courier:
                if first_msg:
                    msg += _('You don\'t have enough credits to deliver products:\n')
                    first_msg = False
                msg += _('Product: `{}`, Count: {}, Courier credits: {}\n').format(product.title, order_item.count, warehouse_count)
            else:
                if first_msg:
                    msg += 'There are not enough credits in warehouse to deliver products:\n'
                    first_msg = False
                msg += _('Product: `{}`, Count: {}, Warehouse credits: {}\n').format(product.title, order_item.count, warehouse_count)
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

# def send_chunks(bot, obj_list, chat_id, selected_command, back_command, first_message, trans, chunk_size=50):
#     _ = trans
#     # first_iter = True
#     while True:
#         chunk = obj_list[:chunk_size]
#         obj_list = obj_list[chunk_size:]
#         # if first_iter:
#         #     msg = _(first_message)
#         #     first_iter = False
#         # else:
#         #     msg = '~' * len(first_message)
#         msg = _(first_message)
#         if obj_list:
#             markup = keyboards.create_select_products_chunk_keyboard(_, chunk, selected_command)
#         else:
#             markup = keyboards.create_select_products_chunk_keyboard(_, chunk, selected_command, back_command)
#         bot.send_message(chat_id, msg, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
#         if not obj_list:
#             break