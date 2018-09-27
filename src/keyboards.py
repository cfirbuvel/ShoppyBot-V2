from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ParseMode
from .helpers import get_trans, get_user_id, config
import math
import calendar
import datetime

def create_time_keyboard(trans):
    _ = trans
    button_row = [
        [
            KeyboardButton(_('⏰ Now'))
        ],
        [
            KeyboardButton(_('📅 Set time'))
        ],
        [
            KeyboardButton(_('↩ Back')),
            KeyboardButton(_('❌ Cancel'))
        ],
    ]
    return ReplyKeyboardMarkup(button_row, resize_keyboard=True)


def create_confirmation_keyboard(trans):
    _ = trans
    button_row = [
        [KeyboardButton(_('✅ Confirm'))],
        [
            KeyboardButton(_('↩ Back')),
            KeyboardButton(_('❌ Cancel'))
        ]
    ]
    return ReplyKeyboardMarkup(button_row, resize_keyboard=True)


def create_phone_number_request_keyboard(trans):
    _ = trans
    buttons = [
        [KeyboardButton(
            text=_('📞 Allow to send my phone number'),
            request_contact=True
        ),
            KeyboardButton(_('✒️Enter phone manually')),
        ],
        [KeyboardButton(_('↩ Back'))],
        [KeyboardButton(_('❌ Cancel'))],
    ]

    return ReplyKeyboardMarkup(buttons, one_time_keyboard=True)


def create_location_request_keyboard(trans):
    _ = trans
    buttons = [
        [KeyboardButton(
            text=_('📍 Allow to send my location'),
            request_location=True
        ),
            KeyboardButton(text=_('✒️Enter location manually')),
        ],
        [KeyboardButton(_('↩ Back'))],
        [KeyboardButton(_('❌ Cancel'))],
    ]

    return ReplyKeyboardMarkup(buttons, one_time_keyboard=True)

# def create_back_keyboard(trans):
#     _ = trans
#     buttons = [
#         [InlineKeyboardButton(_('↩ Back'))]
#     ]
#     return InlineKeyboardMarkup(buttons)

def create_cancel_keyboard(trans):
    _ = trans
    button_row = [
        [
            KeyboardButton(_('↩ Back')),
            KeyboardButton(_('❌ Cancel'))
        ],
    ]
    return ReplyKeyboardMarkup(button_row, resize_keyboard=True)


def create_pickup_location_keyboard(trans, location_names):
    _ = trans
    button_column = []
    for location_name in location_names:
        button_column.append([KeyboardButton(location_name)])

    button_column.append(
        [
            KeyboardButton(_('↩ Back')),
            KeyboardButton(_('❌ Cancel'))
        ])
    return ReplyKeyboardMarkup(button_column, resize_keyboard=True)


def create_shipping_keyboard(trans):
    _ = trans
    button_row = [
        [KeyboardButton(_('🏪 Pickup'))],
        [KeyboardButton(_('🚚 Delivery'))],
        [KeyboardButton(_('❌ Cancel'))],
    ]
    return ReplyKeyboardMarkup(button_row, resize_keyboard=True)


def create_warehouse_keyboard(trans):
    _ = trans
    buttons = [
        [InlineKeyboardButton(_('📊 Change product\'s credits'), callback_data='warehouse_credits')],
        [InlineKeyboardButton(_('🚴‍♀️ Add credits to courier'), callback_data='warehouse_courier')],
        [InlineKeyboardButton(_('↩ Back'), callback_data='warehouse_back')]
    ]
    return InlineKeyboardMarkup(buttons)

def create_locations_keyboard(location_names, trans):
    _ = trans
    button_row = []
    for location_name in location_names:
        button_row.append([InlineKeyboardButton(_(location_name),
                                                callback_data=location_name)])
    back_button = InlineKeyboardButton(_('↩ Back'), callback_data='back')
    cancel_button = InlineKeyboardButton(_('❌ Cancel'), callback_data='back')
    button_row.append([back_button, cancel_button])
    return InlineKeyboardMarkup(button_row)


def create_service_notice_keyboard(order_id, trans, photo_msg_id):
    _ = trans
    buttons = [
        [
            InlineKeyboardButton(
                _('Take Responsibility'),
                callback_data='courier|{}|{}'.format(order_id, photo_msg_id))
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def create_courier_confirmation_keyboard(order_id, courier_name, trans, photo_msg_id, assigned_msg_id):
    #_ = get_trans(user_id)
    _ = trans
    buttons = [
        InlineKeyboardButton(_('Yes'),
                             callback_data='confirmed_courier|{}|{}'.format(
                                 order_id, courier_name)),
        InlineKeyboardButton(_('No'),
                             callback_data='notconfirmed_courier|{}|{}|{}|{}'.format(
                                 order_id, courier_name, photo_msg_id, assigned_msg_id)),
    ]
    return InlineKeyboardMarkup([buttons])


def create_courier_assigned_keyboard(courier_nickname, order_id, trans):
    _ = trans
    buttons = [
        [InlineKeyboardButton(_('Assigned to @{}').format(courier_nickname),
                              url='https://t.me/{}'.format(courier_nickname))],
        # [InlineKeyboardButton(_('Drop responsibility'),
        #                       callback_data='dropped|{}'.format(order_id))],
    ]
    return InlineKeyboardMarkup(buttons)


def create_main_keyboard(trans, review_channel, user, is_admin=None, total_price=0):
    _ = trans
    main_button_list = [
        [InlineKeyboardButton(_('🏪 Our products'),
                              callback_data='menu_products')],
        [InlineKeyboardButton(_('🛍 Checkout').format(total_price),
                              callback_data='menu_order')],
        [InlineKeyboardButton(_('⭐ Reviews'), url=review_channel)],
        [InlineKeyboardButton(_('⏰ Working hours'),
                              callback_data='menu_hours')],
        [InlineKeyboardButton(_('☎ Contact info'),
                              callback_data='menu_contact')],
        [InlineKeyboardButton(_('🈚️ Bot Languages'),
                              callback_data='menu_language')],
    ]
    if user.user_orders:
        main_button_list.append([InlineKeyboardButton(_('📖 My Orders'), callback_data='menu_myorders')])
    if is_admin:
        main_button_list.append(
            [InlineKeyboardButton(_('⚙️ Settings'),
                                  callback_data='menu_settings')])
    return InlineKeyboardMarkup(main_button_list)


def create_my_orders_keyboard(trans):
    _ = trans
    buttons = [
        [InlineKeyboardButton(_('📦 My last order'), callback_data='last_order')],
        [InlineKeyboardButton(_('📆 Order by date'), callback_data='by_date')],
        [InlineKeyboardButton(_('↩ Back'), callback_data='back')],
    ]
    return InlineKeyboardMarkup(buttons)

def create_my_order_keyboard(order_id, cancel, trans):
    _ = trans
    buttons = [
        [InlineKeyboardButton(_('💳 Show Order'), callback_data='show|{}'.format(order_id))]
    ]
    if cancel:
        buttons.append([InlineKeyboardButton(_('❌ Cancel order'), callback_data='cancel|{}'.format(order_id))])
    buttons.append([InlineKeyboardButton(_('↩ Back'), callback_data='back|')])
    return InlineKeyboardMarkup(buttons)

def create_bot_language_keyboard(trans):
    _ = trans
    keyboard = [
        [InlineKeyboardButton(
            _('עברית 🇮🇱'), callback_data='iw')],
        [InlineKeyboardButton(
            _('🇺🇸 English'), callback_data='en')]
    ]
    return InlineKeyboardMarkup(keyboard, resize_keyboard=True)


def create_product_keyboard(trans, product_id, user_data, cart):
    button_row = []
    _ = trans
    if cart.get_product_count(user_data, product_id) > 0:
        button = InlineKeyboardButton(
            _('➕ Add more'), callback_data='product_add|{}'.format(product_id))
        button_row.append(button)
        button = InlineKeyboardButton(
            _('➖ Remove'), callback_data='product_remove|{}'.format(product_id))
        button_row.append(button)
    else:
        button = InlineKeyboardButton(
            _('🛍 Add to cart'),
            callback_data='product_add|{}'.format(product_id))
        button_row.append(button)

    return InlineKeyboardMarkup([button_row])


def create_bot_config_keyboard(trans):
    _ = trans
    button_row = [
        [InlineKeyboardButton(
            _('Set welcome message'),
            callback_data='setwelcomemessage'
        )],
    ]

    return InlineKeyboardMarkup(button_row, resize_keyboard=True)


def create_admin_keyboard(trans):
    _ = trans
    main_button_list = [
        [InlineKeyboardButton(_('📈 Statistics'),
                              callback_data='settings_statistics')],
        [InlineKeyboardButton(_('⚙ Bot settings'),
                              callback_data='settings_bot')],
        [InlineKeyboardButton(_('↩ Back'),
                              callback_data='settings_back')],
    ]

    return InlineKeyboardMarkup(main_button_list)


def create_statistics_keyboard(trans):
    _ = trans
    main_button_list = [
        [InlineKeyboardButton(_('💵 General statistics'), callback_data='statistics_general')],
        [InlineKeyboardButton(_('🛵 Get statistics by different couriers'), callback_data='statistics_couriers')],
        [InlineKeyboardButton(_('🏠 Get statistics by locations'), callback_data='statistics_locations')],
        [InlineKeyboardButton(_('🌝 Get statistics by user'), callback_data='statistics_user')],
        [InlineKeyboardButton(_('↩ Back'), callback_data='statistics_back')]
    ]
    return InlineKeyboardMarkup(main_button_list)


def create_calendar_keyboard(year, month, trans):
    _ = trans
    markup = []
    row = []
    current_date = datetime.date.today()
    if year > 1:
        row.append(InlineKeyboardButton('<', callback_data='calendar_previous_year'))
    row.append(InlineKeyboardButton(year, callback_data='year|{}'.format(year)))
    if not year >= current_date.year:
        row.append(InlineKeyboardButton('>', callback_data='calendar_next_year'))
    markup.append(row)
    month_name = calendar.month_name[month]
    month_name = _(month_name)
    row = [
        InlineKeyboardButton('<', callback_data='calendar_previous_month'),
        InlineKeyboardButton(month_name, callback_data='month|{}'.format(month)),
        InlineKeyboardButton('>', callback_data='calendar_next_month')
    ]
    markup.append(row)
    my_calendar = calendar.monthcalendar(year, month)
    for week in my_calendar:
        row = []
        for day in week:
            if (day == 0):
                row.append(InlineKeyboardButton(" ", callback_data='ignore|'))
            else:
                row.append(InlineKeyboardButton(str(day), callback_data='day|{}'.format(day)))
        markup.append(row)
    markup.append([InlineKeyboardButton(_('↩ Back'), callback_data='back|')])
    return InlineKeyboardMarkup(markup)


def create_bot_settings_keyboard(trans):
    _ = trans
    bot_status = config.get_bot_on_off()
    bot_status = _('ON') if bot_status else _('OFF')
    main_button_list = [
        [InlineKeyboardButton(_('💳 Order options'),
                              callback_data='bot_settings_order_options')],
        [InlineKeyboardButton(_('🛵 Couriers'),
                              callback_data='bot_settings_couriers')],
        [InlineKeyboardButton(_('✉️ Channels'),
                              callback_data='bot_settings_channels')],
        [InlineKeyboardButton(_('⏰ Edit working hours'),
                              callback_data='bot_settings_edit_working_hours')],
        [InlineKeyboardButton(_('🔥 Client ban-list'),
                              callback_data='bot_settings_ban_list')],
        [InlineKeyboardButton(_('☎️ Edit contact info'),
                              callback_data='bot_settings_edit_contact_info')],
        [InlineKeyboardButton(_('⚡️ Bot Status {}').format(bot_status),
                              callback_data='bot_settings_bot_on_off')],
        [InlineKeyboardButton(_('💫 Reset all data'),
                              callback_data='bot_settings_reset_all_data')],
        [InlineKeyboardButton(_('↩ Back'),
                              callback_data='bot_settings_back')],
    ]

    return InlineKeyboardMarkup(main_button_list)


def create_bot_couriers_keyboard(trans):
    _ = trans
    main_button_list = [
        [InlineKeyboardButton(_('🛵 View couriers'),
                              callback_data='bot_couriers_view')],
        [InlineKeyboardButton(_('➕ Add couriers'),
                              callback_data='bot_couriers_add')],
        [InlineKeyboardButton(_('➖ Remove couriers'),
                              callback_data='bot_couriers_delete')],
        [InlineKeyboardButton(_('↩ Back'),
                              callback_data='bot_couriers_back')],
    ]

    return InlineKeyboardMarkup(main_button_list)


def create_bot_channels_keyboard(trans):
    _ = trans
    main_button_list = [
        [InlineKeyboardButton(_('✉️ View channels'),
                              callback_data='bot_channels_view')],
        [InlineKeyboardButton(_('➕ Add channel'),
                              callback_data='bot_channels_add')],
        [InlineKeyboardButton(_('➖ Remove channel'),
                              callback_data='bot_channels_remove')],
        [InlineKeyboardButton(_('🈚︎ Change channels language'),
                              callback_data='bot_channels_language')],
        [InlineKeyboardButton(_('↩ Back'),
                              callback_data='bot_channels_back')],
    ]

    return InlineKeyboardMarkup(main_button_list)

def create_bot_products_keyboard(trans):
    _ = trans
    buttons = [
        [InlineKeyboardButton(_('🏪 View Products'), callback_data='bot_products_view')],
        [InlineKeyboardButton(_('➕ Add product'), callback_data='bot_products_add')],
        [InlineKeyboardButton(_('➖ Remove product'), callback_data='bot_products_remove')],
        [InlineKeyboardButton(_('↩ Back'), callback_data='bot_products_back')]
    ]
    return InlineKeyboardMarkup(buttons)


def create_bot_product_add_keyboard(trans):
    _ = trans
    buttons = [
        [InlineKeyboardButton(_('New Product'), callback_data='bot_product_new')],
        [InlineKeyboardButton(_('Last Products'), callback_data='bot_product_last')],
        [InlineKeyboardButton(_('↩ Back'), callback_data='bot_product_back')]
    ]
    return InlineKeyboardMarkup(buttons)


def create_select_products_chunk_keyboard(trans, chunk, selected_command, back_command=None):
    _ = trans
    buttons = []
    for name, id in chunk:
        callback_command = '{}|{}'.format(selected_command, id)
        btn = [InlineKeyboardButton(name, callback_data=callback_command)]
        buttons.append(btn)
    if back_command:
        back_command = '{}|'.format(back_command)
        buttons.append([InlineKeyboardButton(_('↩ Back'), callback_data=back_command)])
    return InlineKeyboardMarkup(buttons)



def create_bot_locations_keyboard(trans):
    _ = trans
    main_button_list = [
        [InlineKeyboardButton(_('🎯️ View locations'),
                              callback_data='bot_locations_view')],
        [InlineKeyboardButton(_('➕ Add location'),
                              callback_data='bot_locations_add')],
        [InlineKeyboardButton(_('➖ Remove location'),
                              callback_data='bot_locations_delete')],
        [InlineKeyboardButton(_('↩ Back'),
                              callback_data='bot_locations_back')],
    ]

    return InlineKeyboardMarkup(main_button_list)


def create_bot_order_options_keyboard(trans):
    _ = trans
    main_button_list = [
        [InlineKeyboardButton(_('🏪 My Products'),
                              callback_data='bot_order_options_product')],
        [InlineKeyboardButton(_('🏗 Warehouse'),
                              callback_data='bot_order_options_warehouse')],
        [InlineKeyboardButton(_('💲 Add discount'),
                              callback_data='bot_order_options_discount')],
        [InlineKeyboardButton(_('🚕 Add delivery fee'),
                              callback_data='bot_order_options_delivery_fee')],
        [InlineKeyboardButton(_('🎯 Locations'),
                              callback_data='bot_order_options_add_locations')],
        [InlineKeyboardButton(_('👨‍ Edit identify process'),
                              callback_data='bot_order_options_identify')],
        [InlineKeyboardButton(_('🔥 Edit Restricted area'),
                              callback_data='bot_order_options_restricted')],
        [InlineKeyboardButton(_('✉ Edit Welcome message'),
                              callback_data='bot_order_options_welcome')],
        [InlineKeyboardButton(_('✉ Edit Order details message'),
                              callback_data='bot_order_options_details')],
        [InlineKeyboardButton(_('✉ Edit Final message'),
                              callback_data='bot_order_options_final')],
        [InlineKeyboardButton(_('↩ Back'),
                              callback_data='bot_order_options_back')],
    ]

    return InlineKeyboardMarkup(main_button_list)


def create_back_button(trans):
    _ = trans
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_('❌ Cancel'), callback_data='back')]
    ])


def create_on_off_buttons(trans):
    _ = trans
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_('BOT ON'), callback_data='on')],
        [InlineKeyboardButton(_('BOT OFF'), callback_data='off')],
        [InlineKeyboardButton(_('❌ Cancel'), callback_data='back')],
    ])


def create_ban_list_keyboard(trans):
    _ = trans
    main_button_list = [
        [InlineKeyboardButton(_('🔥 View ban list'),
                              callback_data='bot_ban_list_view')],
        [InlineKeyboardButton(_('➖ Remove from ban list'),
                              callback_data='bot_ban_list_remove')],
        [InlineKeyboardButton(_('➕ Add to ban list'),
                              callback_data='bot_ban_list_add')],
        [InlineKeyboardButton(_('↩ Back'),
                              callback_data='bot_ban_list_back')],
    ]

    return InlineKeyboardMarkup(main_button_list)


def general_select_keyboard(trans, objects, cmd_prefix= '', page_num=1, page_len=50):
    _ = trans
    buttons = []
    prev_page = None
    next_page = None
    if len(objects) > 50:
        max_pages = math.ceil(len(objects) / float(page_len))
        objects = objects[(page_num - 1) * page_len: (page_num - 1) * page_len]
        prev_page = page_num - 1 if page_num > 1 else None
        next_page = page_num + 1 if page_num < max_pages else None
    for name, id, is_picked in objects:
        if is_picked:
            is_picked = '➖'
        else:
            is_picked = '➕'
        callback_data = 'select|{}'.format(id)
        name = '{} {}'.format(is_picked, name)
        button = [InlineKeyboardButton(name, callback_data=callback_data)]
        buttons.append(button)
    if prev_page:
        callback_data = 'page|{}'.format(prev_page)
        button = [InlineKeyboardButton(_('◀️ Previous'), callback_data=callback_data)]
        buttons.append(button)
    if next_page:
        callback_data = 'page|{}'.format(next_page)
        button = [InlineKeyboardButton(_('▶️ Next'), callback_data=callback_data)]
        buttons.append(button)
    back_btn = [InlineKeyboardButton(_('Done'), callback_data='done|')]
    buttons.append(back_btn)
    return InlineKeyboardMarkup(buttons)


def general_select_one_keyboard(trans, objects, page_num=1, page_len=50):
    _ = trans
    buttons = []
    prev_page = None
    next_page = None
    if len(objects) > 50:
        max_pages = math.ceil(len(objects) / float(page_len))
        objects = objects[(page_num - 1) * page_len: (page_num - 1) * page_len]
        prev_page = page_num - 1 if page_num > 1 else None
        next_page = page_num + 1 if page_num < max_pages else None
    for name, id in objects:
        callback_data = 'select|{}'.format(id)
        button = [InlineKeyboardButton(name, callback_data=callback_data)]
        buttons.append(button)
    if prev_page:
        callback_data = 'page|{}'.format(prev_page)
        button = [InlineKeyboardButton(_('◀️ Previous'), callback_data=callback_data)]
        buttons.append(button)
    if next_page:
        callback_data = 'page|{}'.format(next_page)
        button = [InlineKeyboardButton(_('▶️ Next'), callback_data=callback_data)]
        buttons.append(button)
    back_btn = [InlineKeyboardButton(_('↩ Back'), callback_data='back|')]
    buttons.append(back_btn)
    return InlineKeyboardMarkup(buttons)


def create_courier_locations_keyboard(trans, locations):
    _ = trans
    main_button_list = []
    for location_name, location_id, is_picked in locations:
        if is_picked:
            is_picked = '➖'
        else:
            is_picked = '➕'

        location_callback = location_id
        location_name = '{} {}'.format(is_picked, location_name)
        main_button_list.append(
            [
                InlineKeyboardButton(
                    location_name,
                    callback_data=location_callback)
            ]
        )
    main_button_list.append(
        [
            InlineKeyboardButton(
                _('Done'),
                callback_data='location_end')
        ]
    )

    return InlineKeyboardMarkup(main_button_list)


def couriers_choose_keyboard(couriers, order_id, message_id):
    couriers_list = []
    for courier in couriers:
        if hasattr(courier.location, 'title'):
            couriers_list.append([InlineKeyboardButton('@{}, from {}'.format(courier.username, courier.location.title),
                                                       callback_data='sendto|{}|{}|{}'.format(courier.telegram_id,
                                                                                              order_id, message_id))])
        else:
            couriers_list.append([InlineKeyboardButton('@{}'.format(courier.username),
                                                       callback_data='sendto|{}|{}|{}'.format(courier.telegram_id,
                                                                                              order_id, message_id))])
    return InlineKeyboardMarkup(couriers_list)


def create_service_channel_keyboard(trans, order_id):
    _ = trans
    main_button_list = [
        [InlineKeyboardButton(_('🛵 Send order to courier channel'),
                              callback_data='order_send_to_couriers|{}'.format(order_id))],
        [InlineKeyboardButton(_('🚀 Send order to specific courier'),
                              callback_data='order_send_to_specific_courier|{}'.format(order_id))],
        [InlineKeyboardButton(_('🚕 Send order yourself'),
                              callback_data='order_send_to_self|{}'.format(order_id))],
        [InlineKeyboardButton(_('⭐ Add user to VIP'),
                              callback_data='order_add_to_vip|{}'.format(order_id))],
        [InlineKeyboardButton(_('🔥 Add client to ban-list'),
                              callback_data='order_ban_client|{}'.format(order_id))],
        [InlineKeyboardButton(_('✅ Order Finished'),
                              callback_data='order_finished|{}'.format(order_id))],
        [InlineKeyboardButton(_('💳 Hide Order'),
                              callback_data='order_hide|{}'.format(order_id))],
    ]
    return InlineKeyboardMarkup(main_button_list)


def create_show_order_keyboard(trans, order_id):
    _ = trans
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(_('💳 Show Order'),
                             callback_data='order_show|{}'.format(order_id))
    ]])


def create_courier_order_status_keyboard(trans, order_id):
    _ = trans
    buttons = [
        [InlineKeyboardButton(_('✅ Order Done'), callback_data='confirm_courier_order_delivered|{}'.format(order_id))],
        [InlineKeyboardButton(_('🔥 Report client to admin'), callback_data='confirm_courier_report_client|{}'.format(order_id))],
        [InlineKeyboardButton(_('📞 Ping Client'), callback_data='ping_client|{}'.format(order_id))],
        [InlineKeyboardButton(_('❌ Drop responsibility'), callback_data='dropped|{}'.format(order_id))]
    ]
    return InlineKeyboardMarkup(buttons)


def create_admin_order_status_keyboard(trans, order_id):
    _ = trans
    buttons = [
        [InlineKeyboardButton(_('✅ Order Done'), callback_data='confirm_courier_order_delivered|{}'.format(order_id))],
        [InlineKeyboardButton(_('📞 Ping Client'), callback_data='ping_client|{}'.format(order_id))],
        [InlineKeyboardButton(_('❌ Drop responsibility'), callback_data='admin_dropped|{}'.format(order_id))]
    ]
    return InlineKeyboardMarkup(buttons)


def create_are_you_sure_keyboard(trans, callback_mapping):
    _ = trans
    buttons = [
        InlineKeyboardButton(_('✅ Yes'), callback_data=callback_mapping['yes']),
        InlineKeyboardButton(_('❌ No'), callback_data=callback_mapping['no'])
    ]
    return InlineKeyboardMarkup([buttons])


def create_edit_identification_keyboard(trans, values):
    _ = trans
    stage_one_text, stage_two_text = (_('✅ Enabled') if val else _('❌ Disabled') for val in values)
    stage_one_text = _('First stage ID image: {}').format(stage_one_text)
    stage_two_text = _('Second stage FB image: {}').format(stage_two_text)
    buttons = [
        [InlineKeyboardButton(stage_one_text, callback_data='stage_one')],
        [InlineKeyboardButton(stage_two_text, callback_data='stage_two')],
        [InlineKeyboardButton(_('Save'), callback_data='save')]
    ]
    return InlineKeyboardMarkup(buttons)

def create_edit_restriction_keyboard(trans, values):
    _ = trans
    first, second = (_('✅ Enabled') if val else _('❌ Disabled') for val in values)
    first_text = _('Only for customers option: {}').format(first)
    second_text = _('Vip customers option: {}').format(second)
    buttons = [
        [InlineKeyboardButton(first_text, callback_data='first')],
        [InlineKeyboardButton(second_text, callback_data='second')],
        [InlineKeyboardButton(_('Save'), callback_data='save')]
    ]
    return InlineKeyboardMarkup(buttons)

