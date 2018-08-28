from telegram import ParseMode

from .models import Order, OrderPhotos

from .helpers import config, get_trans, logger, get_user_id, get_channel_trans, get_user_session, session_client
from .keyboards import create_service_notice_keyboard, create_courier_order_status_keyboard

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
                         reply_markup=create_courier_order_status_keyboard(_, order_id),
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
                         reply_markup=create_service_notice_keyboard(order_id, _, photo_msg_id),
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
                     reply_markup=create_service_notice_keyboard(order_id, _, photo_msg_id),
                     parse_mode=ParseMode.HTML,
                     )

    query.answer(text='Order sent to couriers channel', show_alert=True)