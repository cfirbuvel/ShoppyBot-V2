import io

from telegram import ParseMode
from telegram.ext import ConversationHandler

from .helpers import cart, config, session_client, get_user_session, get_user_id, get_username, is_customer, \
    is_vip_customer, get_locale, get_trans
from .keyboards import create_main_keyboard, create_admin_keyboard, create_product_keyboard, create_shipping_keyboard, \
    create_bot_language_keyboard, create_my_orders_keyboard, general_select_one_keyboard
from .messages import create_product_description, create_cart_details_msg
from .models import User, Product, ProductCategory, Order
from . import enums
from .states import is_admin
from . import shortcuts

def on_start(bot, update, user_data):
    user_id = get_user_id(update)
    username = get_username(update)
    locale = get_locale(update)
    try:
        user = User.get(telegram_id=user_id)
    except User.DoesNotExist:
        user = User(telegram_id=user_id, username=username, locale=locale)
        user.save()
    _ = get_trans(user_id)
    BOT_ON = config.get_bot_on_off() and username not in config.get_banned_users()
    if BOT_ON or is_admin(bot, user_id):
        if is_customer(bot, user_id) or is_vip_customer(bot, user_id):
            user_data = get_user_session(user_id)
            products_info = cart.get_products_info(user_data)
            if products_info:
                msg = create_cart_details_msg(user_id, products_info)
            else:
                msg = config.get_welcome_text().format(update.effective_user.first_name)
            total = cart.get_cart_total(user_data)
            enums.logger.info('Starting session for user %s, language: %s',
                        update.message.from_user.id,
                        update.message.from_user.language_code)
            update.message.reply_text(
                text=msg,
                reply_markup=create_main_keyboard(_, config.get_reviews_channel(), user,
                                                  is_admin(bot, user_id), total),
            )
            return enums.BOT_STATE_INIT
        else:
            enums.logger.info('User %s rejected (not a customer)',
                        update.message.from_user.id)
            update.message.reply_text(
                text=_('Sorry {}\nYou are not authorized to use '
                       'this bot').format(update.message.from_user.first_name),
                reply_markup=None,
                parse_mode=ParseMode.MARKDOWN,
            )
            return ConversationHandler.END
    else:
        update.message.reply_text(
            text=_('Sorry {}, the bot is currently switched off').format(
                update.message.from_user.first_name),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END


def on_menu(bot, update, user_data=None):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    user_data = get_user_session(user_id)
    _ = get_trans(user_id)
    BOT_ON = config.get_bot_on_off()
    total = cart.get_cart_total(get_user_session(user_id))
    user = User.get(telegram_id=user_id)
    chat_id = query.message.chat_id
    if BOT_ON or is_admin(bot, user_id):
        if is_customer(bot, user_id) or is_vip_customer(bot, user_id):
            if data == 'menu_products':
                # the menu disappears
                categories = ProductCategory.select(ProductCategory.title, ProductCategory.id).tuples()
                if categories:
                    keyboard = general_select_one_keyboard(_, categories)
                    msg = _('Please select a category:')
                    bot.edit_message_text(msg, query.message.chat_id, query.message.message_id,
                                          parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
                    query.answer()
                    return enums.PRODUCT_CATEGORIES
                else:
                    for product in Product.filter(is_active=True):
                        product_count = cart.get_product_count(
                            user_data, product.id)
                        subtotal = cart.get_product_subtotal(
                            user_data, product.id)
                        delivery_fee = config.get_delivery_fee()
                        delivery_min = config.get_delivery_min()
                        product_title, prices = cart.product_full_info(
                            user_data, product.id)
                        shortcuts.send_product_media(bot, product, chat_id)
                        bot.send_message(chat_id,
                                         text=create_product_description(
                                             user_id,
                                             product_title, prices,
                                             product_count, subtotal,
                                             delivery_min, delivery_fee),
                                         reply_markup=create_product_keyboard(_,
                                                                              product.id, user_data, cart),
                                         parse_mode=ParseMode.MARKDOWN,
                                         timeout=20, )
                    user = User.get(telegram_id=user_id)
                    total = cart.get_cart_total(user_data)
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
                    return enums.BOT_STATE_INIT
            elif data == 'menu_order':
                if cart.is_full(user_data):
                    unfinished_orders = Order.select().where(Order.user == user, Order.delivered == False)
                    if len(unfinished_orders):
                        msg = _('You cannot make new order if previous order is not finished')
                        query.answer(msg)
                        return enums.BOT_STATE_INIT
                    bot.send_message(query.message.chat_id,
                                     text=_('Please choose pickup or delivery'),
                                     reply_markup=create_shipping_keyboard(_),
                                     parse_mode=ParseMode.MARKDOWN, )
                    query.answer()
                    return enums.BOT_STATE_CHECKOUT_SHIPPING
                else:
                    bot.answer_callback_query(
                        query.id,
                        text=_('Your cart is empty. '
                               'Please add something to the cart.'),
                        parse_mode=ParseMode.MARKDOWN, )
                    return enums.BOT_STATE_INIT

            elif data == 'menu_language':
                bot.edit_message_text(chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      text=_('🈚︎  Languages'),
                                      reply_markup=create_bot_language_keyboard(_),
                                      parse_mode=ParseMode.MARKDOWN)

                query.answer()
                return enums.BOT_LANGUAGE_CHANGE

            elif data == 'menu_hours':
                bot.edit_message_text(chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      text=config.get_working_hours(),
                                      reply_markup=create_main_keyboard(_,
                                                                        config.get_reviews_channel(),
                                                                        user,
                                                                        is_admin(bot, user_id), total),
                                      parse_mode=ParseMode.MARKDOWN, )
            elif data == 'menu_contact':
                bot.edit_message_text(chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      text=config.get_contact_info(),
                                      reply_markup=create_main_keyboard(_,
                                                                        config.get_reviews_channel(),
                                                                        user,
                                                                        is_admin(bot, user_id), total),
                                      parse_mode=ParseMode.MARKDOWN, )
            elif data.startswith('product_add'):
                product_id = int(data.split('|')[1])
                user_data = cart.add(user_data, product_id)
                session_client.json_set(user_id, user_data)

                subtotal = cart.get_product_subtotal(user_data, product_id)
                delivery_fee = config.get_delivery_fee()
                delivery_min = config.get_delivery_min()
                product_title, prices = cart.product_full_info(
                    user_data, product_id)
                product_count = cart.get_product_count(user_data, product_id)
                products_info = cart.get_products_info(user_data)
                msg = create_cart_details_msg(user_id, products_info)
                bot.edit_message_text(chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      text=create_product_description(
                                          user_id,
                                          product_title, prices,
                                          product_count, subtotal,
                                          delivery_min, delivery_fee),
                                      reply_markup=create_product_keyboard(_,
                                                                           product_id, user_data, cart),
                                      parse_mode=ParseMode.MARKDOWN, )
                bot.edit_message_text(chat_id=query.message.chat_id,
                                      message_id=user_data['menu_id'],
                                      text=msg,
                                      reply_markup=create_main_keyboard(_,
                                                                       config.get_reviews_channel(),
                                                                       user,
                                                                       is_admin(bot, user_id), total))
            elif data.startswith('product_remove'):
                product_id = int(data.split('|')[1])
                user_data = cart.remove(user_data, product_id)
                session_client.json_set(user_id, user_data)

                subtotal = cart.get_product_subtotal(user_data, product_id)
                delivery_fee = config.get_delivery_fee()
                delivery_min = config.get_delivery_min()
                product_title, prices = cart.product_full_info(
                    user_data, product_id)
                product_count = cart.get_product_count(user_data, product_id)
                products_info = cart.get_products_info(user_data)
                if products_info:
                    msg = create_cart_details_msg(user_id, products_info)
                else:
                    msg = config.get_order_text()
                bot.edit_message_text(chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      text=create_product_description(
                                          user_id,
                                          product_title, prices,
                                          product_count, subtotal,
                                          delivery_min, delivery_fee),
                                      reply_markup=create_product_keyboard(_,
                                                                           product_id, user_data, cart),
                                      parse_mode=ParseMode.MARKDOWN, )
                bot.edit_message_text(chat_id=query.message.chat_id,
                                      message_id=user_data['menu_id'],
                                      text=msg,
                                      reply_markup=create_main_keyboard(_,
                                                                        config.get_reviews_channel(),
                                                                        user,
                                                                        is_admin(bot, user_id), total))
            elif data == 'menu_settings':
                bot.edit_message_text(chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      text=_('⚙️ Settings'),
                                      reply_markup=create_admin_keyboard(_),
                                      parse_mode=ParseMode.MARKDOWN, )
                query.answer()
                return enums.ADMIN_MENU
            elif data == 'menu_myorders':
                bot.edit_message_text(chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      text=_('📖 My Orders'),
                                      reply_markup=create_my_orders_keyboard(_),
                                      parse_mode=ParseMode.MARKDOWN)
                query.answer()
                return enums.BOT_STATE_MY_ORDERS
            else:
                enums.logger.warn('Unknown query: %s', query.data)
        else:
            enums.logger.info('User %s rejected (not a customer)', user_id)
            bot.send_message(
                query.message.chat_id,
                text=_('Sorry {}\nYou are not authorized '
                       'to use this bot').format(query.from_user.first_name),
                reply_markup=None,
                parse_mode=ParseMode.MARKDOWN,
            )
            return ConversationHandler.END
    else:
        bot.send_message(
            query.message.chat_id,
            text=_('Sorry, the bot is currently switched off').format(
                query.from_user.first_name),
            reply_markup=None,
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END
    query.answer()
    # we want to remain in init state here
    return enums.BOT_STATE_INIT


def on_error(bot, update, error):
    enums.logger.error('Error: %s', error)


def on_chat_update_handler(bot, update):
    for val in dir(update):
        if not val.startswith('_'):
            print('{}: {}'.format(val, getattr(update, val)))

