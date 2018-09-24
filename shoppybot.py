#! /usr/bin/env python3

from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, Filters, MessageHandler, Updater, \
    Handler
from src import admin
from src import enums
from src.handlers import on_start, on_menu, on_error, on_chat_update_handler
from src.helpers import config, get_user_id, \
    get_user_session

from src.shortcuts import resend_responsibility_keyboard, make_confirm, make_unconfirm

from src.models import create_tables, close_db
from src import triggers

# will be called when conversation context is lost (e.g. bot is restarted)
# and the user clicks menu buttons


def fallback_query_handler(bot, update, user_data):
    user_id = get_user_id(update)
    user_data = get_user_session(user_id)
    return on_menu(bot, update, user_data)

def close_db_on_signal(signum, frame):
    close_db()


def main():
    courier_conversation_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(triggers.on_courier_action_to_confirm,
                                 pattern='^confirm_courier',
                                 ),
            CallbackQueryHandler(triggers.on_courier_ping_client,
                                 pattern='^ping'),
            CallbackQueryHandler(triggers.on_admin_drop_order, pattern='^admin_dropped'),
            CallbackQueryHandler(resend_responsibility_keyboard,
                                 pattern='^dropped',
                                 )
        ],
        states={
            enums.COURIER_STATE_INIT: [
                CallbackQueryHandler(triggers.on_courier_action_to_confirm,
                                     pattern='^confirm_courier',
                                     ),
                CallbackQueryHandler(triggers.on_courier_ping_client,
                                     pattern='^ping'),
                CallbackQueryHandler(triggers.on_admin_drop_order, pattern='^admin_dropped'),
                CallbackQueryHandler(resend_responsibility_keyboard,
                                     pattern='^dropped',
                                     )
            ],
            enums.COURIER_STATE_CONFIRM_ORDER: [
                CallbackQueryHandler(triggers.on_courier_confirm_order,)
                                     #pattern='^confirm_order')

            ],
            enums.COURIER_STATE_CONFIRM_REPORT: [
                CallbackQueryHandler(triggers.on_courier_confirm_report,)
                                     #pattern='^confirm_report')
            ],
            enums.COURIER_STATE_REPORT_REASON: [
                MessageHandler(Filters.text, triggers.on_courier_enter_reason),
                CallbackQueryHandler(triggers.on_courier_cancel_reason, pattern='^back')
            ]

        },
        fallbacks=[
            CommandHandler('start', on_start, pass_user_data=True)
        ]
    )
    user_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', on_start, pass_user_data=True),
                      CommandHandler('admin', admin.on_start_admin),
                      CallbackQueryHandler(fallback_query_handler,
                                           pattern='^(menu|product)',
                                           pass_user_data=True)],
        states={
            enums.BOT_STATE_INIT: [
                CommandHandler('start', on_start, pass_user_data=True),
                CommandHandler('admin', admin.on_start_admin),
                CallbackQueryHandler(
                    on_menu, pattern='^(menu|product)', pass_user_data=True)
            ],
            enums.BOT_STATE_CHECKOUT_SHIPPING: [
                CallbackQueryHandler(triggers.checkout_fallback_command_handler,
                                     pass_user_data=True),
                MessageHandler(Filters.text, triggers.on_shipping_method,
                               pass_user_data=True),
            ],
            enums.BOT_STATE_CHECKOUT_LOCATION_PICKUP: [
                CallbackQueryHandler(triggers.checkout_fallback_command_handler,
                                     pass_user_data=True),
                MessageHandler(Filters.text, triggers.on_shipping_pickup_location,
                               pass_user_data=True),
            ],
            enums.BOT_STATE_CHECKOUT_LOCATION_DELIVERY: [
                CallbackQueryHandler(triggers.checkout_fallback_command_handler,
                                     pass_user_data=True),
                MessageHandler(Filters.text | Filters.location,
                               triggers.on_shipping_delivery_address,
                               pass_user_data=True),
            ],
            enums.BOT_STATE_CHECKOUT_TIME: [
                CallbackQueryHandler(triggers.checkout_fallback_command_handler,
                                     pass_user_data=True),
                MessageHandler(Filters.text, triggers.on_checkout_time,
                               pass_user_data=True),
            ],
            enums.BOT_STATE_CHECKOUT_TIME_TEXT: [
                CallbackQueryHandler(triggers.checkout_fallback_command_handler,
                                     pass_user_data=True),
                MessageHandler(Filters.text, triggers.on_shipping_time_text,
                               pass_user_data=True),
            ],
            enums.BOT_STATE_CHECKOUT_PHONE_NUMBER_TEXT: [
                CallbackQueryHandler(triggers.checkout_fallback_command_handler,
                                     pass_user_data=True),

                MessageHandler(Filters.contact | Filters.text,
                               triggers.on_phone_number_text, pass_user_data=True),
            ],
            enums.BOT_STATE_CHECKOUT_IDENTIFY_STAGE1: [
                CallbackQueryHandler(triggers.checkout_fallback_command_handler,
                                     pass_user_data=True),
                MessageHandler(Filters.all, triggers.on_shipping_identify_photo,
                               pass_user_data=True),
            ],
            enums.BOT_STATE_CHECKOUT_IDENTIFY_STAGE2: [
                CallbackQueryHandler(triggers.checkout_fallback_command_handler,
                                     pass_user_data=True),
                MessageHandler(Filters.all, triggers.on_shipping_identify_stage2,
                               pass_user_data=True),
            ],
            enums.BOT_STATE_ORDER_CONFIRMATION: [
                CallbackQueryHandler(triggers.checkout_fallback_command_handler,
                                     pass_user_data=True),
                MessageHandler(Filters.text, triggers.on_confirm_order,
                               pass_user_data=True),
            ],
            enums.BOT_LANGUAGE_CHANGE: [
                CallbackQueryHandler(triggers.on_bot_language_change,
                                     pass_user_data=True),
            ],
            enums.BOT_STATE_MY_ORDERS: [
                CallbackQueryHandler(triggers.on_my_orders, pass_user_data=True)
            ],
            enums.BOT_STATE_MY_ORDER_DATE: [
                CallbackQueryHandler(triggers.on_calendar_change, pattern='^calendar', pass_user_data=True),
                CallbackQueryHandler(triggers.on_my_order_date, pass_user_data=True)
            ],
            enums.BOT_STATE_MY_LAST_ORDER: [
                CallbackQueryHandler(triggers.on_my_last_order, pass_user_data=True)
            ],
            enums.BOT_STATE_MY_ORDER_SELECT:[
                CallbackQueryHandler(triggers.on_my_order_select, pass_user_data=True)
            ],
            #
            # admin states
            #

            enums.ADMIN_MENU: [CallbackQueryHandler(
                triggers.on_settings_menu, pattern='^settings')],
            enums.ADMIN_STATISTICS: [CallbackQueryHandler(
                triggers.on_statistics_menu, pattern='^statistics', pass_user_data=True)],
            enums.ADMIN_STATISTICS_GENERAL: [
                CallbackQueryHandler(triggers.on_calendar_change, pattern='^calendar', pass_user_data=True),
                CallbackQueryHandler(triggers.on_statistics_general, pass_user_data=True),
                #CallbackQueryHandler(on_calendar_change, pattern='^calendar', pass_user_data=True),
                # CallbackQueryHandler(on_statistics_general, pass_user_data=True)
            ],
            enums.ADMIN_STATISTICS_COURIERS: [
                CallbackQueryHandler(triggers.on_statistics_courier_select, pass_user_data=True)
            ],
            enums.ADMIN_STATISTICS_COURIERS_DATE: [
                CallbackQueryHandler(triggers.on_calendar_change, pattern='^calendar', pass_user_data=True),
                CallbackQueryHandler(triggers.on_statistics_couriers, pass_user_data=True)
            ],
            enums.ADMIN_STATISTICS_LOCATIONS: [
                CallbackQueryHandler(triggers.on_statistics_locations_select, pass_user_data=True)
            ],
            enums.ADMIN_STATISTICS_LOCATIONS_DATE: [
                CallbackQueryHandler(triggers.on_calendar_change, pattern='^calendar', pass_user_data=True),
                CallbackQueryHandler(triggers.on_statistics_locations, pass_user_data=True)
            ],
            enums.ADMIN_STATISTICS_USER: [
                CallbackQueryHandler(triggers.on_statistics_username, pass_user_data=True),
                MessageHandler(Filters.text, triggers.on_statistics_username, pass_user_data=True)
            ],
            enums.ADMIN_STATISTICS_USER_DATE: [
                CallbackQueryHandler(triggers.on_calendar_change, pattern='^calendar', pass_user_data=True),
                CallbackQueryHandler(triggers.on_statistics_user, pass_user_data=True)
            ],
            enums.ADMIN_BOT_SETTINGS: [CallbackQueryHandler(
                triggers.on_bot_settings_menu, pattern='^bot_settings')],
            enums.ADMIN_COURIERS: [
                CallbackQueryHandler(
                    triggers.on_admin_couriers, pattern='^bot_couriers')],
            enums.ADMIN_COURIERS_SHOW: [
                CallbackQueryHandler(admin.on_admin_show_courier, pass_user_data=True)
            ],
            enums.ADMIN_COURIER_ADD: [
                CallbackQueryHandler(admin.on_admin_add_courier, pass_user_data=True)
            ],
            enums.ADMIN_COURIER_DELETE: [
                CallbackQueryHandler(admin.on_admin_delete_courier)
            ],
            enums.ADMIN_LOCATIONS: [
                CallbackQueryHandler(
                    admin.on_admin_locations, pattern='^bot_locations')],
            enums.ADMIN_PRODUCTS: [
                CallbackQueryHandler(admin.on_admin_products, pattern='^bot_products', pass_user_data=True)
            ],
            enums.ADMIN_PRODUCTS_SHOW: [
                CallbackQueryHandler(admin.on_admin_show_product, pass_user_data=True)
            ],
            enums.ADMIN_PRODUCT_ADD: [
                CallbackQueryHandler(admin.on_admin_product_add, pattern='^bot_product', pass_user_data=True)
            ],
            enums.ADMIN_PRODUCT_LAST_ADD: [
                CallbackQueryHandler(admin.on_admin_product_last_select, pass_user_data=True)
            ],
            enums.ADMIN_WAREHOUSE_PRODUCT: [
                CallbackQueryHandler(admin.on_admin_warehouse_products, pass_user_data=True)
            ],
            enums.ADMIN_WAREHOUSE: [
                CallbackQueryHandler(admin.on_admin_warehouse, pass_user_data=True)
            ],
            enums.ADMIN_WAREHOUSE_COURIER: [
                CallbackQueryHandler(admin.on_admin_warehouse_courier, pass_user_data=True)
            ],
            enums.ADMIN_WAREHOUSE_PRODUCT_CREDITS: [
                CallbackQueryHandler(admin.on_admin_warehouse_product_credits, pass_user_data=True),
                MessageHandler(Filters.text, admin.on_admin_warehouse_product_credits, pass_user_data=True)
            ],
            enums.ADMIN_WAREHOUSE_COURIER_CREDITS: [
                CallbackQueryHandler(admin.on_admin_warehouse_courier_credits, pass_user_data=True),
                MessageHandler(Filters.text, admin.on_admin_warehouse_courier_credits, pass_user_data=True)
            ],
            enums.ADMIN_CHANNELS: [
                CallbackQueryHandler(triggers.on_admin_channels, pattern='^bot_channels')
            ],
            enums.ADMIN_CHANNELS_LANGUAGE: [
                CallbackQueryHandler(triggers.on_admin_channels_language)
            ],
            enums.ADMIN_CHANNELS_SELECT_TYPE: [
                CallbackQueryHandler(
                    admin.on_admin_select_channel_type, pass_user_data=True),
                MessageHandler(Filters.text, admin.on_admin_select_channel_type,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel)
            ],
            enums.ADMIN_CHANNELS_ADDRESS: [
                MessageHandler(Filters.text, admin.on_admin_add_channel_address,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel)
            ],
            enums.ADMIN_CHANNELS_REMOVE: [
                CallbackQueryHandler(
                    admin.on_admin_remove_channel, pass_user_data=True),
                MessageHandler(Filters.text, admin.on_admin_remove_channel,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel)
            ],
            enums.ADMIN_BAN_LIST: [
                CallbackQueryHandler(triggers.on_admin_ban_list, pattern='^bot_ban_list')
            ],
            enums.ADMIN_BAN_LIST_REMOVE: [
                CallbackQueryHandler(
                    admin.on_admin_remove_ban_list, pass_user_data=True),
                MessageHandler(Filters.text, admin.on_admin_remove_ban_list,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel)
            ],
            enums.ADMIN_BAN_LIST_ADD: [
                CallbackQueryHandler(
                    admin.on_admin_add_ban_list, pass_user_data=True),
                MessageHandler(Filters.text, admin.on_admin_add_ban_list,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel)
            ],
            enums.ADMIN_EDIT_WORKING_HOURS: [
                CallbackQueryHandler(
                    admin.on_admin_edit_working_hours, pass_user_data=True),
                MessageHandler(Filters.text, admin.on_admin_edit_working_hours,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel)
            ],
            enums.ADMIN_EDIT_CONTACT_INFO: [
                CallbackQueryHandler(
                    admin.on_admin_edit_contact_info, pass_user_data=True),
                MessageHandler(Filters.text, admin.on_admin_edit_contact_info,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel)
            ],
            enums.ADMIN_BOT_ON_OFF: [
                CallbackQueryHandler(
                    admin.on_admin_bot_on_off, pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel)
            ],
            enums.ADMIN_ORDER_OPTIONS: [
                CallbackQueryHandler(
                    admin.on_admin_order_options, pattern='^bot_order_options', pass_user_data=True)
            ],
            enums.ADMIN_ADD_DISCOUNT: [
                CallbackQueryHandler(
                    admin.on_admin_add_discount, pass_user_data=True),
                MessageHandler(Filters.text, admin.on_admin_add_discount,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel),
            ],
            enums.ADMIN_EDIT_IDENTIFICATION_STAGES: [
                CallbackQueryHandler(admin.on_admin_edit_identification_stages, pass_user_data=True)
            ],
            enums.ADMIN_EDIT_IDENTIFICATION_QUESTION: [
                CallbackQueryHandler(admin.on_admin_edit_identification_question),
                MessageHandler(Filters.text, admin.on_admin_edit_identification_question)
            ],
            # enums.ADMIN_EDIT_IDENTIFICATION: [
            #     CallbackQueryHandler(
            #         admin.on_admin_edit_identification, pass_user_data=True),
            #     MessageHandler(Filters.text, admin.on_admin_edit_identification,
            #                    pass_user_data=True),
            #     CommandHandler('cancel', admin.on_admin_cancel),
            # ],
            enums.ADMIN_EDIT_RESTRICTION: [
                CallbackQueryHandler(
                    admin.on_admin_edit_restriction, pass_user_data=True),
                # MessageHandler(Filters.text, admin.on_admin_edit_restriction,
                #                pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel),
            ],
            enums.ADMIN_ADD_DELIVERY_FEE: [
                CallbackQueryHandler(
                    admin.on_admin_add_delivery, pass_user_data=True),
                MessageHandler(Filters.text, admin.on_admin_add_delivery,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel),
            ],
            enums.ADMIN_EDIT_WELCOME_MESSAGE: [
                CallbackQueryHandler(
                    admin.on_admin_edit_welcome_message, pass_user_data=True),
                MessageHandler(Filters.text, admin.on_admin_edit_welcome_message,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel),
            ],
            enums.ADMIN_EDIT_ORDER_DETAILS: [
                CallbackQueryHandler(
                    admin.on_admin_edit_order_message, pass_user_data=True),
                MessageHandler(Filters.text, admin.on_admin_edit_order_message,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel),
            ],
            enums.ADMIN_EDIT_FINAL_MESSAGE: [
                CallbackQueryHandler(
                    admin.on_admin_edit_final_message, pass_user_data=True),
                MessageHandler(Filters.text, admin.on_admin_edit_final_message,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel),
            ],
            enums.ADMIN_INIT: [
                CommandHandler('addproduct', admin.on_admin_cmd_add_product),
                CommandHandler('delproduct', admin.on_admin_cmd_delete_product, pass_user_data=True),
                CommandHandler('addcourier', admin.on_admin_cmd_add_courier),
                CommandHandler('delcourier', admin.on_admin_cmd_delete_courier),
                CommandHandler('on', admin.on_admin_cmd_bot_on),
                CommandHandler('off', admin.on_admin_cmd_bot_off),
                CommandHandler('cancel', admin.on_admin_cancel),
                MessageHandler(Filters.all, admin.on_admin_fallback),
            ],
            enums.ADMIN_TXT_PRODUCT_TITLE: [
                CallbackQueryHandler(
                    admin.on_admin_txt_product_title, pass_user_data=True),
                MessageHandler(Filters.text, admin.on_admin_txt_product_title,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel),
            ],
            enums.ADMIN_TXT_PRODUCT_PRICES: [
                MessageHandler(Filters.text, admin.on_admin_txt_product_prices,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel),
            ],
            enums.ADMIN_TXT_PRODUCT_PHOTO: [
                MessageHandler(Filters.photo, admin.on_admin_txt_product_photo,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel),
            ],
            # ADMIN_TXT_DELETE_PRODUCT: [
            #     CallbackQueryHandler(
            #         on_admin_txt_delete_product, pass_user_data=True),
            #     MessageHandler(Filters.text, on_admin_txt_delete_product,
            #                    pass_user_data=True),
            #     CommandHandler('cancel', on_admin_cancel),
            # ],
            enums.ADMIN_DELETE_PRODUCT: [
                CallbackQueryHandler(admin.on_admin_delete_product, pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel)
            ],
            enums.ADMIN_TXT_COURIER_NAME: [
                CallbackQueryHandler(
                    admin.on_admin_txt_courier_name, pass_user_data=True),
                MessageHandler(Filters.text, admin.on_admin_txt_courier_name,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel),
            ],
            enums.ADMIN_TXT_COURIER_ID: [
                MessageHandler(Filters.text, admin.on_admin_txt_courier_id,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel),
            ],
            enums.ADMIN_TXT_COURIER_LOCATION: [
                CallbackQueryHandler(
                    admin.on_admin_btn_courier_location, pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel),
            ],
            enums.ADMIN_TXT_DELETE_COURIER: [
                CallbackQueryHandler(
                    admin.on_admin_txt_delete_courier, pass_user_data=True),
                MessageHandler(Filters.text, admin.on_admin_txt_delete_courier,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel),
            ],
            enums.ADMIN_TXT_ADD_LOCATION: [
                CallbackQueryHandler(
                    admin.on_admin_txt_location, pass_user_data=True),
                MessageHandler(Filters.text, admin.on_admin_txt_location,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel),
            ],
            enums.ADMIN_TXT_DELETE_LOCATION: [
                CallbackQueryHandler(
                    admin.on_admin_txt_delete_location, pass_user_data=True),
                MessageHandler(Filters.text, admin.on_admin_txt_delete_location,
                               pass_user_data=True),
                CommandHandler('cancel', admin.on_admin_cancel), ]
        },
        fallbacks=[
            CommandHandler('cancel', triggers.on_cancel, pass_user_data=True),
            CommandHandler('start', on_start, pass_user_data=True)
        ])

    updater = Updater(config.get_api_token(), user_sig_handler=close_db_on_signal)
    # updater.dispatcher.add_handler(CallbackQueryHandler(on_chat_update_handler))
    updater.dispatcher.add_handler(MessageHandler(
        Filters.status_update.new_chat_members, triggers.send_welcome_message))
    # updater.dispatcher.add_handler(MessageHandler(
    #     Filters.text, triggers.get_channel_id
    # ))
    # updater.dispatcher.add_handler(MessageHandler(
    #     Filters.status_update.left_chat_member, on_courier_left))
    updater.dispatcher.add_handler(user_conversation_handler)
    updater.dispatcher.add_handler(courier_conversation_handler)
    # updater.dispatcher.add_handler(CallbackQueryHandler(on_calendar_change, pattern='^calendar', pass_user_data=True))
    updater.dispatcher.add_handler(
        CallbackQueryHandler(triggers.service_channel_courier_query_handler,
                             pattern='^courier',
                             pass_user_data=True))
    updater.dispatcher.add_handler(
        CallbackQueryHandler(triggers.service_channel_sendto_courier_handler,
                             pattern='^sendto',
                             pass_user_data=True))
    updater.dispatcher.add_handler(
        CallbackQueryHandler(triggers.on_service_send_order_to_courier,
                             pattern='^order',
                             pass_user_data=True))
    # updater.dispatcher.add_handler(
        # CallbackQueryHandler(resend_responsibility_keyboard,
        #                      pattern='^dropped',
        #                      pass_user_data=True))
    updater.dispatcher.add_handler(
        CallbackQueryHandler(make_confirm,
                             pattern='^confirmed',
                             pass_user_data=True))
    updater.dispatcher.add_handler(
        CallbackQueryHandler(make_unconfirm,
                             pattern='^notconfirmed',
                             pass_user_data=True))
    # updater.dispatcher.add_handler(on_courier_action_to_confirm,
    #                                pattern='^confirm_courier')
    # updater.dispatcher.add_handler(on_courier_ping_client,
    #                                pattern='^ping')
    #
    # updater.dispatcher.add_handler()
    updater.dispatcher.add_error_handler(on_error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    create_tables()
    main()