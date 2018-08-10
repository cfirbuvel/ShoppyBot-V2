#! /usr/bin/env python3

from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, Filters, MessageHandler, Updater

from src.admin import on_start_admin, on_admin_select_channel_type, on_admin_add_channel_address, on_admin_cancel, \
    on_admin_remove_channel, on_admin_remove_ban_list, on_admin_add_ban_list, on_admin_edit_working_hours, \
    on_admin_edit_contact_info, on_admin_bot_on_off, on_admin_order_options, on_admin_add_discount, \
    on_admin_edit_identification, on_admin_edit_restriction, on_admin_add_delivery, on_admin_edit_welcome_message, \
    on_admin_edit_order_message, on_admin_edit_final_message, on_admin_cmd_add_product, on_admin_cmd_delete_product, \
    on_admin_cmd_add_courier, on_admin_txt_courier_name, on_admin_cmd_bot_on, on_admin_cmd_bot_off, on_admin_fallback, \
    on_admin_txt_product_title, on_admin_txt_product_prices, on_admin_txt_product_photo, on_admin_txt_delete_product, \
    on_admin_cmd_delete_courier, on_admin_txt_courier_id, on_admin_btn_courier_location, on_admin_txt_delete_courier, \
    on_admin_txt_delete_location, on_admin_txt_location, on_admin_locations
from src.enums import BOT_STATE_CHECKOUT_SHIPPING, BOT_STATE_CHECKOUT_LOCATION_PICKUP, \
    BOT_STATE_CHECKOUT_LOCATION_DELIVERY, BOT_STATE_CHECKOUT_TIME, BOT_STATE_CHECKOUT_TIME_TEXT, \
    BOT_STATE_CHECKOUT_IDENTIFY_STAGE1, BOT_STATE_CHECKOUT_IDENTIFY_STAGE2, \
    BOT_STATE_ORDER_CONFIRMATION, BOT_STATE_INIT, ADMIN_BOT_SETTINGS, ADMIN_ORDER_OPTIONS, \
    ADMIN_TXT_COURIER_NAME, ADMIN_TXT_DELETE_COURIER, ADMIN_CHANNELS, ADMIN_CHANNELS_SELECT_TYPE, \
    ADMIN_CHANNELS_REMOVE, ADMIN_BAN_LIST, BOT_STATE_CHECKOUT_PHONE_NUMBER_TEXT, \
    BOT_LANGUAGE_CHANGE, ADMIN_MENU, ADMIN_STATISTICS, ADMIN_COURIERS, ADMIN_EDIT_WORKING_HOURS, \
    ADMIN_EDIT_CONTACT_INFO, ADMIN_BOT_ON_OFF, ADMIN_BAN_LIST_REMOVE, ADMIN_BAN_LIST_ADD, ADMIN_CHANNELS_ADDRESS, \
    ADMIN_ADD_DISCOUNT, ADMIN_EDIT_IDENTIFICATION, ADMIN_EDIT_RESTRICTION, ADMIN_ADD_DELIVERY_FEE, \
    ADMIN_EDIT_WELCOME_MESSAGE, ADMIN_EDIT_ORDER_DETAILS, ADMIN_TXT_COURIER_ID, ADMIN_INIT, ADMIN_TXT_PRODUCT_TITLE, \
    ADMIN_TXT_PRODUCT_PRICES, ADMIN_TXT_PRODUCT_PHOTO, ADMIN_TXT_DELETE_PRODUCT, ADMIN_EDIT_FINAL_MESSAGE, \
    ADMIN_TXT_COURIER_LOCATION, ADMIN_TXT_DELETE_LOCATION, ADMIN_TXT_ADD_LOCATION, ADMIN_LOCATIONS
from src.handlers import on_start, on_menu, on_error
from src.helpers import resend_responsibility_keyboard, make_confirm, make_unconfirm, config, get_user_id, \
    get_user_session

from src.models import create_tables

from src.triggers import checkout_fallback_command_handler, on_shipping_method, on_shipping_pickup_location, \
    on_shipping_delivery_address, on_checkout_time, on_shipping_time_text, on_phone_number_text, \
    on_shipping_identify_photo, on_statistics_menu, on_confirm_order, on_bot_language_change, on_settings_menu, \
    on_shipping_identify_stage2, on_bot_settings_menu, on_admin_couriers, on_admin_channels, on_admin_ban_list, \
    on_cancel, send_welcome_message, service_channel_courier_query_handler, on_service_send_order_to_courier, \
    service_channel_sendto_courier_handler


# will be called when conversation context is lost (e.g. bot is restarted)
# and the user clicks menu buttons


def fallback_query_handler(bot, update, user_data):
    user_id = get_user_id(update)
    user_data = get_user_session(user_id)
    return on_menu(bot, update, user_data)


def main():
    user_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', on_start, pass_user_data=True),
                      CommandHandler('admin', on_start_admin),
                      CallbackQueryHandler(fallback_query_handler,
                                           pattern='^(menu|product)',
                                           pass_user_data=True)],
        states={
            BOT_STATE_INIT: [
                CommandHandler('start', on_start, pass_user_data=True),
                CommandHandler('admin', on_start_admin),
                CallbackQueryHandler(
                    on_menu, pattern='^(menu|product)', pass_user_data=True)
            ],
            BOT_STATE_CHECKOUT_SHIPPING: [
                CallbackQueryHandler(checkout_fallback_command_handler,
                                     pass_user_data=True),
                MessageHandler(Filters.text, on_shipping_method,
                               pass_user_data=True),
            ],
            BOT_STATE_CHECKOUT_LOCATION_PICKUP: [
                CallbackQueryHandler(checkout_fallback_command_handler,
                                     pass_user_data=True),
                MessageHandler(Filters.text, on_shipping_pickup_location,
                               pass_user_data=True),
            ],
            BOT_STATE_CHECKOUT_LOCATION_DELIVERY: [
                CallbackQueryHandler(checkout_fallback_command_handler,
                                     pass_user_data=True),
                MessageHandler(Filters.text or Filters.location,
                               on_shipping_delivery_address,
                               pass_user_data=True),
            ],
            BOT_STATE_CHECKOUT_TIME: [
                CallbackQueryHandler(checkout_fallback_command_handler,
                                     pass_user_data=True),
                MessageHandler(Filters.text, on_checkout_time,
                               pass_user_data=True),
            ],
            BOT_STATE_CHECKOUT_TIME_TEXT: [
                CallbackQueryHandler(checkout_fallback_command_handler,
                                     pass_user_data=True),
                MessageHandler(Filters.text, on_shipping_time_text,
                               pass_user_data=True),
            ],
            BOT_STATE_CHECKOUT_PHONE_NUMBER_TEXT: [
                CallbackQueryHandler(checkout_fallback_command_handler,
                                     pass_user_data=True),

                MessageHandler(Filters.contact | Filters.text,
                               on_phone_number_text, pass_user_data=True),
            ],
            BOT_STATE_CHECKOUT_IDENTIFY_STAGE1: [
                CallbackQueryHandler(checkout_fallback_command_handler,
                                     pass_user_data=True),
                MessageHandler(Filters.all, on_shipping_identify_photo,
                               pass_user_data=True),
            ],
            BOT_STATE_CHECKOUT_IDENTIFY_STAGE2: [
                CallbackQueryHandler(checkout_fallback_command_handler,
                                     pass_user_data=True),
                MessageHandler(Filters.all, on_shipping_identify_stage2,
                               pass_user_data=True),
            ],
            BOT_STATE_ORDER_CONFIRMATION: [
                CallbackQueryHandler(checkout_fallback_command_handler,
                                     pass_user_data=True),
                MessageHandler(Filters.text, on_confirm_order,
                               pass_user_data=True),
            ],
            BOT_LANGUAGE_CHANGE: [
                CallbackQueryHandler(on_bot_language_change,
                                     pass_user_data=True),
            ],
            #
            # admin states
            #

            ADMIN_MENU: [CallbackQueryHandler(
                on_settings_menu, pattern='^settings')],
            ADMIN_STATISTICS: [CallbackQueryHandler(
                on_statistics_menu, pattern='^statistics')],
            ADMIN_BOT_SETTINGS: [CallbackQueryHandler(
                on_bot_settings_menu, pattern='^bot_settings')],
            ADMIN_COURIERS: [
                CallbackQueryHandler(
                    on_admin_couriers, pattern='^bot_couriers')],
            ADMIN_LOCATIONS: [
                CallbackQueryHandler(
                    on_admin_locations, pattern='^bot_locations')],
            ADMIN_CHANNELS: [
                CallbackQueryHandler(on_admin_channels, pattern='^bot_channels')
            ],
            ADMIN_CHANNELS_SELECT_TYPE: [
                CallbackQueryHandler(
                    on_admin_select_channel_type, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_select_channel_type,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel)
            ],
            ADMIN_CHANNELS_ADDRESS: [
                MessageHandler(Filters.text, on_admin_add_channel_address,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel)
            ],
            ADMIN_CHANNELS_REMOVE: [
                CallbackQueryHandler(
                    on_admin_remove_channel, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_remove_channel,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel)
            ],
            ADMIN_BAN_LIST: [
                CallbackQueryHandler(on_admin_ban_list, pattern='^bot_ban_list')
            ],
            ADMIN_BAN_LIST_REMOVE: [
                CallbackQueryHandler(
                    on_admin_remove_ban_list, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_remove_ban_list,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel)
            ],
            ADMIN_BAN_LIST_ADD: [
                CallbackQueryHandler(
                    on_admin_add_ban_list, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_add_ban_list,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel)
            ],
            ADMIN_EDIT_WORKING_HOURS: [
                CallbackQueryHandler(
                    on_admin_edit_working_hours, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_edit_working_hours,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel)
            ],
            ADMIN_EDIT_CONTACT_INFO: [
                CallbackQueryHandler(
                    on_admin_edit_contact_info, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_edit_contact_info,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel)
            ],
            ADMIN_BOT_ON_OFF: [
                CallbackQueryHandler(
                    on_admin_bot_on_off, pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel)
            ],
            ADMIN_ORDER_OPTIONS: [
                CallbackQueryHandler(
                    on_admin_order_options, pattern='^bot_order_options')
            ],
            ADMIN_ADD_DISCOUNT: [
                CallbackQueryHandler(
                    on_admin_add_discount, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_add_discount,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_EDIT_IDENTIFICATION: [
                CallbackQueryHandler(
                    on_admin_edit_identification, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_edit_identification,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_EDIT_RESTRICTION: [
                CallbackQueryHandler(
                    on_admin_edit_restriction, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_edit_restriction,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_ADD_DELIVERY_FEE: [
                CallbackQueryHandler(
                    on_admin_add_delivery, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_add_delivery,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_EDIT_WELCOME_MESSAGE: [
                CallbackQueryHandler(
                    on_admin_edit_welcome_message, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_edit_welcome_message,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_EDIT_ORDER_DETAILS: [
                CallbackQueryHandler(
                    on_admin_edit_order_message, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_edit_order_message,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_EDIT_FINAL_MESSAGE: [
                CallbackQueryHandler(
                    on_admin_edit_final_message, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_edit_final_message,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_INIT: [
                CommandHandler('addproduct', on_admin_cmd_add_product),
                CommandHandler('delproduct', on_admin_cmd_delete_product),
                CommandHandler('addcourier', on_admin_cmd_add_courier),
                CommandHandler('delcourier', on_admin_cmd_delete_courier),
                CommandHandler('on', on_admin_cmd_bot_on),
                CommandHandler('off', on_admin_cmd_bot_off),
                CommandHandler('cancel', on_admin_cancel),
                MessageHandler(Filters.all, on_admin_fallback),
            ],
            ADMIN_TXT_PRODUCT_TITLE: [
                CallbackQueryHandler(
                    on_admin_txt_product_title, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_txt_product_title,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_TXT_PRODUCT_PRICES: [
                MessageHandler(Filters.text, on_admin_txt_product_prices,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_TXT_PRODUCT_PHOTO: [
                MessageHandler(Filters.photo, on_admin_txt_product_photo,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_TXT_DELETE_PRODUCT: [
                CallbackQueryHandler(
                    on_admin_txt_delete_product, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_txt_delete_product,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_TXT_COURIER_NAME: [
                CallbackQueryHandler(
                    on_admin_txt_courier_name, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_txt_courier_name,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_TXT_COURIER_ID: [
                MessageHandler(Filters.text, on_admin_txt_courier_id,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_TXT_COURIER_LOCATION: [
                CallbackQueryHandler(
                    on_admin_btn_courier_location, pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_TXT_DELETE_COURIER: [
                CallbackQueryHandler(
                    on_admin_txt_delete_courier, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_txt_delete_courier,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_TXT_ADD_LOCATION: [
                CallbackQueryHandler(
                    on_admin_txt_location, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_txt_location,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel),
            ],
            ADMIN_TXT_DELETE_LOCATION: [
                CallbackQueryHandler(
                    on_admin_txt_delete_location, pass_user_data=True),
                MessageHandler(Filters.text, on_admin_txt_delete_location,
                               pass_user_data=True),
                CommandHandler('cancel', on_admin_cancel), ]
        },
        fallbacks=[
            CommandHandler('cancel', on_cancel, pass_user_data=True),
            CommandHandler('start', on_start, pass_user_data=True)
        ])

    updater = Updater(config.get_api_token())
    updater.dispatcher.add_handler(MessageHandler(
        Filters.status_update, send_welcome_message))
    updater.dispatcher.add_handler(user_conversation_handler)
    updater.dispatcher.add_handler(
        CallbackQueryHandler(service_channel_courier_query_handler,
                             pattern='^courier',
                             pass_user_data=True))
    updater.dispatcher.add_handler(
        CallbackQueryHandler(service_channel_sendto_courier_handler,
                             pattern='^sendto',
                             pass_user_data=True))
    updater.dispatcher.add_handler(
        CallbackQueryHandler(on_service_send_order_to_courier,
                             pattern='^order',
                             pass_user_data=True))
    updater.dispatcher.add_handler(
        CallbackQueryHandler(resend_responsibility_keyboard,
                             pattern='^dropped',
                             pass_user_data=True))
    updater.dispatcher.add_handler(
        CallbackQueryHandler(make_confirm,
                             pattern='^confirmed',
                             pass_user_data=True))
    updater.dispatcher.add_handler(
        CallbackQueryHandler(make_unconfirm,
                             pattern='^notconfirmed',
                             pass_user_data=True))
    updater.dispatcher.add_error_handler(on_error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    create_tables()
    main()
