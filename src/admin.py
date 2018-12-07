import io
import os
import mimetypes

from telegram import ParseMode
from telegram import ReplyKeyboardRemove
from telegram.error import TelegramError
from telegram.ext import ConversationHandler

from . import enums
from .helpers import session_client, get_config_session, get_user_id, set_config_session, config, get_trans, \
    parse_discount, get_channel_trans
from .models import Product, ProductCount, Courier, Location, CourierLocation, ProductWarehouse, User, \
    ProductMedia, ProductCategory, IdentificationStage, Order, OrderPhotos, IdentificationQuestion
from .keyboards import create_back_button, create_bot_couriers_keyboard, create_bot_channels_keyboard, \
    create_bot_settings_keyboard, create_bot_order_options_keyboard, \
    create_ban_list_keyboard, create_courier_locations_keyboard, create_bot_locations_keyboard, \
    create_locations_keyboard, create_bot_products_keyboard, create_bot_product_add_keyboard, \
    general_select_keyboard, general_select_one_keyboard, create_warehouse_keyboard, \
    create_edit_identification_keyboard, create_edit_restriction_keyboard, create_product_media_keyboard, \
    create_categories_keyboard, create_add_courier_keyboard, create_delivery_fee_keyboard, \
    create_general_on_off_keyboard, create_bot_product_edit_keyboard, create_product_edit_media_keyboard, \
    create_edit_identification_type_keyboard, create_bot_orders_keyboard

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
        enums.logger.error("Failed to check admin id: %s", e)
        return False


def on_start_admin(bot, update):
    user_id = get_user_id(update)
    if not is_admin(bot, user_id):
        _ = get_trans(user_id)
        enums.logger.info(_('User %s, @%s rejected (not admin)'),
                    update.message.from_user.id,
                    update.message.from_user.username)
        update.message.reply_text(text=_(
            'Sorry {}, you are not authorized to administrate this bot').format(
            update.message.from_user.first_name))
        return enums.BOT_STATE_INIT


def on_admin_cmd_add_product(bot, update):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    update.message.reply_text(
        text=_('Enter new product title'),
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return enums.ADMIN_TXT_PRODUCT_TITLE


def on_admin_order_options(bot, update, user_data):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    if data == 'bot_order_options_back':
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=_('⚙ Bot settings'),
                              reply_markup=create_bot_settings_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_BOT_SETTINGS
    if data == 'bot_order_options_orders':
        bot.edit_message_text(_('📖 Orders'), chat_id, message_id, reply_markup=create_bot_orders_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_ORDERS
    if data == 'bot_order_options_product':
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=_('🏪 My Products'),
                              reply_markup=create_bot_products_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_PRODUCTS
    if data == 'bot_order_options_categories':
        bot.edit_message_text(_('🛍 Categories'), chat_id, message_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_categories_keyboard(_)
        )
        query.answer()
        return enums.ADMIN_CATEGORIES
    elif data == 'bot_order_options_warehouse':
        products = Product.filter(is_active=True)
        if not products:
            bot.send_message(chat_id, _('You don\'t have any products yet'))
            bot.send_message(chat_id, _('⚙ Bot settings'), reply_markup=create_bot_settings_keyboard(_))
            return enums.ADMIN_BOT_SETTINGS
        products = [(product.title, product.id) for product in products]
        products_keyboard = general_select_one_keyboard(_, products)
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=_('Select a product'),
                              reply_markup=products_keyboard, parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_WAREHOUSE_PRODUCT
    elif data == 'bot_order_options_discount':
        bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            text=_('Enter discount like:\n'
                   '50 > 500: all deals above 500$ will be -50$\n'
                   '10% > 500: all deals above 500$ will be -10%\n'
                   'Current discount: {} > {}'.format(config.get_discount(), config.get_discount_min())),
            reply_markup=create_back_button(_),
            parse_mode=ParseMode.MARKDOWN,
        )
        query.answer()
        return enums.ADMIN_ADD_DISCOUNT
    elif data == 'bot_order_options_delivery_fee':
        msg = _('🚕 Delivery fee')
        bot.edit_message_text(msg, chat_id, message_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_delivery_fee_keyboard(_))
        query.answer()
        return enums.ADMIN_DELIVERY_FEE
    elif data == 'bot_order_options_add_locations':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('🎯 Locations'),
                              reply_markup=create_bot_locations_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_LOCATIONS
    elif data == 'bot_order_options_identify':
        questions = IdentificationStage.select(IdentificationStage.id, IdentificationStage.active, IdentificationStage.vip_required).tuples()
        msg = _('👨 Edit identification process:')
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_edit_identification_keyboard(_, questions),
                              parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_EDIT_IDENTIFICATION_STAGES
    elif data == 'bot_order_options_restricted':
        msg = _('🔥 Edit restricted area:')
        first = config.get_only_for_customers()
        second = config.get_vip_customers()
        user_data['edit_restricted_area'] = (first, second)
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_edit_restriction_keyboard(_, (first, second)),
                              parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_EDIT_RESTRICTION
    elif data == 'bot_order_options_welcome':
        msg = _('Type new welcome message.\n')
        msg += _('Current message:\n\n{}').format(config.get_welcome_text())
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_back_button(_),
                              parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_EDIT_WELCOME_MESSAGE
    elif data == 'bot_order_options_details':
        msg = _('Type new order details message.\n')
        msg += _('Current message:\n\n{}').format(config.get_order_text())
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_back_button(_),
                              parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_EDIT_ORDER_DETAILS
    elif data == 'bot_order_options_final':
        msg = _('Type new final message.\n')
        msg += _('Current message:\n\n{}').format(config.get_order_complete_text())
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=msg,
                              reply_markup=create_back_button(_),
                              parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_EDIT_FINAL_MESSAGE

    return ConversationHandler.END


def on_admin_orders(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    msg_id = query.message.message_id
    action = query.data
    if action == 'back':
        msg = _('💳 Order options')
        bot.edit_message_text(msg, chat_id, msg_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_bot_order_options_keyboard(_))
        query.answer()
        return enums.ADMIN_ORDER_OPTIONS
    if action == 'pending':
        orders = Order.select().where(Order.delivered == False)
        orders_data = [(order.id, order.date_created.strftime('%d/%m/%Y')) for order in orders]
        orders = [('Order №{} {}'.format(order_id, order_date), order_id) for order_id, order_date in orders_data]
        user_data['admin_pending_orders'] = orders
        keyboard = general_select_one_keyboard(_, orders)
        msg = _('Please select an order\n'
                'Bot will send it to service channel:')
        bot.edit_message_text(msg, chat_id, msg_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=keyboard)
        query.answer()
        return enums.ADMIN_ORDERS_PENDING_SELECT
    elif action == 'finished':
        state = enums.ADMIN_ORDERS_FINISHED_DATE
        shortcuts.initialize_calendar(bot, user_data, chat_id, msg_id, state, _, query.id)
        return state


def on_admin_orders_pending_select(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    action, val = query.data.split('|')
    if action == 'back':
        bot.edit_message_text(_('📖 Orders'), chat_id, message_id, reply_markup=create_bot_orders_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_ORDERS
    if action == 'page':
        #orders = Order.select().where(Order.delivered == False).tuples()
        orders = user_data['admin_pending_orders']
        keyboard = general_select_one_keyboard(_, orders, int(val))
        msg = _('Please select an order\n'
                'Bot will send it to service channel:')
        bot.edit_message_text(msg, chat_id, message_id,
                              reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        query.answer()
    elif action == 'select':
        # order = Order.get(id=val)
        service_trans = get_channel_trans()
        msg = service_trans('Order №{}').format(val)
        shortcuts.bot_send_order_msg(bot, config.get_service_channel(), msg, service_trans, val)
        query.answer(_('Order has been sent to service channel'), show_alert=True)
    return enums.ADMIN_ORDERS_PENDING_SELECT


def on_admin_orders_finished_date(bot, update, user_data):
    print('invoked\n\n')
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action, val = query.data.split('|')
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    if action == 'ignore':
        return enums.ADMIN_ORDERS_FINISHED_DATE
    elif action == 'back':
        bot.edit_message_text(_('📖 Orders'), chat_id, message_id, reply_markup=create_bot_orders_keyboard(_),
                             parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_ORDERS
    elif action in ('day', 'month', 'year'):
        print('if entered')
        year, month = user_data['calendar_date']
        queries = shortcuts.get_order_subquery(action, val, month, year)
        orders = Order.select().where(*queries)
        orders = orders.select().where(Order.delivered == True)
        orders_data = [(order.id, order.date_created.strftime('%d/%m/%Y')) for order in orders]
        orders = [('Order №{} {}'.format(order_id, order_date), order_id) for order_id, order_date in orders_data]
        user_data['admin_finished_orders'] = orders
        print('before edit msg')
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=_('Select order'),
                              reply_markup=general_select_one_keyboard(_, orders),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_ORDERS_FINISHED_SELECT


def on_admin_orders_finished_select(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action, val = query.data.split('|')
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    if action == 'back':
        state = enums.ADMIN_ORDERS_FINISHED_DATE
        shortcuts.initialize_calendar(bot, user_data, chat_id, message_id, state, _, query.id)
        return state
    orders = user_data['admin_finished_orders']
    if action == 'page':
        page_num = int(val)
        keyboard = general_select_one_keyboard(_, orders, page_num)
        msg = _('Select order')
    elif action == 'select':
        order = Order.get(id=val)
        msg = OrderPhotos.get(order=order).order_text
        courier_delivered = _('Courier: {}').format(order.courier.username)
        msg += '\n\n' + courier_delivered
        keyboard = general_select_one_keyboard(_, orders)
    bot.edit_message_text(msg, chat_id, message_id,
                          reply_markup=keyboard)
    query.answer()
    return enums.ADMIN_ORDERS_FINISHED_SELECT


def on_admin_delivery_fee(bot, update):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    msg_id = query.message.message_id
    action = query.data
    if action == 'add':
        msg = _('Enter delivery fee like:\n'
                '50 > 500: Deals below 500 will have delivery fee of 50\n'
                'or\n'
                '50: All deals will have delivery fee of 50\n'
                'Only works on delivery\n\n'
                'Current fee: {}').format(config.get_delivery_fee())
        bot.edit_message_text(
            msg, chat_id, msg_id,
            reply_markup=create_back_button(_),
            parse_mode=ParseMode.MARKDOWN,
        )
        query.answer()
        return enums.ADMIN_ADD_DELIVERY_FEE
    elif action == 'back':
        msg = _('💳 Order options')
        bot.edit_message_text(msg, chat_id, msg_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_bot_order_options_keyboard(_))
        return enums.ADMIN_ORDER_OPTIONS
    elif action == 'vip':
        msg = _('Activate delivery fee for vip customers')
        bot.edit_message_text(msg, chat_id, msg_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_general_on_off_keyboard(_))
        query.answer()
        return enums.ADMIN_DELIVERY_FEE_VIP


def on_admin_delivery_fee_vip(bot, update):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    msg_id = query.message.message_id
    action = query.data
    if action == 'back':
        msg = _('🚕 Delivery fee')
        # bot.edit_message_text(msg, chat_id, msg_id, parse_mode=ParseMode.MARKDOWN,
        #                       reply_markup=create_delivery_fee_keyboard(_))
        # query.answer()
        # return enums.ADMIN_DELIVERY_FEE
    else:
        callback_map = {
            'on': (True, _('Delivery fee for vip customers was activated')),
            'off': (False, _('Delivery fee for vip customers was deactivated'))
        }
        config_val, msg = callback_map[action]
        config_session = get_config_session()
        config_session['delivery_fee_for_vip'] = config_val
        set_config_session(config_session)
    bot.edit_message_text(msg, chat_id, msg_id, parse_mode=ParseMode.MARKDOWN,
                          reply_markup=create_delivery_fee_keyboard(_))
    query.answer()
    return enums.ADMIN_DELIVERY_FEE

# bot.send_message(chat_id=update.message.chat_id,
#                  text='Delivery fee was changed',
#                  reply_markup=create_bot_order_options_keyboard(_),
#                  parse_mode=ParseMode.MARKDOWN)
# return enums.ADMIN_ORDER_OPTIONS

def on_admin_categories(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    action = query.data
    if action == 'add':
        msg = _('Please enter the name of category')
        bot.edit_message_text(msg, chat_id, message_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_back_button(_))
        query.answer()
        return enums.ADMIN_CATEGORY_ADD
    elif action == 'back':
        bot.edit_message_text(_('💳 Order options'), chat_id, message_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_bot_order_options_keyboard(_))
        query.answer()
        return enums.ADMIN_ORDER_OPTIONS
    categories = ProductCategory.select(ProductCategory.title, ProductCategory.id).tuples()
    keyboard = general_select_one_keyboard(_, categories)
    msg = _('Please select a category:')
    bot.edit_message_text(msg, chat_id, message_id,
                          parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    query.answer()
    if action == 'products':
        return enums.ADMIN_CATEGORY_PRODUCTS_SELECT
    elif action == 'remove':
        return enums.ADMIN_CATEGORY_REMOVE_SELECT


def on_admin_category_add(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        upd_msg = update.callback_query.message
        bot.edit_message_text(_('🛍 Categories'), upd_msg.chat_id, upd_msg.message_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_categories_keyboard(_))
        query.answer()
        return enums.ADMIN_CATEGORIES
    answer = update.message.text
    try:
        cat = ProductCategory.get(title=answer)
        msg = _('Category with name `{}` exists already').format(cat.title)
    except ProductCategory.DoesNotExist:
        categories = ProductCategory.select().exists()
        if not categories:
            def_cat = ProductCategory.create(title='Default')
            for product in Product.filter(is_active=True):
                product.category = def_cat
                product.save()
        cat = ProductCategory.create(title=answer)
        msg = _('Category `{}` has been created').format(cat.title)
    bot.send_message(update.message.chat_id, msg, parse_mode=ParseMode.HTML, reply_markup=create_categories_keyboard(_))
    return enums.ADMIN_CATEGORIES


def on_admin_category_products_select(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    action, val = query.data.split('|')
    if action == 'page':
        categories = ProductCategory.select(ProductCategory.title, ProductCategory.id).tuples()
        keyboard = general_select_one_keyboard(_, categories, int(val))
        bot.edit_message_text(_('Please select a category'), chat_id, message_id,
                              reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_CATEGORY_PRODUCTS_SELECT
    elif action == 'back':
        bot.edit_message_text(_('🛍 Categories'), chat_id, message_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_categories_keyboard(_))
        query.answer()
        return enums.ADMIN_CATEGORIES
    elif action == 'select':
        user_data['category_products_add'] = {'category_id': val, 'page': 1, 'products_ids': []}
        products = []
        for product in Product.filter(is_active=True):
            category = product.category
            if category:
                product_title = '{} ({})'.format(product.title, category.title)
            else:
                product_title = product.title
            products.append((product_title, product.id, False))
        msg = _('Please select products to add')
        bot.edit_message_text(msg, chat_id, message_id, reply_markup=general_select_keyboard(_, products),
                              parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_CATEGORY_PRODUCTS_ADD


def on_admin_category_remove(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    action, val = query.data.split('|')
    if action == 'page':
        categories = ProductCategory.select(ProductCategory.title, ProductCategory.id).tuples()
        keyboard = general_select_one_keyboard(_, categories, int(val))
        bot.edit_message_text(_('Please select a category'), chat_id, message_id,
                              reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_CATEGORY_REMOVE_SELECT
    if action == 'back':
        bot.edit_message_text(_('🛍 Categories'), chat_id, message_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_categories_keyboard(_))
    elif action == 'select':
        cat_len = ProductCategory.select().count()
        cat = ProductCategory.get(id=val)
        if cat.title == 'Default' and cat_len > 1:
            msg = _('Cannot delete default category')
        else:
            default = ProductCategory.get(title='Default')
            if cat_len == 2:
                default.delete_instance()
            else:
                for product in cat.products:
                    product.category = default
                    product.save()
            cat.delete_instance()
            msg = _('Category "{}" has been deleted').format(cat.title)
        bot.edit_message_text(msg, chat_id, message_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_categories_keyboard(_))
    query.answer()
    return enums.ADMIN_CATEGORIES


def on_admin_category_products_add(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    action, val = query.data.split('|')
    selected_ids = user_data['category_products_add']['products_ids']
    if action == 'done':
        cat_id = user_data['category_products_add']['category_id']
        cat = ProductCategory.get(id=cat_id)
        if selected_ids:
            products = Product.filter(Product.id << selected_ids)
            for product in products:
                product.category = cat
                product.save()
        msg = _('Category "{}" was updated').format(cat.title)
        del user_data['category_products_add']
        bot.edit_message_text(msg, chat_id, message_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_categories_keyboard(_))
        query.answer()
        return enums.ADMIN_CATEGORIES
    products = []
    current_page = user_data['category_products_add']['page']
    if action == 'page':
        current_page = int(val)
        user_data['category_products_add']['page'] = current_page
    elif action == 'select':
        if val in selected_ids:
            selected_ids.remove(val)
        else:
            selected_ids.append(val)
    for product in Product.filter(is_active=True):
        if str(product.id) in selected_ids:
            selected = True
        else:
            selected = False
        category = product.category
        if category:
            product_title = '{} ({})'.format(product.title, category.title)
        else:
            product_title = product.title
        products.append((product_title, product.id, selected))
    products_keyboard = general_select_keyboard(_, products, current_page)
    msg = _('Please select products to add')
    bot.edit_message_text(msg, chat_id, message_id, parse_mode=ParseMode.MARKDOWN,
                          reply_markup=products_keyboard)
    query.answer()
    return enums.ADMIN_CATEGORY_PRODUCTS_ADD



def on_admin_warehouse_products(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    action, val = query.data.split('|')
    if action == 'page':
        products = Product.filter(is_active=True)
        products = [(product.title, product.id) for product in products]
        products_keyboard = general_select_one_keyboard(_, products, int(val))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=_('Select a product'),
                              reply_markup=products_keyboard, parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_WAREHOUSE_PRODUCT
    elif action == 'back':
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=_('💳 Order options'),
                              reply_markup=create_bot_order_options_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_ORDER_OPTIONS
    elif action == 'select':
        user_data['product_warehouse'] = {'product_id': val}
        product = Product.get(id=val)
        msg = _('🏗\nProduct: `{}`\n'
                'Credits: {}').format(product.title, product.credits)
        bot.edit_message_text(msg, chat_id, message_id, reply_markup=create_warehouse_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_WAREHOUSE


def on_admin_warehouse(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    data = query.data
    if data == 'warehouse_back':
        products = Product.filter(is_active=True)
        products = [(product.title, product.id) for product in products]
        products_keyboard = general_select_one_keyboard(_, products)
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=_('Select a product'),
                              reply_markup=products_keyboard, parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_WAREHOUSE_PRODUCT
    elif data == 'warehouse_credits':
        product_id = user_data['product_warehouse']['product_id']
        product = Product.get(id=product_id)
        msg = _('🏗\nProduct: `{}`\n'
                'Credits: {}\n'
                'Please enter new number of credits:').format(product.title, product.credits)
        bot.edit_message_text(msg, chat_id, message_id=message_id, reply_markup=create_back_button(_), parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_WAREHOUSE_PRODUCT_CREDITS
    elif data == 'warehouse_courier':
        couriers = Courier.select(Courier.username, Courier.id).where(Courier.is_active == True).tuples()
        couriers_keyboard = general_select_one_keyboard(_, couriers)
        bot.edit_message_text(_('Select a courier'), chat_id, message_id=message_id, reply_markup=couriers_keyboard)
        query.answer()
        return enums.ADMIN_WAREHOUSE_COURIER


def on_admin_warehouse_courier(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    action, val = query.data.split('|')
    if action == 'page':
        couriers = Courier.select(Courier.username, Courier.id).where(Courier.is_active == True).tuples()
        couriers_keyboard = general_select_one_keyboard(_, couriers, int(val))
        bot.edit_message_text(_('Select a courier'), chat_id, message_id=message_id, reply_markup=couriers_keyboard)
        query.answer()
        return enums.ADMIN_WAREHOUSE_COURIER
    elif action == 'back':
        product_id = user_data['product_warehouse']['product_id']
        product = Product.get(id=product_id)
        msg = _('🏗\nProduct: `{}`\n'
                'Credits: {}').format(product.title, product.credits)
        bot.edit_message_text(msg, chat_id, message_id, reply_markup=create_warehouse_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_WAREHOUSE
    elif action == 'select':
        product_id = user_data['product_warehouse']['product_id']
        product = Product.get(id=int(product_id))
        courier = Courier.get(id=int(val))
        try:
            product_warehouse = ProductWarehouse.get(courier=courier, product=product)
        except ProductWarehouse.DoesNotExist:
            product_warehouse = ProductWarehouse(courier=courier, product=product)
            product_warehouse.save()
        user_data['product_warehouse']['courier_warehouse_id'] = product_warehouse.id
        msg = _('🏗\nProduct: `{}`\n'
                'Courier: `{}`\n'
                'Courier credits: {}\n'
                'Please enter new number of credits:').format(product.title, courier.username, product_warehouse.count)
        bot.edit_message_text(msg, chat_id, message_id=message_id, reply_markup=create_back_button(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_WAREHOUSE_COURIER_CREDITS


def on_admin_warehouse_product_credits(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    product_id = user_data['product_warehouse']['product_id']
    product = Product.get(id=product_id)
    if update.callback_query and update.callback_query.data == 'back':
        msg = _('🏗\nProduct: `{}`\n'
                'Credits: {}').format(product.title, product.credits)
        bot.edit_message_text(msg, update.callback_query.message.chat_id, update.callback_query.message.message_id, reply_markup=create_warehouse_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_WAREHOUSE
    text = update.message.text
    chat_id = update.message.chat_id
    try:
        credits = int(text)
    except ValueError:
        msg = _('Please enter a number:')
        bot.send_message(chat_id, msg, reply_markup=create_back_button(_))
        return enums.ADMIN_WAREHOUSE_PRODUCT_CREDITS
    credits = abs(credits)
    if credits > 2**63-1:
        msg = _('Entered amount is too big\n'
                'Please enter new number of credits:')
        bot.send_message(chat_id, msg, reply_markup=create_back_button(_))
        return enums.ADMIN_WAREHOUSE_PRODUCT_CREDITS
    product.credits = credits
    product.save()
    msg = _('✅ Product\'s credits were changed to {}').format(credits)
    bot.send_message(chat_id, msg)
    msg = _('🏗\nProduct: `{}`\n'
            'Credits: {}').format(product.title, product.credits)
    bot.send_message(chat_id, msg, reply_markup=create_warehouse_keyboard(_), parse_mode=ParseMode.MARKDOWN)
    return enums.ADMIN_WAREHOUSE


def on_admin_warehouse_courier_credits(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        q_msg = update.callback_query.message
        couriers = Courier.select(Courier.username, Courier.id).where(Courier.is_active == True).tuples()
        couriers_keyboard = general_select_one_keyboard(_, couriers)
        bot.edit_message_text(_('Select a courier'), q_msg.chat_id, message_id=q_msg.message_id,
                              reply_markup=couriers_keyboard)
        update.callback_query.answer()
        return enums.ADMIN_WAREHOUSE_COURIER
    text = update.message.text
    chat_id = update.message.chat_id
    try:
        credits = int(text)
    except ValueError:
        msg = _('Please enter a number:')
        bot.send_message(chat_id, msg, reply_markup=create_back_button(_))
        return enums.ADMIN_WAREHOUSE_COURIER_CREDITS
    product_id = user_data['product_warehouse']['product_id']
    product = Product.get(id=product_id)
    warehouse_id = user_data['product_warehouse']['courier_warehouse_id']
    courier_warehouse = ProductWarehouse.get(id=warehouse_id)
    total_credits = product.credits + courier_warehouse.count
    if credits > total_credits:
        msg = _('Cannot give to courier more credits than you have in warehouse: {}\n'
                'Please enter new number of credits:').format(total_credits)
        bot.send_message(chat_id, msg, reply_markup=create_back_button(_))
        return enums.ADMIN_WAREHOUSE_COURIER_CREDITS
    admin_credits = product.credits - (credits - courier_warehouse.count)
    product.credits = admin_credits
    courier_warehouse.count = credits
    courier_warehouse.save()
    product.save()
    msg = _('✅ You have given {} credits to courier `{}`').format(credits, courier_warehouse.courier.username)
    bot.send_message(chat_id, msg, parse_mode=ParseMode.MARKDOWN)
    msg = _('🏗\nProduct: `{}`\n'
            'Credits: {}').format(product.title, product.credits)
    bot.send_message(chat_id, msg, reply_markup=create_warehouse_keyboard(_), parse_mode=ParseMode.MARKDOWN)
    return enums.ADMIN_WAREHOUSE


def on_admin_products(bot, update, user_data):
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
        return enums.ADMIN_ORDER_OPTIONS
    elif data == 'bot_products_view':
        products = Product.select(Product.title, Product.id).where(Product.is_active == True).tuples()
        if not products:
            query.answer(_('You don\'t have products'))
            return enums.ADMIN_PRODUCTS
        msg = _('Select a product:')
        bot.edit_message_text(msg, chat_id, message_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=general_select_one_keyboard(_, products))
        query.answer()
        return enums.ADMIN_PRODUCTS_SHOW
    elif data == 'bot_products_add':
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=_('➕ Add product'),
                              reply_markup=create_bot_product_add_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_PRODUCT_ADD
    elif data == 'bot_products_edit':
        products = Product.select(Product.title, Product.id).where(Product.is_active==True).tuples()
        products_keyboard = general_select_one_keyboard(_, products)
        msg = _('Select a product to edit')
        bot.edit_message_text(msg, chat_id, message_id, parse_mode=ParseMode.MARKDOWN, reply_markup=products_keyboard)
        query.answer()
        return enums.ADMIN_PRODUCT_EDIT_SELECT
    elif data == 'bot_products_remove':
        products = Product.filter(is_active=True)
        if not products:
            msg = _('No products to delete')
            query.answer(text=msg)
            return enums.ADMIN_PRODUCTS
        user_data['products_remove'] = {'ids': [], 'page': 1}
        products = [(product.title, product.id, False) for product in products]
        products_keyboard = general_select_keyboard(_, products)
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=_('Select a product which you want to remove'),
                              reply_markup=products_keyboard, parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_DELETE_PRODUCT


def on_admin_show_product(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id, msg_id = query.message.chat_id, query.message.message_id
    action, param = query.data.split('|')
    if action == 'back':
        msg = _('🏪 My Products')
        bot.edit_message_text(msg, chat_id, msg_id,
                              reply_markup=create_bot_products_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_PRODUCTS
    products = Product.select(Product.title, Product.id).where(Product.is_active == True).tuples()
    if action == 'page':
        current_page = int(param)
        msg = _('Select a product:')
        bot.edit_message_text(msg, chat_id, msg_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=general_select_one_keyboard(_, products, current_page))
        query.answer()
    elif action == 'select':
        product = Product.get(id=param)
        bot.delete_message(chat_id, msg_id)
        product_prices = ((obj.count, obj.price) for obj in product.product_counts)
        shortcuts.send_product_media(bot, product, chat_id)
        msg = messages.create_admin_product_description(_, product.title, product_prices)
        bot.send_message(chat_id, msg)
        msg = _('Select a product:')
        bot.send_message(chat_id, msg, parse_mode=ParseMode.MARKDOWN,
                         reply_markup=general_select_one_keyboard(_, products))
        query.answer()
    return enums.ADMIN_PRODUCTS_SHOW


def on_admin_product_edit_select(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id, msg_id = query.message.chat_id, query.message.message_id
    action, param = query.data.split('|')
    if action == 'back':
        msg = _('🏪 My Products')
        bot.edit_message_text(msg, chat_id, msg_id,
                              reply_markup=create_bot_products_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_PRODUCTS
    if action == 'page':
        products = Product.select(Product.title, Product.id).where(Product.is_active == True).tuples()
        msg = _('Select a product to edit')
        current_page = int(param)
        bot.edit_message_text(msg, chat_id, msg_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=general_select_one_keyboard(_, products, current_page))
        query.answer()
        return enums.ADMIN_PRODUCT_EDIT_SELECT
    elif action == 'select':
        product = Product.get(id=param)
        user_data['admin_product_edit_id'] = product.id
        msg = _('Edit product "{}"').format(product.title)
        bot.edit_message_text(msg, chat_id, msg_id, reply_markup=create_bot_product_edit_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_PRODUCT_EDIT


def on_admin_product_edit(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id, msg_id = query.message.chat_id, query.message.message_id
    action = query.data
    if action == 'back':
        products = Product.select(Product.title, Product.id).where(Product.is_active == True).tuples()
        msg = _('Select a product to edit')
        bot.edit_message_text(msg, chat_id, msg_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=general_select_one_keyboard(_, products))
        query.answer()
        return enums.ADMIN_PRODUCT_EDIT_SELECT
    product_id = user_data['admin_product_edit_id']
    product = Product.get(id=product_id)
    if action == 'title':
        msg = _('Current title: {}').format(product.title)
        bot.edit_message_text(msg, chat_id, msg_id, parse_mode=ParseMode.MARKDOWN)
        msg = _('Enter new title for product')
        bot.send_message(chat_id, msg, reply_markup=create_back_button(_), parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_PRODUCT_EDIT_TITLE
    elif action == 'price':
        prices_str = _('Current prices:\n\n')
        for price in product.product_counts:
            price_str = _('x {} = ${}\n').format(price.count, price.price)
            prices_str += price_str
        bot.edit_message_text(prices_str, chat_id, msg_id, parse_mode=ParseMode.MARKDOWN)
        msg = _('Enter prices for new product\none per line in the format\n*COUNT PRICE*, e.g. *1 10*')
        bot.send_message(chat_id, msg, reply_markup=create_back_button(_), parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_PRODUCT_EDIT_PRICES
    elif action == 'media':
        bot.delete_message(chat_id, msg_id)
        shortcuts.send_product_media(bot, product, chat_id)
        msg = _('Upload new photos for product')
        bot.send_message(chat_id, msg, reply_markup=create_product_edit_media_keyboard(_), parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_PRODUCT_EDIT_MEDIA


def on_admin_product_edit_title(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    product_id = user_data['admin_product_edit_id']
    product = Product.get(id=product_id)
    if update.callback_query and update.callback_query.data == 'back':
        upd_msg = update.callback_query.message
        msg = _('Edit product "{}"').format(product.title)
        bot.edit_message_text(msg, upd_msg.chat_id, upd_msg.message_id, reply_markup=create_bot_product_edit_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
    else:
        upd_msg = update.message
        product.title = upd_msg.text
        product.save()
        msg = _('Product\'s title has been updated')
        bot.send_message(upd_msg.chat_id, msg, reply_markup=create_bot_product_edit_keyboard(_),
                         parse_mode=ParseMode.MARKDOWN)
    return enums.ADMIN_PRODUCT_EDIT


def on_admin_product_edit_prices(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    product_id = user_data['admin_product_edit_id']
    product = Product.get(id=product_id)
    if update.callback_query and update.callback_query.data == 'back':
        upd_msg = update.callback_query.message
        msg = _('Edit product "{}"').format(product.title)
        bot.edit_message_text(msg, upd_msg.chat_id, upd_msg.message_id,
                              reply_markup=create_bot_product_edit_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
    else:
        upd_msg = update.message
        prices_list = []
        try:
            for line in upd_msg.text.split('\n'):
                count_str, price_str = line.split()
                count = int(count_str)
                price = float(price_str)
                prices_list.append((count, price))
        except ValueError:
            msg = _('Could not read prices, please try again')
        else:
            for product_count in product.product_counts:
                product_count.delete_instance()
            for count, price in prices_list:
                ProductCount.create(product=product, count=count, price=price)
            msg = _('Product\'s prices have been updated')
        bot.send_message(upd_msg.chat_id, msg, reply_markup=create_bot_product_edit_keyboard(_),
                         parse_mode=ParseMode.MARKDOWN)
    return enums.ADMIN_PRODUCT_EDIT


def on_admin_product_edit_media(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    upd_msg = update.message
    msg_text = upd_msg.text
    chat_id = update.message.chat_id
    product_id = user_data['admin_product_edit_id']
    product = Product.get(id=product_id)
    if msg_text == _('Save Changes'):
        try:
            files = user_data['admin_product_edit_files']
        except KeyError:
            msg = _('Send photos for new product')
            bot.send_message(chat_id, msg)
            return enums.ADMIN_PRODUCT_EDIT_MEDIA
        for media in product.product_media:
            media.delete_instance()
        for file_id in files:
            ProductMedia.create(product=product, file_id=file_id)
        del user_data['admin_product_edit_files']
        msg = _('Product\'s media has been updated\n✅')
        bot.send_message(chat_id, msg, reply_markup=ReplyKeyboardRemove())
        msg = _('Edit product "{}"').format(product.title)
        bot.send_message(upd_msg.chat_id, msg, reply_markup=create_bot_product_edit_keyboard(_),
                         parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_PRODUCT_EDIT
    elif msg_text == _('❌ Cancel'):
        bot.send_message(chat_id, _('Cancelled'), reply_markup=ReplyKeyboardRemove())
        msg = _('Edit product "{}"').format(product.title)
        bot.send_message(upd_msg.chat_id, msg, reply_markup=create_bot_product_edit_keyboard(_),
                         parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_PRODUCT_EDIT
    file = upd_msg.photo
    if type(file) == list:
        file = file[-1]
    if not user_data.get('admin_product_edit_files'):
        user_data['admin_product_edit_files'] = [file.file_id]
    else:
        user_data['admin_product_edit_files'].append(file.file_id)
    return enums.ADMIN_PRODUCT_EDIT_MEDIA


def on_admin_delete_product(bot, update, user_data):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action, param = data.split('|')
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    selected_ids = user_data['products_remove']['ids']
    if action == 'done':
        if selected_ids:
            products = Product.filter(Product.id << selected_ids)
            for product in products:
                product.is_active = False
                product.save()
            msg = _('Products have been removed')
            query.answer(text=msg)
        del user_data['products_remove']
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=_('🏪 My Products'),
                              reply_markup=create_bot_products_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_PRODUCTS
    products = []
    current_page = user_data['products_remove']['page']
    if action == 'page':
        current_page = int(param)
        user_data['products_remove']['page'] = current_page
    elif action == 'select':
        if param in selected_ids:
            selected_ids.remove(param)
        else:
            selected_ids.append(param)
    for product in Product.filter(is_active=True):
        if str(product.id) in selected_ids:
            selected = True
        else:
            selected = False
        products.append((product.title, product.id, selected))
    products_keyboard = general_select_keyboard(_, products, current_page)
    bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                          text=_('Select a product which you want to remove'),
                          reply_markup=products_keyboard, parse_mode=ParseMode.MARKDOWN)
    query.answer()
    return enums.ADMIN_DELETE_PRODUCT


def on_admin_product_add(bot, update, user_data):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    if data == 'bot_product_back':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('🏪 My Products'),
                              reply_markup=create_bot_products_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_PRODUCTS
    elif data == 'bot_product_new':
        bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=_('Enter new product title'),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_back_button(_),
            )
        query.answer()
        return enums.ADMIN_TXT_PRODUCT_TITLE
    elif data == 'bot_product_last':
        inactive_products = Product.filter(is_active=False)
        if not inactive_products:
            msg = _('You don\'t have last products')
            query.answer(text=msg)
            return enums.ADMIN_PRODUCT_ADD
        inactive_products = [(product.title, product.id, False) for product in inactive_products]
        user_data['last_products_add'] = {'ids': [], 'page': 1}
        products_keyboard = general_select_keyboard(_, inactive_products)
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=_('Select a product which you want to activate again'),
                              reply_markup=products_keyboard, parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_PRODUCT_LAST_ADD


def on_admin_product_last_select(bot, update, user_data):
    query = update.callback_query
    data = query.data
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    action, param = data.split('|')
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    selected_ids = user_data['last_products_add']['ids']
    if action == 'done':
        if selected_ids:
            products = Product.filter(Product.id << selected_ids)
            for product in products:
                product.is_active = True
                product.save()
            msg = _('Products have been added')
            query.answer(text=msg)
        del user_data['last_products_add']
        bot.edit_message_text(_('➕ Add product'), chat_id, message_id,
                              reply_markup=create_bot_product_add_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_PRODUCT_ADD
    inactive_products = []
    current_page = user_data['last_products_add']['page']
    if action == 'page':
        current_page = int(param)
        user_data['last_products_add']['page'] = current_page
    elif action == 'select':
        if param in selected_ids:
            selected_ids.remove(param)
        else:
            selected_ids.append(param)
    for product in Product.filter(is_active=False):
        if str(product.id) in selected_ids:
            selected = True
        else:
            selected = False
        inactive_products.append((product.title, product.id, selected))
    products_keyboard = general_select_keyboard(_, inactive_products, current_page)
    bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                          text=_('Select a product which you want to activate again'),
                          reply_markup=products_keyboard, parse_mode=ParseMode.MARKDOWN)
    query.answer()
    return enums.ADMIN_PRODUCT_LAST_ADD


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
        return enums.ADMIN_PRODUCT_ADD

    title = update.message.text
    # initialize new product data
    user_data['add_product'] = {}
    user_data['add_product']['title'] = title
    update.message.reply_text(
        text=_('Enter new product prices\none per line in the format\n*COUNT PRICE*, e.g. *1 10*'),
        reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.MARKDOWN,
    )
    return enums.ADMIN_TXT_PRODUCT_PRICES


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
            return enums.ADMIN_TXT_PRODUCT_PRICES

    user_data['add_product']['prices'] = prices_list
    # msg = _('Send a photo/gif/video')
    # update.message.reply_text(
    #     text=msg, parse_mode=ParseMode.MARKDOWN,
    #     reply_markup=create_back_button(_)
    # )
    update.message.reply_text(
        text=_('Send photos for new product'),
        reply_markup=create_product_media_keyboard(_), parse_mode=ParseMode.MARKDOWN,
    )
    return enums.ADMIN_TXT_PRODUCT_PHOTO


def on_admin_txt_product_photo(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    upd_msg = update.message
    msg_text = upd_msg.text
    chat_id = update.message.chat_id
    if msg_text == _('Create Product'):
        title = user_data['add_product']['title']
        prices = user_data['add_product']['prices']
        try:
            files = user_data['add_product']['files']
        except KeyError:
            msg = _('Send photos for new product')
            bot.send_message(chat_id, msg)
            return enums.ADMIN_TXT_PRODUCT_PHOTO
        try:
            def_cat = ProductCategory.get(title='Default')
        except ProductCategory.DoesNotExist:
            product = Product.create(title=title)
        else:
            product = Product.create(title=title, category=def_cat)
        for count, price in prices:
            ProductCount.create(product=product, price=price, count=count)
        for file_id in files:
            ProductMedia.create(product=product, file_id=file_id)
        for courier in Courier:
            ProductWarehouse.create(product=product, courier=courier)
        # clear new product data
        del user_data['add_product']
        msg = _('New Product Created\n✅')
        bot.send_message(chat_id, msg, reply_markup=ReplyKeyboardRemove())
        bot.send_message(chat_id=chat_id,
                         text=_('🏪 My Products'),
                         reply_markup=create_bot_products_keyboard(_),
                         parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_PRODUCTS
    elif msg_text == _('❌ Cancel'):
        del user_data['add_product']
        bot.send_message(chat_id, _('Cancelled'), reply_markup=ReplyKeyboardRemove())
        bot.send_message(chat_id=chat_id,
                         text=_('🏪 My Products'),
                         reply_markup=create_bot_products_keyboard(_),
                         parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_PRODUCTS
    file = upd_msg.photo
    if type(file) == list:
        file = file[-1]
    if not user_data['add_product'].get('files'):
        user_data['add_product']['files'] = [file.file_id]
    else:
        user_data['add_product']['files'].append(file.file_id)
    return enums.ADMIN_TXT_PRODUCT_PHOTO

# def on_admin_txt_product_photo(bot, update, user_data):
#     user_id = get_user_id(update)
#     _ = get_trans(user_id)
#     upd_msg = update.message
#     msg_text = upd_msg.text
#     chat_id = update.message.chat_id
#     if msg_text == _('Create Product'):
#         title = user_data['add_product']['title']
#         prices = user_data['add_product']['prices']
#         try:
#             files = user_data['add_product']['files']
#         except KeyError:
#             msg = _('Send a photo, gif or video')
#             bot.send_message(chat_id, msg)
#             return enums.ADMIN_TXT_PRODUCT_PHOTO
#         try:
#             def_cat = ProductCategory.get(title='Default')
#         except ProductCategory.DoesNotExist:
#             product = Product.create(title=title)
#         else:
#             product = Product.create(title=title, category=def_cat)
#         for count, price in prices:
#             ProductCount.create(product=product, price=price, count=count)
#         for file_id, ftype in files:
#             file = bot.get_file(file_id)
#             file_ext = os.path.splitext(file.file_path)[1]
#             filename = '{}{}'.format(file.file_id, file_ext)
#             media_dir = config.get_media_path()
#             filename = os.path.join(media_dir, filename)
#             file.download(custom_path=filename)
#             ProductMedia.create(product=product, file_path=filename, type=ftype)
#         for courier in Courier:
#             ProductWarehouse.create(product=product, courier=courier)
#         # clear new product data
#         del user_data['add_product']
#         msg = _('New Product Created\n✅')
#         bot.send_message(chat_id, msg, reply_markup=ReplyKeyboardRemove())
#         bot.send_message(chat_id=chat_id,
#                          text=_('🏪 My Products'),
#                          reply_markup=create_bot_products_keyboard(_),
#                          parse_mode=ParseMode.MARKDOWN)
#         return enums.ADMIN_PRODUCTS
#     elif msg_text == _('❌ Cancel'):
#         del user_data['add_product']
#         bot.send_message(chat_id, _('Cancelled'), reply_markup=ReplyKeyboardRemove())
#         bot.send_message(chat_id=chat_id,
#                          text=_('🏪 My Products'),
#                          reply_markup=create_bot_products_keyboard(_),
#                          parse_mode=ParseMode.MARKDOWN)
#         return enums.ADMIN_PRODUCTS
#     files_types = ('video', 'photo', 'document')
#     file, ftype = next((getattr(upd_msg, ftype), ftype) for ftype in files_types if getattr(upd_msg, ftype, None))
#     if type(file) == list:
#         file = file[-1]
#     file = bot.get_file(file.file_id)
#     if file.file_size > 1000 * 20000:
#         err_msg = _('File size shouldn\'t be larger than 20 MB')
#         bot.send_message(chat_id, err_msg)
#     else:
#         new_type = mimetypes.guess_type(file.file_path)[0]
#         if new_type:
#             new_type = new_type.split('/')[0]
#         #if new_type in files_types + ('image',):
#         if new_type in ('image', 'video'):
#             if new_type == 'image':
#                 new_type = 'photo'
#             ftype = new_type
#             if not user_data['add_product'].get('files'):
#                 user_data['add_product']['files'] = [(file.file_id, ftype)]
#             else:
#                 user_data['add_product']['files'].append((file.file_id, ftype))
#     return enums.ADMIN_TXT_PRODUCT_PHOTO


def on_admin_cmd_delete_product(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    products = Product.filter(is_active=True)
    chat_id = update.message.chat_id
    if not products:
        msg = _('No products to delete')
        bot.send_message(text=msg, chat_id=chat_id)
        return enums.ADMIN_INIT
    user_data['products_remove'] = {'ids': [], 'page': 1}
    products = [(product.title, product.id, False) for product in products]
    products_keyboard = general_select_keyboard(_, products)
    bot.send_message(chat_id=chat_id,
                          text=_('Select a product which you want to remove'),
                          reply_markup=products_keyboard, parse_mode=ParseMode.MARKDOWN)
    return enums.ADMIN_DELETE_PRODUCT


def on_admin_cmd_bot_on(bot, update):
    global BOT_ON
    BOT_ON = True
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    update.message.reply_text(text=_('Bot switched on'))
    return enums.ADMIN_INIT


def on_admin_cmd_bot_off(bot, update):
    global BOT_ON
    BOT_ON = False
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    update.message.reply_text(text=_('Bot switched off'))
    return enums.ADMIN_INIT


def on_admin_cmd_add_courier(bot, update):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = update.message.chat_id
    couriers = Courier.select(Courier.username, Courier.id).where(Courier.is_active == False).tuples()
    if not couriers:
        msg = _('There\'s no couriers to add')
        bot.send_message(msg, chat_id)
        return enums.ADMIN_INIT
    bot.send_message(chat_id=chat_id, text=_('Select a courier to add'),
                     reply_markup=general_select_one_keyboard(_, couriers),
                     parse_mode=ParseMode.MARKDOWN)
    return enums.ADMIN_COURIER_ADD


def on_admin_cmd_delete_courier(bot, update):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id = update.message.chat_id
    couriers = Courier.select(Courier.username, Courier.id).where(Courier.is_active == True).tuples()
    if not couriers:
        msg = _('There\'s not couriers to delete')
        bot.send_message(msg, chat_id)
        return enums.ADMIN_INIT
    bot.send_message(chat_id=chat_id,
                        text=_('Select a courier to delete'),
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=general_select_one_keyboard(_, couriers)
                        )
    return enums.ADMIN_COURIER_DELETE


def on_admin_show_courier(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id, msg_id = query.message.chat_id, query.message.message_id
    action, param = query.data.split('|')
    if action == 'back':
        msg = _('🛵 Couriers')
        bot.edit_message_text(msg, chat_id, msg_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_bot_couriers_keyboard(_))
        query.answer()
        return enums.ADMIN_COURIERS
    couriers = Courier.select(Courier.username, Courier.id).where(Courier.is_active == True).tuples()
    if action == 'page':
        current_page = int(param)
        msg = _('Select a courier:')
        bot.edit_message_text(msg, chat_id, msg_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=general_select_one_keyboard(_, couriers, current_page))
        query.answer()
    elif action == 'select':
        courier = Courier.get(id=param)
        locations = CourierLocation.filter(courier=courier)
        locations = [item.location.title for item in locations]
        msg = ''
        msg += _('Name:\n`@{}`\n').format(courier.username)
        msg += _('courier ID:\n`{}`\n').format(courier.id)
        msg += _('telegram ID:\n`{}`\n').format(courier.telegram_id)
        msg += _('locations:\n{}\n').format(locations)
        bot.edit_message_text(msg, chat_id, msg_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=general_select_one_keyboard(_, couriers))
        query.answer()
    return enums.ADMIN_COURIERS_SHOW


def on_admin_add_courier(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id, message_id = query.message.chat_id, query.message.message_id
    action, param = query.data.split('|')
    if action == 'back':
        msg = _('🛵 Couriers')
        bot.edit_message_text(msg, chat_id, message_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_bot_couriers_keyboard(_))
        query.answer()
    if action == 'page':
        current_page = int(param)
        couriers = Courier.select(Courier.username, Courier.id).where(Courier.is_active == False).tuples()
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=_('Select a courier to add'),
                              reply_markup=general_select_one_keyboard(_, couriers, current_page),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_COURIER_ADD
    elif action == 'select':
        user_data['add_courier'] = {'location_ids': [], 'courier_id': param}
        text = _('Choose locations for new courier')
        locations = []
        for location in Location:
            is_picked = False
            locations.append((location.title, location.id, is_picked))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text,
                              reply_markup=create_courier_locations_keyboard(_, locations))
        query.answer()
        return enums.ADMIN_TXT_COURIER_LOCATION
    # query = update.callback_query
    # user_id = get_user_id(update)
    # _ = get_trans(user_id)
    # chat_id, message_id = query.message.chat_id, query.message.message_id
    # action = query.data
    # if action == 'back':
    #     bot.edit_message_text(_('🛵 Couriers'), chat_id, message_id, parse_mode=ParseMode.MARKDOWN,
    #                           reply_markup=create_bot_couriers_keyboard(_))
    #     query.answer()
    #     return enums.ADMIN_COURIERS
    # elif action == 'by_id':
    #     msg = _('Enter telegram ID of courier')
    #     bot.edit_message_text(msg, chat_id, message_id, parse_mode=ParseMode.MARKDOWN,
    #                           reply_markup=create_back_button(_))
    #     query.answer()
    #     return enums.ADMIN_COURIER_ADD_ID
    # elif action == 'select':
    #     couriers = Courier.select(Courier.username, Courier.id).where(Courier.is_active == False).tuples()
    #     if not couriers:
    #         msg = _('There\'s no couriers to add')
    #         query.answer(msg)
    #         return enums.ADMIN_COURIERS
    #     bot.edit_message_text(chat_id=chat_id, message_id=message_id,
    #                           text=_('Select a courier to add'),
    #                           reply_markup=general_select_one_keyboard(_, couriers),
    #                           parse_mode=ParseMode.MARKDOWN)
    #     query.answer()
    #     return enums.ADMIN_COURIER_ADD_SELECT


# def on_admin_add_courier_id(bot, update, user_data):
#     user_id = get_user_id(update)
#     _ = get_trans(user_id)
#     if update.callback_query and update.callback_query.data == 'back':
#         upd_msg = update.callback_query.message
#         bot.edit_message_text(_('➕ Add couriers'), upd_msg.chat_id, upd_msg.message_id, parse_mode=ParseMode.MARKDOWN,
#                               reply_markup=create_add_courier_keyboard(_))
#         update.callback_query.answer()
#         return enums.ADMIN_COURIER_ADD
#     upd_msg = update.message
#     courier_id = upd_msg.text
#     user_data['add_courier_by_id'] = courier_id
#     msg =
#     bot.send_message()


# def on_admin_add_courier_select(bot, update, user_data):
    # query = update.callback_query
    # user_id = get_user_id(update)
    # _ = get_trans(user_id)
    # chat_id, message_id = query.message.chat_id, query.message.message_id
    # action, param = query.data.split('|')
    # if action == 'back':
    #     bot.edit_message_text(_('➕ Add couriers'), chat_id, message_id, parse_mode=ParseMode.MARKDOWN,
    #                           reply_markup=create_add_courier_keyboard(_))
    #     query.answer()
    #     return enums.ADMIN_COURIER_ADD
    # if action == 'page':
    #     current_page = int(param)
    #     couriers = Courier.select(Courier.username, Courier.id).where(Courier.is_active == False).tuples()
    #     bot.edit_message_text(chat_id=chat_id, message_id=message_id,
    #                           text=_('Select a courier to add'),
    #                           reply_markup=general_select_one_keyboard(_, couriers, current_page),
    #                           parse_mode=ParseMode.MARKDOWN)
    #     query.answer()
    #     return enums.ADMIN_COURIER_ADD_SELECT
    # elif action == 'select':
    #     user_data['add_courier'] = {'location_ids': [], 'courier_id': param}
    #     text = _('Choose locations for new courier')
    #     locations = []
    #     for location in Location:
    #         is_picked = False
    #         locations.append((location.title, location.id, is_picked))
    #     bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text,
    #                           reply_markup=create_courier_locations_keyboard(_, locations))
    #     query.answer()
    #     return enums.ADMIN_TXT_COURIER_LOCATION


def on_admin_delete_courier(bot, update):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    chat_id, message_id = query.message.chat_id, query.message.message_id
    action, param = query.data.split('|')
    if action == 'back':
        bot.edit_message_text(chat_id=chat_id,
                              message_id=message_id,
                              text=_('🛵 Couriers'),
                              reply_markup=create_bot_couriers_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_COURIERS
    if action == 'page':
        current_page = int(param)
        couriers = Courier.select(Courier.username, Courier.id).where(Courier.is_active == False).tuples()
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=_('Select a courier to delete'),
                              reply_markup=general_select_one_keyboard(_, couriers, current_page),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_COURIER_DELETE
    elif action == 'select':
        courier = Courier.get(id=param)
        courier.is_active = False
        for warehouse in courier.courier_warehouses:
            if warehouse.count:
                warehouse.product.credits += warehouse.count
                warehouse.product.save()
                warehouse.count = 0
                warehouse.save()
        courier.save()
        text = _('Courier `{}` has been deleted').format(courier.username)
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text,
                              reply_markup=create_bot_couriers_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_COURIERS


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
        return enums.ADMIN_COURIERS

    name = update.message.text
    # initialize new courier data
    user_data['add_courier'] = {}
    user_data['add_courier']['name'] = name
    text = _('Enter courier telegram_id')
    update.message.reply_text(text=text)
    return enums.ADMIN_TXT_COURIER_ID


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

    return enums.ADMIN_TXT_COURIER_LOCATION


def on_admin_btn_courier_location(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query.data == 'location_end':
        location_ids = user_data['add_courier']['location_ids']
        courier_id = user_data['add_courier']['courier_id']
        locations = Location.filter(id__in=location_ids)
        courier = Courier.get(id=courier_id)
        courier.is_active = True
        courier.save()
        for location in locations:
            try:
                CourierLocation.get(courier=courier, location=location)
            except CourierLocation.DoesNotExist:
                CourierLocation.create(courier=courier, location=location)
            # clear new courier data
        for product in Product:
            try:
                ProductWarehouse.get(courier=courier, product=product)
            except ProductWarehouse.DoesNotExist:
                ProductWarehouse.create(courier=courier, product=product)
        del user_data['add_courier']
        bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id,
                              text=_('Courier added'),
                              reply_markup=create_bot_couriers_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_COURIERS

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
    query.answer()
    return enums.ADMIN_TXT_COURIER_LOCATION


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
        query.answer()
        return enums.ADMIN_COURIERS

    courier_id = update.message.text

    # check that courier id is valid
    try:
        courier = Courier.get(id=courier_id)
    except Courier.DoesNotExist:
        update.message.reply_text(
            text='Invalid courier id, please enter correct id')
        return enums.ADMIN_TXT_DELETE_COURIER

    courier.delete_instance()
    bot.send_message(chat_id=update.message.chat_id,
                     text=_('Courier deleted'),
                     reply_markup=create_bot_couriers_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return enums.ADMIN_COURIERS


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
        query.answer()
        return enums.ADMIN_LOCATIONS

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
        return enums.ADMIN_LOCATIONS

    except Location.DoesNotExist:
        Location.create(title=location_user_txt)

        del user_data['add_location']
        bot.send_message(chat_id=update.message.chat_id,
                         message_id=update.message.message_id,
                         text=_('new location added'),
                         reply_markup=create_bot_locations_keyboard(_),
                         parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_LOCATIONS


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
        return enums.ADMIN_LOCATIONS
    lct = update.callback_query.data
    try:
        location = Location.get(title=lct)
        location.delete_instance()
    except Location.DoesNotExist:
        update.message.reply_text(
            text='Invalid Location title, please enter correct title')
        return enums.ADMIN_TXT_DELETE_LOCATION

    query = update.callback_query
    bot.send_message(chat_id=query.message.chat_id,
                     text='Location deleted',
                     reply_markup=create_bot_locations_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return enums.ADMIN_LOCATIONS


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
        return enums.ADMIN_ORDER_OPTIONS
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
        return enums.ADMIN_LOCATIONS
    elif data == 'bot_locations_add':
        bot.edit_message_text(chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              text=_('Enter new location'),
                              parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_back_button(_)
                              ),
        query.answer()
        return enums.ADMIN_TXT_ADD_LOCATION
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
        return enums.ADMIN_TXT_DELETE_LOCATION

    return ConversationHandler.END

# additional cancel handler for admin commands
def on_admin_cancel(bot, update):
    update.message.reply_text(
        text='Admin command cancelled, to enter admin mode again type /admin',
        reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.MARKDOWN,
    )
    return enums.BOT_STATE_INIT


def on_admin_fallback(bot, update):
    update.message.reply_text(
        text='Unknown input, type /cancel to exit admin mode',
        reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.MARKDOWN,
    )
    return enums.ADMIN_INIT


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
        return enums.ADMIN_CHANNELS

    channel_type = int(update.message.text)
    if channel_type in range(1, 5):
        user_data['add_channel'] = {}
        user_data['add_channel']['channel_type'] = channel_type - 1
        update.message.reply_text(
            text='Enter channel address',
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return enums.ADMIN_CHANNELS_ADDRESS

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
    return enums.ADMIN_CHANNELS_SELECT_TYPE


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
    return enums.ADMIN_CHANNELS


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
        return enums.ADMIN_CHANNELS

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
        return enums.ADMIN_CHANNELS

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
    return enums.ADMIN_CHANNELS_REMOVE


def on_admin_edit_working_hours(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        option_back_function(
            bot, update, create_bot_settings_keyboard(_),
            'Bot settings')
        return enums.ADMIN_BOT_SETTINGS
    user_id = get_user_id(update)
    new_working_hours = update.message.text
    config_session = get_config_session()
    config_session['working_hours'] = new_working_hours
    set_config_session(config_session)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Working hours was changed',
                     reply_markup=create_bot_settings_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return enums.ADMIN_BOT_SETTINGS


def on_admin_edit_contact_info(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        option_back_function(
            bot, update, create_bot_settings_keyboard(_),
            'Bot settings')
        return enums.ADMIN_BOT_SETTINGS
    user_id = get_user_id(update)
    contact_info = update.message.text
    config_session = get_config_session()
    config_session['contact_info'] = contact_info
    set_config_session(config_session)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Contact info was changed',
                     reply_markup=create_bot_settings_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return enums.ADMIN_BOT_SETTINGS


def on_admin_add_discount(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        option_back_function(
            bot, update, create_bot_order_options_keyboard(_),
            'Order options')
        return enums.ADMIN_ORDER_OPTIONS
    # user_id = get_user_id(update)
    discount = update.message.text
    discount = parse_discount(discount)
    if discount:
        discount, discount_min = discount
        config_session = get_config_session()
        config_session['discount'] = discount
        config_session['discount_min'] = discount_min
        set_config_session(config_session)
        bot.send_message(chat_id=update.message.chat_id,
                         text=_('Discount was changed'),
                         reply_markup=create_bot_order_options_keyboard(_),
                         parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_ORDER_OPTIONS
    else:
        msg = _('Invalid format')
        msg += '\n'
        msg += _('Enter discount like:\n'
                 '50 > 500: all deals above 500$ will be -50$\n'
                 '10% > 500: all deals above 500$ will be -10%\n'
                 'Current discount: {} > {}'.format(config.get_discount(), config.get_discount_min()))
        bot.send_message(update.message.chat_id,
                         msg, reply_markup=create_back_button(_),
                         parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_ADD_DISCOUNT

def on_admin_add_delivery(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        msg = _('🚕 Delivery fee')
        upd_msg = update.callback_query.message
        bot.edit_message_text(msg, upd_msg.chat_id, upd_msg.message_id, parse_mode=ParseMode.MARKDOWN,
                              reply_markup=create_delivery_fee_keyboard(_))
        update.callback_query.answer()
        return enums.ADMIN_DELIVERY_FEE
        # option_back_function(
        #     bot, update, create_bot_order_options_keyboard(_),
        #     'Order options')
        # return enums.ADMIN_ORDER_OPTIONS
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

    bot.send_message(update.message.chat_id,
                     _('Delivery fee was changed'),
                     reply_markup=create_delivery_fee_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return enums.ADMIN_DELIVERY_FEE

    # bot.send_message(chat_id=update.message.chat_id,
    #                  text='Delivery fee was changed',
    #                  reply_markup=create_bot_order_options_keyboard(_),
    #                  parse_mode=ParseMode.MARKDOWN)
    # return enums.ADMIN_ORDER_OPTIONS


def on_admin_bot_on_off(bot, update, user_data):
    query = update.callback_query
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if query.data == 'back':
        option_back_function(
            bot, update, create_bot_settings_keyboard(_),
            'Bot settings')
        return enums.ADMIN_BOT_SETTINGS
    status = query.data == 'on'
    config_session = get_config_session()
    config_session['bot_on_off'] = status
    set_config_session(config_session)
    msg = _('Bot status was changed')
    bot.edit_message_text(msg, query.message.chat_id, query.message.message_id,
                          reply_markup=create_bot_settings_keyboard(_),
                          parse_mode=ParseMode.MARKDOWN)
    return enums.ADMIN_BOT_SETTINGS


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
        return enums.ADMIN_ORDER_OPTIONS
    # user_id = get_user_id(update)
    welcome_message = update.message.text
    config_session = get_config_session()
    config_session['welcome_text'] = welcome_message
    set_config_session(config_session)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Welcome message was changed',
                     reply_markup=create_bot_order_options_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return enums.ADMIN_ORDER_OPTIONS


def on_admin_edit_order_message(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        option_back_function(
            bot, update, create_bot_order_options_keyboard(_),
            'Order options')
        return enums.ADMIN_ORDER_OPTIONS
    # user_id = get_user_id(update)
    order_message = update.message.text
    config_session = get_config_session()
    config_session['order_text'] = order_message
    set_config_session(config_session)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Order message was changed',
                     reply_markup=create_bot_order_options_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return enums.ADMIN_ORDER_OPTIONS


def on_admin_edit_final_message(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        option_back_function(
            bot, update, create_bot_order_options_keyboard(_),
            'Order options')
        return enums.ADMIN_ORDER_OPTIONS
    final_message = update.message.text
    config_session = get_config_session()
    config_session['order_complete_text'] = final_message
    set_config_session(config_session)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Final message was changed',
                     reply_markup=create_bot_order_options_keyboard(_),
                     parse_mode=ParseMode.MARKDOWN)
    return enums.ADMIN_ORDER_OPTIONS


def on_admin_edit_identification_stages(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    query = update.callback_query
    chat_id, msg_id = query.message.chat_id, query.message.message_id
    action, data = query.data.split('|')
    if action == 'back':
        msg = _('💳 Order options')
        bot.edit_message_text(msg, chat_id, msg_id,
                         reply_markup=create_bot_order_options_keyboard(_),
                         parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_ORDER_OPTIONS
    if action in ('toggle', 'vip_toggle', 'delete'):
        question = IdentificationStage.get(id=data)
        if action == 'toggle':
            question.active = not question.active
            question.save()
        elif action == 'vip_toggle':
            question.vip_required = not question.vip_required
            question.save()
        elif action == 'delete':
            question.delete_instance()
        questions = IdentificationStage.select(IdentificationStage.id, IdentificationStage.active, IdentificationStage.vip_required).tuples()
        msg = _('👨 Edit identification process:')
        bot.edit_message_text(msg, chat_id, msg_id, reply_markup=create_edit_identification_keyboard(_, questions),
                              parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_EDIT_IDENTIFICATION_STAGES
    if action == 'add':
        user_data['admin_edit_identification'] = {'new': True}
    elif action == 'edit':
        user_data['admin_edit_identification'] = {'new': False, 'id': data}
    msg = _('Select type of identification question')
    bot.edit_message_text(msg, chat_id, msg_id, reply_markup=create_edit_identification_type_keyboard(_),
                          parse_mode=ParseMode.MARKDOWN)
    return enums.ADMIN_EDIT_IDENTIFICATION_QUESTION_TYPE


def on_admin_edit_identification_question_type(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    query = update.callback_query
    chat_id, msg_id = query.message.chat_id, query.message.message_id
    action = query.data
    if action == 'back':
        questions = IdentificationStage.select(IdentificationStage.id, IdentificationStage.active, IdentificationStage.vip_required).tuples()
        msg = _('👨 Edit identification process:')
        bot.edit_message_text(msg, chat_id, msg_id, reply_markup=create_edit_identification_keyboard(_, questions),
                              parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_EDIT_IDENTIFICATION_STAGES
    #new_q = user_data['admin_edit_identification']['new']
    if action in ('photo', 'text'):
        edit_options = user_data['admin_edit_identification']
        #user_data['admin_edit_identification']['type'] = action
        edit_options['type'] = action
        msg = _('Enter new question or variants to choose randomly, e.g.:\n'
                '_Send identification photo_ ✌️\n'
                '_Send identification photo_ 🖖')
        if not edit_options['new']:
            questions = IdentificationStage.get(id=edit_options['id']).identification_questions
            q_msg = ''
            for q in questions:
                q_msg += '_{}_\n'.format(q.content)
            msg = _('Current questions:\n'
                    '{}\n{}').format(q_msg, msg)
        bot.edit_message_text(msg, chat_id, msg_id, reply_markup=create_back_button(_),
                              parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_EDIT_IDENTIFICATION_QUESTION


def on_admin_edit_identification_question(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        upd_msg = update.callback_query.message
        msg = _('Select type of identification question')
        bot.edit_message_text(msg, upd_msg.chat_id, upd_msg.message_id, reply_markup=create_edit_identification_type_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        return enums.ADMIN_EDIT_IDENTIFICATION_QUESTION_TYPE

    upd_msg = update.message
    edit_options = user_data['admin_edit_identification']
    msg_text = upd_msg.text
    if edit_options['new']:
        stage = IdentificationStage.create(type=edit_options['type'])
        for q_text in msg_text.split('\n'):
            if q_text:
                IdentificationQuestion.create(content=q_text, stage=stage)
        msg = _('Identification question has been created')
    else:
        stage = IdentificationStage.get(id=edit_options['id'])
        stage.type = edit_options['type']
        stage.save()
        for q in stage.identification_questions:
            q.delete_instance()
        for q_text in msg_text.split('\n'):
            if q_text:
                IdentificationQuestion.create(content=q_text, stage=stage)
        msg = _('Identification question has been changed')
    questions = IdentificationStage.select(IdentificationStage.id, IdentificationStage.active, IdentificationStage.vip_required).tuples()
    bot.send_message(upd_msg.chat_id, msg, reply_markup=create_edit_identification_keyboard(_, questions),
                          parse_mode=ParseMode.MARKDOWN)
    return enums.ADMIN_EDIT_IDENTIFICATION_STAGES


# def on_admin_edit_identification_stages(bot, update, user_data):
#     user_id = get_user_id(update)
#     _ = get_trans(user_id)
#     query = update.callback_query
#     chat_id = query.message.chat_id
#     message_id = query.message.message_id
    # config_session = get_config_session()
    # stage_one, stage_two = user_data['edit_identification_stages']
    # if query.data == 'save':
    #     config_session['identification_required'] = stage_one
    #     config_session['identification_stage2_required'] = stage_two
    #     set_config_session(config_session)
    #     old_question = config.get_identification_stage2_question()
    #     msg = _('Identification question: {}\n'
    #             'Enter new identification question:').format(old_question)
    #     bot.edit_message_text(msg, chat_id, message_id, reply_markup=create_back_button(_),
    #                           parse_mode=ParseMode.MARKDOWN)
    #     query.answer()
    #     return enums.ADMIN_EDIT_IDENTIFICATION_QUESTION
    # if query.data == 'stage_one':
    #     stage_one = not stage_one
    # elif query.data == 'stage_two':
    #     stage_two = not stage_two
    # user_data['edit_identification_stages'] = (stage_one, stage_two)
    # msg = _('👨 Edit identification stages:')
    # bot.edit_message_text(msg, chat_id, message_id, parse_mode=ParseMode.MARKDOWN,
    #                       reply_markup=create_edit_identification_keyboard(_, (stage_one, stage_two)))
    # query.answer()
    # return enums.ADMIN_EDIT_IDENTIFICATION_STAGES

# def on_admin_edit_identification_question(bot, update):
#     user_id = get_user_id(update)
#     _ = get_trans(user_id)
#     if update.callback_query and update.callback_query.data == 'back':
#         option_back_function(
#             bot, update, create_bot_order_options_keyboard(_),
#             'Order options')
#         return enums.ADMIN_ORDER_OPTIONS
#     config_session = get_config_session()
#     config_session['identification_stage2_question'] = update.message.text
#     set_config_session(config_session)
#     msg = _('Identification was changed')
#     bot.send_message(update.message.chat_id, msg,
#                      reply_markup=create_bot_order_options_keyboard(_),
#                      parse_mode=ParseMode.MARKDOWN)
#     return enums.ADMIN_ORDER_OPTIONS

def on_admin_edit_restriction(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    query = update.callback_query
    chat_id, msg_id = query.message.chat_id, query.message.message_id
    callback_data = query.data
    first, second = user_data['edit_restricted_area']
    if callback_data == 'save':
        config_session = get_config_session()
        config_session['only_for_customers'] = first
        config_session['vip_customers'] = second
        set_config_session(config_session)
        msg = _('Restriction options are changed')
        bot.edit_message_text(msg, chat_id, msg_id,
                              reply_markup=create_bot_order_options_keyboard(_),
                              parse_mode=ParseMode.MARKDOWN)
        query.answer()
        return enums.ADMIN_ORDER_OPTIONS
    if callback_data == 'first':
        first = not first
    elif callback_data == 'second':
        second = not second
    user_data['edit_restricted_area'] = (first, second)
    msg = _('🔥 Edit restricted area:')
    bot.edit_message_text(msg, chat_id, msg_id, parse_mode=ParseMode.MARKDOWN,
                          reply_markup=create_edit_restriction_keyboard(_, (first, second)))
    query.answer()
    return enums.ADMIN_EDIT_RESTRICTION


def on_admin_add_ban_list(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        option_back_function(
            bot, update, create_ban_list_keyboard(_),
            'Ban list')
        return enums.ADMIN_BAN_LIST

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
    return enums.ADMIN_BAN_LIST


def on_admin_remove_ban_list(bot, update, user_data):
    user_id = get_user_id(update)
    _ = get_trans(user_id)
    if update.callback_query and update.callback_query.data == 'back':
        option_back_function(
            bot, update, create_ban_list_keyboard(_),
            'Ban list')
        return enums.ADMIN_BAN_LIST

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
    return enums.ADMIN_BAN_LIST
