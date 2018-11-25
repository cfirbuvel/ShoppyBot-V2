import configparser
import redis
import json
import gettext
import os

from telegram import ParseMode, TelegramError

from .models import ProductCount, Product, User, OrderItem, Courier, Order
# from .keyboards import create_service_notice_keyboard
from .enums import logger


class JsonRedis(redis.StrictRedis):

    def json_get(self, name):
        value = self.get(name)
        if value:
            value = json.loads(value.decode("utf-8"))
        return value

    # @set_locale
    def json_set(self, name, value):
        value = json.dumps(value)
        return self.set(name, value)


class ConfigHelper:
    def __init__(self, cfgfilename='shoppybot.conf'):
        self.config = configparser.ConfigParser(
            defaults={'api_token': None, 'reviews_channel': None,
                      'service_channel': None, 'customers_channel': None,
                      'vip_customers_channel': None, 'couriers_channel': None,
                      'channels_language': 'iw', 'media_path': './media',
                      'welcome_text': 'Welcome text not configured yet',
                      'order_text': 'Order text not configured yet',
                      'order_complete_text': 'Order text not configured yet',
                      'working_hours': 'Working hours not configured yet',
                      'contact_info': 'Contact info not configured yet',
                      'phone_number_required': True,
                      'identification_required': True,
                      'identification_stage2_required': False,
                      'identification_stage2_question': None,
                      'has_courier_option': True,
                      'only_for_customers': False, 'delivery_fee': 0,
                      'delivery_fee_for_vip': False, 'discount': 0,
                      'discount_min': 0})
        self.config.read(cfgfilename, encoding='utf-8')
        self.section = 'Settings'

    def get_api_token(self):
        value = self.config.get(self.section, 'api_token')
        return value.strip()

    def get_reviews_channel(self):
        value = get_config_session().get('reviews_channel')
        if value is None:
            value = self.config.get(self.section, 'reviews_channel')
        return value.strip()

    def get_service_channel(self):
        value = get_config_session().get('service_channel')
        if value is None:
            value = self.config.get(self.section, 'service_channel')
        return value.strip()

    def get_customers_channel(self):
        value = get_config_session().get('customers_channel')
        if value is None:
            value = self.config.get(self.section, 'customers_channel')
        return value.strip()

    def get_vip_customers_channel(self):
        value = get_config_session().get('vip_customers_channel')
        if value is None:
            value = self.config.get(self.section, 'vip_customers_channel')
        return value.strip()

    def get_couriers_channel(self):
        value = get_config_session().get('couriers_channel')
        if value is None:
            value = self.config.get(self.section, 'couriers_channel')
        return value.strip()

    def get_channels_language(self):
        value = get_config_session().get('channels_language')
        if value is None:
            value = self.config.get(self.section, 'channels_language')
        return value.strip()

    def get_media_path(self):
        value = self.config.get(self.section, 'media_path')
        value = value.strip()
        value = os.path.abspath(value)
        if not os.path.isdir(value):
            os.mkdir(value)
        return value

    def get_welcome_text(self):
        value = get_config_session().get('welcome_text')
        if value is None:
            value = self.config.get(self.section, 'welcome_text')
        return value.strip()

    def get_order_text(self):
        value = get_config_session().get('order_text')
        if value is None:
            value = self.config.get(self.section, 'order_text')
        return value.strip()

    def get_order_complete_text(self):
        value = get_config_session().get('order_complete_text')
        if value is None:
            value = self.config.get(self.section, 'order_complete_text')
        return value.strip()

    def get_working_hours(self):
        value = get_config_session().get('working_hours')
        if value is None:
            value = self.config.get(self.section, 'working_hours')
        return value.strip()

    def get_contact_info(self):
        value = get_config_session().get('contact_info')
        if value is None:
            value = self.config.get(self.section, 'contact_info')
        return value.strip()

    def get_phone_number_required(self):
        value = get_config_session().get('phone_number_required')
        if value is None:
            value = self.config.getboolean(
                self.section, 'phone_number_required')
        else:
            value = value == '1' or value == 'yes'
        return value

    def get_identification_required(self):
        value = get_config_session().get('identification_required')
        if value is None:
            value = self.config.getboolean(self.section,
                                           'identification_required')
        # else:
        #     value = value == '1' or value == 'yes'
        return value

    def get_identification_stage2_required(self):
        value = get_config_session().get('identification_stage2_required')
        if value is None:
            value = self.config.getboolean(self.section,
                                           'identification_stage2_required')
        # else:
        #     value = value == '1' or value == 'yes'
        return value

    def get_identification_stage2_question(self):
        value = get_config_session().get('identification_stage2_question')
        if value is None:
            value = self.config.get(self.section,
                                    'identification_stage2_question')
        return value

    def get_only_for_customers(self):
        value = get_config_session().get('only_for_customers')
        if value is None:
            value = self.config.getboolean(self.section, 'only_for_customers')
        # else:
        #     value = value == '1' or value == 'yes'
        return value

    def get_has_courier_option(self):
        value = get_config_session().get('has_courier_option')
        if value is None:
            value = self.config.getboolean(self.section, 'has_courier_option')
        else:
            value = value == '1' or value == 'yes'
        return value

    def get_vip_customers(self):
        value = get_config_session().get('vip_customers')
        if value is None:
            value = self.config.getboolean(self.section, 'vip_customers')
        # else:
        #     value = value == '1' or value == 'yes' or value is True
        return value

    def get_delivery_fee_for_vip(self):
        value = get_config_session().get('delivery_fee_for_vip')
        if value is None:
            value = self.config.getboolean(self.section, 'delivery_fee_for_vip')
        return value

    def get_delivery_fee(self):
        value = get_config_session().get('delivery_fee')
        if value is None:
            value = self.config.get(self.section, 'delivery_fee')
        return int(value)

    def get_delivery_min(self):
        value = get_config_session().get('delivery_min')
        if value is None:
            value = self.config.get(self.section, 'delivery_min')
        return int(value)

    def get_bot_on_off(self):
        value = get_config_session().get('bot_on_off')
        if value is None:
            value = self.config.getboolean(self.section, 'bot_on_off')
        else:
            value = value == '1' or value == 'yes' or value is True
        return value

    def get_discount(self):
        value = get_config_session().get('discount')
        if value is None:
            value = self.config.get(self.section, 'discount')
        return value

    def get_discount_min(self):
        value = get_config_session().get('discount_min')
        if value is None:
            value = self.config.get(self.section, 'discount_min')
            try:
                value = int(value)
            except ValueError:
                value = 0
        return value

    def get_banned_users(self):
        value = get_config_session().get('banned')
        if value is None:
            value = self.config.get(self.section, 'banned')
        values = value
        if not value:
            values = []
        elif isinstance(value, str):
            values = value.split(', ')
        return values


class CartHelper:
    def __init__(self):
        pass

    def check_cart(self, user_data):
        # check that cart is still here in case we've restarted
        if 'cart' not in user_data:
            user_data['cart'] = {}
        return user_data['cart']

    def add(self, user_data, product_id):
        cart = self.check_cart(user_data)
        product_id = str(product_id)
        prices = ProductCount.select().where(
            ProductCount.product == product_id).order_by(
            ProductCount.count.asc())
        counts = [x.count for x in prices]
        min_count = counts[0]

        if product_id not in cart:
            # add minimum product count (usually 1)
            cart[product_id] = min_count
        else:
            # add more
            current_count = cart[product_id]
            current_count_index = counts.index(current_count)
            # iterate through possible product counts for next price
            next_count_index = (current_count_index + 1) % len(counts)
            cart[product_id] = counts[next_count_index]
        user_data['cart'] = cart

        return user_data

    def remove(self, user_data, product_id):
        cart = self.check_cart(user_data)
        product_id = str(product_id)

        prices = ProductCount.select().where(
            ProductCount.product == product_id).order_by(
            ProductCount.count.asc())
        counts = [x.count for x in prices]

        if product_id in cart:
            current_count = cart[product_id]
            current_count_index = counts.index(current_count)

            if current_count_index == 0:
                del cart[product_id]
            else:
                next_count_index = current_count_index - 1
                cart[product_id] = counts[next_count_index]
        user_data['cart'] = cart

        return user_data

    def get_products_info(self, user_data, for_order=False):
        product_ids = self.get_product_ids(user_data)
        product_info = []
        for product_id in product_ids:
            info = self.get_product_info(user_data, product_id, for_order)
            if info:
                product_info.append(info)

        return product_info

    def get_product_info(self, user_data, product_id, for_order=False):
        result = None
        try:
            product_title = Product.get(id=product_id).title
        except Product.DoesNotExist:
            return result
        product_count = self.get_product_count(user_data, product_id)
        product_price = ProductCount.get(
            product_id=product_id, count=product_count).price
        if for_order:
            result = product_id, product_count, product_price
        else:
            result = product_title, product_count, product_price
        return result

    def product_full_info(self, user_data, product_id):
        try:
            product_title = Product.get(id=product_id).title
        except Product.DoesNotExist:
            return '', []
        rows = ProductCount.select(
            ProductCount.count, ProductCount.price).where(
            ProductCount.product == product_id).tuples()
        return product_title, rows

    def get_product_ids(self, user_data):
        cart = self.check_cart(user_data)

        return cart.keys()

    def get_product_count(self, user_data, product_id):
        cart = self.check_cart(user_data)
        product_id = str(product_id)

        if product_id not in cart:
            return 0
        else:
            return cart[product_id]

    def is_full(self, user_data):
        cart = self.check_cart(user_data)

        return len(cart) > 0

    def get_product_subtotal(self, user_data, product_id):
        count = self.get_product_count(user_data, product_id)

        rows = ProductCount.filter(product_id=product_id)
        min_price = 0
        for row in rows:
            price, product_count = row.price, row.count
            if count >= product_count:
                min_price = price

        return min_price

    def get_cart_total(self, user_data):
        cart = self.check_cart(user_data)

        total = 0
        for product_id in cart:
            subtotal = self.get_product_subtotal(user_data, product_id)
            total += subtotal
        return total

    def fill_order(self, user_data, order):
        products = self.get_products_info(user_data, for_order=True)
        for p_id, p_count, p_price in products:
            OrderItem.create(order=order, product_id=p_id, count=p_count,
                             total_price=p_price)


cart = CartHelper()
config = ConfigHelper(cfgfilename='shoppybot.conf')


def parse_discount(discount_str):
    discount_list = [v.strip() for v in discount_str.split('>')]
    if len(discount_list) == 2:
        discount, discount_min = discount_list
        try:
            discount_num = int(discount.split('%')[0].strip())
            discount_min = int(discount_min)
        except ValueError:
            pass
        else:
            # if discount_num > 0 and discount_min > 0:
            return discount, discount_min


def calculate_discount_total(discount, total):
    if discount.endswith('%'):
        discount = discount.replace('%', '').strip()
        discount = round(total / 100 * int(discount))
    return total - int(discount)


def is_vip_customer(bot, user_id):
    if not config.get_vip_customers():
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


# we assume people in service channel can administrate the bot


def get_user_session(user_id):
    user_session = session_client.json_get(user_id)
    updated = False

    if not user_session:
        try:
            user = User.get(telegram_id=user_id)
        except User.DoesNotExist:
            user = Courier.get(telegram_id=user_id)
        session_client.json_set(user_id, {'locale': user.locale})
        user_session = session_client.json_get(user_id)

    if not user_session.get('cart'):
        user_session["cart"] = {}
        updated = True

    if not user_session.get('shipping'):
        user_session["shipping"] = {}
        updated = True

    if not user_session.get('courier'):
        user_session['courier'] = {}
        updated = True

    if updated:
        session_client.json_set(user_id, user_session)

    return user_session


def get_username(update):
    if update.callback_query is not None:
        username = update.callback_query.from_user.username
    else:
        username = update.message.from_user.username

    return username


def get_locale(update):
    if update.callback_query is not None:
        language = update.callback_query.from_user.language_code
    else:
        language = update.message.from_user.language_code
    if language is None:
        language = 'en-US'

    return language[:2]


def get_user_id(update):
    if update.callback_query is not None:
        user_id = update.callback_query.from_user.id
    else:
        user_id = update.message.from_user.id

    return user_id


def get_trans(user_id):
    user_data = get_user_session(user_id)
    locale = user_data.get('locale')
    return gettext.gettext if locale == 'en' else cat.gettext


def get_channel_trans():
    locale = config.get_channels_language()
    return gettext.gettext if locale == 'en' else cat.gettext


def get_config_session():
    session = session_client.json_get('git_config')

    if not session:
        session_client.json_set('git_config', {})
        session = session_client.json_get('git_config')

    return session


def set_config_session(session):
    session_client.json_set('git_config', session)

# def get_user_model(update):
#

session_client = JsonRedis(host='localhost', port=6379, db=0)
cat = gettext.GNUTranslations(open('he.mo', 'rb'))
