import io

from telegram import ParseMode
from telegram.ext import ConversationHandler

from .helpers import cart, config, session_client, get_user_session, get_user_id, get_username, is_customer, \
    is_vip_customer, get_locale, get_trans
from .keyboards import create_main_keyboard, create_admin_keyboard, create_product_keyboard, create_shipping_keyboard, \
    create_bot_language_keyboard
from .messages import create_product_description
from .models import User, Product
from .enums import BOT_STATE_CHECKOUT_SHIPPING, BOT_STATE_INIT, logger, ADMIN_MENU, BOT_LANGUAGE_CHANGE
from .states import is_admin


def on_start(bot, update, user_data):
    user_id = get_user_id(update)
    username = get_username(update)
    locale = get_locale(update)
    _ = get_trans(user_id)
    try:
        User.get(telegram_id=user_id)
    except User.DoesNotExist:
        user = User(telegram_id=user_id, username=username, locale=locale)
        user.save()
    BOT_ON = config.get_bot_on_off() and username not in config.get_banned_users()
    if BOT_ON or is_admin(bot, user_id):
        if is_customer(bot, user_id) or is_vip_customer(bot, user_id):
            total = cart.get_cart_total(get_user_session(user_id))
            logger.info('Starting session for user %s, language: %s',
                        update.message.from_user.id,
                        update.message.from_user.language_code)
            update.message.reply_text(
                text=config.get_welcome_text().format(
                    update.message.from_user.first_name),
                reply_markup=create_main_keyboard(user_id, config.get_reviews_channel(),
                                                  is_admin(bot, user_id),
                                                  total),
            )
            return BOT_STATE_INIT
        else:
            logger.info('User %s rejected (not a customer)',
                        update.message.from_user.id)
            update.message.reply_text(
                text=_('Sorry {}\nYou are not authorized to use '
                       'this bot').format(update.message.from_user.first_name),
                reply_markup=None,
                parse_mode=ParseMode.HTML,
            )
            return ConversationHandler.END
    else:
        update.message.reply_text(
            text=_('Sorry {}, the bot is currently switched off').format(
                update.message.from_user.first_name),
            parse_mode=ParseMode.HTML,
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
    if BOT_ON or is_admin(bot, user_id):
        if is_customer(bot, user_id) or is_vip_customer(bot, user_id):
            if data == 'menu_products':
                # the menu disappears
                bot.edit_message_text(chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      text=_('Our products:'),
                                      parse_mode=ParseMode.MARKDOWN, )

                # send_products to current chat
                for product in Product.filter(is_active=True):
                    product_count = cart.get_product_count(
                        user_data, product.id)
                    subtotal = cart.get_product_subtotal(
                        user_data, product.id)
                    delivery_fee = config.get_delivery_fee()
                    delivery_min = config.get_delivery_min()
                    product_title, prices = cart.product_full_info(
                        user_data, product.id)
                    image_data = product.image
                    image_stream = io.BytesIO(image_data)
                    bot.send_photo(query.message.chat_id,
                                   photo=image_stream)
                    bot.send_message(query.message.chat_id,
                                     text=create_product_description(
                                         product_title, prices,
                                         product_count, subtotal,
                                         delivery_min, delivery_fee),
                                     reply_markup=create_product_keyboard(user_id,
                                                                          product.id, user_data, cart),
                                     parse_mode=ParseMode.HTML,
                                     timeout=20, )

                # send menu again as a new message
                bot.send_message(query.message.chat_id,
                                 text=config.get_order_text(),
                                 reply_markup=create_main_keyboard(user_id,
                                                                   config.get_reviews_channel(),
                                                                   is_admin(bot, user_id), total),
                                 parse_mode=ParseMode.HTML, )
            elif data == 'menu_order':
                if cart.is_full(user_data):
                    # we are not using enter_state_... here because it relies
                    #  on update.message
                    bot.send_message(query.message.chat_id,
                                     text=_('Please choose pickup or delivery'),
                                     reply_markup=create_shipping_keyboard(user_id),
                                     parse_mode=ParseMode.MARKDOWN, )
                    query.answer()
                    return BOT_STATE_CHECKOUT_SHIPPING
                else:
                    bot.answer_callback_query(
                        query.id,
                        text=_('Your cart is empty. '
                               'Please add something to the cart.'),
                        parse_mode=ParseMode.MARKDOWN, )
                    return BOT_STATE_INIT

            elif data == 'menu_language':
                bot.edit_message_text(chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      text=_('🈚︎  Languages'),
                                      reply_markup=create_bot_language_keyboard(user_id),
                                      parse_mode=ParseMode.MARKDOWN)

                query.answer()
                return BOT_LANGUAGE_CHANGE

            elif data == 'menu_hours':
                bot.edit_message_text(chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      text=config.get_working_hours(),
                                      reply_markup=create_main_keyboard(user_id,
                                                                        config.get_reviews_channel(),
                                                                        is_admin(bot, user_id), total),
                                      parse_mode=ParseMode.MARKDOWN, )
            elif data == 'menu_contact':
                bot.edit_message_text(chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      text=config.get_contact_info(),
                                      reply_markup=create_main_keyboard(user_id,
                                                                        config.get_reviews_channel(),
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

                bot.edit_message_text(chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      text=create_product_description(
                                          product_title, prices,
                                          product_count, subtotal,
                                          delivery_min, delivery_fee),
                                      reply_markup=create_product_keyboard(user_id,
                                                                           product_id, user_data, cart),
                                      parse_mode=ParseMode.HTML, )
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

                bot.edit_message_text(chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      text=create_product_description(
                                          product_title, prices,
                                          product_count, subtotal,
                                          delivery_min, delivery_fee),
                                      reply_markup=create_product_keyboard(user_id,
                                                                           product_id, user_data, cart),
                                      parse_mode=ParseMode.HTML, )
            elif data == 'menu_settings':
                bot.edit_message_text(chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      text=_('⚙️ Settings'),
                                      reply_markup=create_admin_keyboard(user_id),
                                      parse_mode=ParseMode.MARKDOWN, )
                query.answer()
                return ADMIN_MENU
            else:
                logger.warn('Unknown query: %s', query.data)
        else:
            logger.info('User %s rejected (not a customer)', user_id)
            bot.send_message(
                query.message.chat_id,
                text=_('Sorry {}\nYou are not authorized '
                       'to use this bot').format(query.from_user.first_name),
                reply_markup=None,
                parse_mode=ParseMode.HTML,
            )
            return ConversationHandler.END
    else:
        bot.send_message(
            query.message.chat_id,
            text=_('Sorry, the bot is currently switched off').format(
                query.from_user.first_name),
            reply_markup=None,
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    query.answer()
    # we want to remain in init state here
    return BOT_STATE_INIT


def on_error(bot, update, error):
    logger.error('Error: %s', error)