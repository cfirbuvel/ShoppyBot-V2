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
 BOT_STATE_CHECKOUT_IDENTIFY_STAGE1,
 BOT_STATE_CHECKOUT_IDENTIFY_STAGE2,
 BOT_STATE_ORDER_CONFIRMATION,
 BOT_LANGUAGE_CHANGE,

 ADMIN_INIT,
 ADMIN_TXT_PRODUCT_TITLE,
 ADMIN_TXT_PRODUCT_PRICES,
 ADMIN_TXT_PRODUCT_PHOTO,
 ADMIN_TXT_DELETE_PRODUCT,
 ADMIN_TXT_COURIER_NAME,
 ADMIN_TXT_COURIER_ID,
 ADMIN_TXT_COURIER_LOCATION,
 ADMIN_TXT_DELETE_COURIER,
 ADMIN_MENU,
 ADMIN_STATISTICS,
 ADMIN_COURIERS,
 ADMIN_CHANNELS,
 ADMIN_CHANNELS_SELECT_TYPE,
 ADMIN_CHANNELS_ADDRESS,
 ADMIN_CHANNELS_REMOVE,
 ADMIN_EDIT_WORKING_HOURS,
 ADMIN_EDIT_CONTACT_INFO,
 ADMIN_BOT_ON_OFF,
 ADMIN_BOT_SETTINGS,
 ADMIN_RESET_OPTIONS,
 ADMIN_ORDER_OPTIONS,
 ADMIN_ADD_DISCOUNT,
 ADMIN_ADD_DELIVERY_FEE,
 ADMIN_EDIT_WELCOME_MESSAGE,
 ADMIN_EDIT_ORDER_DETAILS,
 ADMIN_EDIT_FINAL_MESSAGE,
 ADMIN_EDIT_IDENTIFICATION,
 ADMIN_EDIT_RESTRICTION,
 ADMIN_BAN_LIST,
 ADMIN_BAN_LIST_VIEW,
 ADMIN_BAN_LIST_REMOVE,
 ADMIN_BAN_LIST_ADD,
 ADMIN_SET_WELCOME_MESSAGE,) = range(46)