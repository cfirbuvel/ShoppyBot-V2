import gettext
import logging
import sys
import random

_ = gettext.gettext

logging.basicConfig(stream=sys.stderr, format='%(asctime)s %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def create_photo_question():
    q1 = _('👍')
    q2 = _('🤘')
    q3 = _('✌️')
    q4 = _('👌')
    return random.choice([q1, q2, q3, q4])


(BOT_STATE_INIT,
 BOT_STATE_CHECKOUT_SHIPPING,
 BOT_STATE_CHECKOUT_LOCATION,
 BOT_STATE_CHECKOUT_LOCATION_PICKUP,
 BOT_STATE_CHECKOUT_LOCATION_DELIVERY,
 BOT_STATE_CHECKOUT_TIME,
 BOT_STATE_CHECKOUT_PHONE_NUMBER_TEXT,
 BOT_STATE_CHECKOUT_TIME_TEXT,
 BOT_STATE_CHECKOUT_IDENTIFY,
 BOT_STATE_CHECKOUT_IDENTIFY_STAGE1,
 BOT_STATE_CHECKOUT_IDENTIFY_STAGE2,
 BOT_STATE_ORDER_CONFIRMATION,
 BOT_LANGUAGE_CHANGE,
 BOT_STATE_MY_ORDERS,
 BOT_STATE_MY_ORDER_SELECT,
 BOT_STATE_MY_ORDER_DATE,
 BOT_STATE_MY_LAST_ORDER,
 BOT_STATE_MY_LAST_ORDER_CANCEL,
 PRODUCT_CATEGORIES,

 ADMIN_INIT,
 ADMIN_TXT_PRODUCT_TITLE,
 ADMIN_TXT_PRODUCT_PRICES,
 ADMIN_TXT_PRODUCT_PHOTO,
 # ADMIN_TXT_DELETE_PRODUCT,
 ADMIN_TXT_COURIER_NAME,
 ADMIN_TXT_COURIER_ID,
 ADMIN_TXT_COURIER_LOCATION,
 ADMIN_TXT_DELETE_COURIER,
 ADMIN_TXT_ADD_LOCATION,
 ADMIN_TXT_DELETE_LOCATION,
 ADMIN_MENU,
 ADMIN_STATISTICS,
 ADMIN_COURIERS,
 ADMIN_COURIERS_SHOW,
 ADMIN_CHANNELS,
 ADMIN_LOCATIONS,
 ADMIN_CHANNELS_SELECT_TYPE,
 ADMIN_CHANNELS_ADDRESS,
 ADMIN_CHANNELS_REMOVE,
 ADMIN_CHANNELS_LANGUAGE,
 ADMIN_EDIT_WORKING_HOURS,
 ADMIN_EDIT_CONTACT_INFO,
 ADMIN_BOT_ON_OFF,
 ADMIN_BOT_SETTINGS,
 ADMIN_RESET_OPTIONS,
 ADMIN_ORDER_OPTIONS,
 ADMIN_ADD_DISCOUNT,
 ADMIN_DELIVERY_FEE,
 ADMIN_ADD_DELIVERY_FEE,
 ADMIN_DELIVERY_FEE_VIP,
 ADMIN_EDIT_WELCOME_MESSAGE,
 ADMIN_EDIT_ORDER_DETAILS,
 ADMIN_EDIT_FINAL_MESSAGE,
 ADMIN_EDIT_IDENTIFICATION_STAGES,
 ADMIN_EDIT_IDENTIFICATION_QUESTION_TYPE,
 ADMIN_EDIT_IDENTIFICATION_QUESTION,
 ADMIN_EDIT_RESTRICTION,
 ADMIN_BAN_LIST,
 ADMIN_BAN_LIST_VIEW,
 ADMIN_BAN_LIST_REMOVE,
 ADMIN_BAN_LIST_ADD,
 ADMIN_SET_WELCOME_MESSAGE,
 ADMIN_PRODUCTS,
 ADMIN_PRODUCTS_SHOW,
 ADMIN_PRODUCT_ADD,
 ADMIN_PRODUCT_LAST_ADD,
 ADMIN_PRODUCT_EDIT_SELECT,
 ADMIN_PRODUCT_EDIT,
 ADMIN_PRODUCT_EDIT_TITLE,
 ADMIN_PRODUCT_EDIT_PRICES,
 ADMIN_PRODUCT_EDIT_MEDIA,
 ADMIN_DELETE_PRODUCT,
 ADMIN_COURIER_ADD,
 ADMIN_COURIER_DELETE,
 ADMIN_STATISTICS_GENERAL,
 ADMIN_STATISTICS_COURIERS,
 ADMIN_STATISTICS_COURIERS_DATE,
 ADMIN_STATISTICS_LOCATIONS,
 ADMIN_STATISTICS_LOCATIONS_DATE,
 ADMIN_STATISTICS_USER,
 ADMIN_STATISTICS_USER_DATE,
 ADMIN_WAREHOUSE,
 ADMIN_WAREHOUSE_PRODUCT,
 ADMIN_WAREHOUSE_PRODUCT_CREDITS,
 ADMIN_WAREHOUSE_COURIER,
 ADMIN_WAREHOUSE_COURIER_CREDITS,
 ADMIN_CATEGORIES,
 ADMIN_CATEGORY_ADD,
 ADMIN_CATEGORY_PRODUCTS_SELECT,
 ADMIN_CATEGORY_REMOVE_SELECT,
 ADMIN_CATEGORY_PRODUCTS_ADD,
 ADMIN_ORDERS,
 ADMIN_ORDERS_PENDING_SELECT,
 ADMIN_ORDERS_FINISHED_DATE,
 ADMIN_ORDERS_FINISHED_SELECT,

 COURIER_STATE_INIT,
 COURIER_STATE_CONFIRM_ORDER,
 COURIER_STATE_CONFIRM_REPORT,
 COURIER_STATE_REPORT_REASON,
 COURIER_STATE_PING,
 COURIER_STATE_PING_SOON) = range(100)
# range(49) without courier states
