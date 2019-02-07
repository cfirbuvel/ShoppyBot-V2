from .helpers import get_trans, calculate_discount_total, config, cart
from .models import Location


def create_cart_details_msg(user_id, products_info):
    _ = get_trans(user_id)
    msg = '▫️◾️◽️◼️◻️⬛️◻️◼️◽️◾️▫️'
    msg += '\n'
    msg += _('Products in cart:')
    msg += '\n\n'
    total = 0
    for title, count, price in products_info:
        msg += '{}:'.format(title)
        msg += '\n'
        msg += _('x {} = {}₪').format(count, price)
        msg += '\n\n'
        total += price
    msg += _('Total: {}₪').format(total)
    msg += '\n\n'
    msg += '▫️◾️◽️◼️◻️⬛️◻️◼️◽️◾️▫️'
    return msg


def create_product_description(user_id, product_title, product_prices, product_count,
                               subtotal):
    _ = get_trans(user_id)
    text = _('Product:\n{}').format(product_title)
    text += '\n\n'
    text += '〰️'
    text += '\n'
    delivery_fee = config.get_delivery_fee()
    delivery_min = config.get_delivery_min()
    if delivery_fee > 0 and delivery_min > 0:
        text += _('Delivery Fee: {}₪').format(delivery_fee)
        text += '\n'
        text += _('for orders below {}₪').format(delivery_min)
        text += '\n'
        text += '〰️'
        text += '\n'
    elif delivery_fee > 0:
        text += _('Delivery Fee: {}₪').format(delivery_fee)
        text += '\n'

    if Location.select().exists():
        for loc in Location.select():
            conf_delivery_fee = config.get_delivery_fee()
            if conf_delivery_fee == loc.delivery_fee:
                continue
            delivery_fee = loc.delivery_fee
            delivery_min = loc.delivery_min
            if delivery_fee:
                if delivery_fee > 0 and delivery_min > 0:
                    text += _('Delivery Fee from *{}*: {}₪').format(loc.title, delivery_fee)
                    text += '\n'
                    text += _('for orders below {}₪').format(delivery_min)
                    text += '\n'
                    text += '〰️'
                    text += '\n'
                else:
                    text += _('Delivery Fee from *{}*: {}₪').format(loc.title, delivery_fee)
                    text += '\n'
    text += '\n'
    text += _('Price:')
    text += '\n'

    for q, price in product_prices:
        text += '\n'
        text += _('x {} = {}₪').format(q, int(price))

    q = product_count
    if q > 0:
        text += '\n\n〰️\n\n'
        text += _('Count: {}').format(q)
        text += '\n'
        text += _('Subtotal: {}₪').format(int(subtotal))
        text += '\n'

    return text


def create_admin_product_description(trans, product_title, product_prices):
    _ = trans
    text = _('Product:\n{}'
             '\n\n'
             '~~'
             '\n'
             'Price:\n').format(product_title)
    for q, price in product_prices:
        text += '\n'
        text += _('x {} = {}₪').format(q, price)
    text += '\n\n~~\n'
    return text


def create_confirmation_text(user_id, is_pickup, shipping_data, total,
                             delivery_for_vip, product_info):
    _ = get_trans(user_id)
    active_delivery = False
    text = _('Please confirm your order:')
    text += '\n\n'
    text += '〰〰〰〰〰〰〰〰〰〰〰〰️'
    text += '\n'
    text += _('Items in cart:')
    text += '\n'

    for title, product_count, price in product_info:
        text += '\n'
        text += _('Product:\n{}').format(title)
        text += '\n'
        text += _('x {} = {}₪').format(product_count, price)
        text += '\n'
    text += '〰〰〰〰〰〰〰〰〰〰〰〰️'

    if 'vip' in shipping_data:
        if shipping_data['vip']:
            is_vip = True
        else:
            is_vip = False
    else:
        is_vip = False

    shipping_loc = shipping_data.get('pickup_location')
    try:
        shipping_loc = Location.get(title=shipping_loc)
    except Location.DoesNotExist:
        shipping_loc = None
    if shipping_loc and shipping_loc.delivery_fee is not None:
        delivery_fee, delivery_min = shipping_loc.delivery_fee, shipping_loc.delivery_min
    else:
        delivery_fee, delivery_min = config.get_delivery_fee(), config.get_delivery_min()
    if total < delivery_min or delivery_min == 0:
        if not is_vip or delivery_for_vip:
            if not is_pickup:
                active_delivery = True
                text += '\n'
                text += _('Delivery Fee: {}₪').format(delivery_fee)

    discount = config.get_discount()
    discount_min = config.get_discount_min()
    if discount_min != 0:
        if is_vip:
            discount_num = calculate_discount_total(discount, total)
            if discount_num and total >= discount_min:
                if not discount.endswith('%'):
                    text += '\n'
                    discount_str = '{}'.format(discount)
                    discount_str += _('₪')
                    total -= int(discount)
                else:
                    text += '\n'
                    discount_str = discount
                    total -= discount_num
                text += _('Discount: {}').format(discount_str)

    if active_delivery:
        total += delivery_fee

    text += '\n\n'
    text += _('Total: {}₪').format(total)
    return text


def create_service_notice(trans, is_pickup, order_id, username, product_info, shipping_data,
                          total, delivery_for_vip):
    _ = trans
    active_delivery = False
    text = _('Order №{} notice:').format(order_id)
    text += '\n'
    text += '〰〰〰〰〰〰〰〰〰〰〰〰️'
    text += '\n'
    text += _('Items in cart:')
    text += '\n'

    for title, product_count, price in product_info:
        text += '\n'
        text += _('Product:\n{}').format(title)
        text += '\n'
        text += _('x {} = {}₪').format(product_count, price)
        text += '\n'

    if 'vip' in shipping_data:
        if shipping_data['vip']:
            is_vip = True
        else:
            is_vip = False
    else:
        is_vip = False

    shipping_loc = shipping_data.get('pickup_location')
    try:
        shipping_loc = Location.get(title=shipping_loc)
    except Location.DoesNotExist:
        shipping_loc = None
    if shipping_loc and shipping_loc.delivery_fee is not None:
        delivery_fee, delivery_min = shipping_loc.delivery_fee, shipping_loc.delivery_min
    else:
        delivery_fee, delivery_min = config.get_delivery_fee(), config.get_delivery_min()

    if total < delivery_min or delivery_min == 0:
        if not is_vip or delivery_for_vip:
            if not is_pickup:
                active_delivery = True
                text += '\n'
                text += _('Delivery Fee: {}₪').format(delivery_fee)

    discount = config.get_discount()
    discount_min = config.get_discount_min()
    if discount_min != 0:
        if is_vip:
            discount_num = calculate_discount_total(discount, total)
            if discount_num and total >= discount_min:
                if not discount.endswith('%'):
                    text += '\n'
                    discount_str = '{}'.format(discount)
                    discount_str += _('₪')
                    total -= int(discount)
                else:
                    text += '\n'
                    discount_str = discount
                    total -= discount_num
                text += _('Discount: {}').format(discount_str)

    if active_delivery:
        total += delivery_fee

    text += '\n'
    text += _('Total: {}₪').format(total)

    text += '\n'
    text += '〰〰〰〰〰〰〰〰〰〰〰〰️'
    text += '\n'
    text += _('Customer: @{}').format(username)
    text += '\n'
    text += _('Vip Customer') + '\n' if is_vip else ''
    text += '\n'
    for key, value in shipping_data.items():

        if key == 'photo_question':
            text += _('Photo question: ')
            text += value
            text += '\n'
        if key == 'method':
            text += value
            text += '\n'
        if key == 'pickup_location':
            text += _('From location: ')
            text += value
            text += '\n'
        if key == 'location':
            text += _('Address: ')
            text += value
            text += '\n'
        if key == 'time':
            text += _('When: ')
            text += value
            text += '\n'
        if key == 'time_text':
            text += _('Time: ')
            text += value
            text += '\n'
        if key == 'phone_number':
            text += _('Phone number: ')
            text += value
            text += '\n'

    return text


def create_delivery_fee_msg(trans, location=None):
    _ = trans
    if location:
        location_string = _(' for {}').format(location.title)
        if location.delivery_fee is None:
            delivery_fee = config.get_delivery_fee()
            delivery_min = config.get_delivery_min()
        else:
            delivery_fee = location.delivery_fee
            delivery_min = location.delivery_min
    else:
        location_string = _(' for all locations')
        delivery_fee = config.get_delivery_fee()
        delivery_min = config.get_delivery_min()

    res = _('Enter delivery fee like:\n'
            '50 > 500: Deals below 500 will have delivery fee of 50\n'
            'or\n'
            '50: All deals will have delivery fee of 50\n'
            'Only works on delivery\n\n'
            'Current fee{}: {}>{}').format(location_string, delivery_fee, delivery_min)
    return res
