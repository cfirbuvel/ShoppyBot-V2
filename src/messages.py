from .helpers import get_trans, calculate_discount_total, config


def create_product_description(user_id, product_title, product_prices, product_count,
                               subtotal, delivery_min, delivery_fee):
    _ = get_trans(user_id)
    text = _('Product:\n{}').format(product_title)
    text += '\n\n'
    text += '〰️'
    text += '\n'
    if delivery_fee > 0 and delivery_min > 0:
        text += _('Delivery Fee: {}$').format(delivery_fee)
        text += '\n'
        text += _('for orders below {}$').format(delivery_min)
        text += '\n'
        text += '〰️'
    else:
        text += _('Delivery Fee: {}$').format(delivery_fee)
        text += '\n'
    text += '\n'
    text += _('Price:')
    text += '\n'

    for q, price in product_prices:
        text += '\n'
        text += _('x {} = ${}').format(q, int(price))

    q = product_count
    if q > 0:
        text += '\n\n〰️\n\n'
        text += _('Count: {}').format(q)
        text += '\n'
        text += _('Subtotal: ${}').format(int(subtotal))
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
        text += _('x {} = ${}').format(q, price)
    text += '\n\n~~\n'
    return text

def create_confirmation_text(user_id, is_pickup, shipping_data, total, delivery_min, delivery_cost,
                             delivery_for_vip, product_info):
    _ = get_trans(user_id)
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
        text += _('x {} = ${}').format(product_count, price)
        text += '\n'
    text += '〰〰〰〰〰〰〰〰〰〰〰〰️'

    is_vip = True if 'vip' in shipping_data else False

    discount = config.get_discount()
    discount_min = config.get_discount_min()
    if is_vip:
        if discount_min > 0 and total >= discount_min:
            text += '\n\n'
            if not discount.endswith('%'):
                discount_str = '{}$'.format(discount)
            else:
                discount_str = discount
            text += _('Discount: {}').format(discount_str)
            total = calculate_discount_total(discount, total)
            text += '\n\n'
            text += _('Total: ${}').format(total)
            return text
        else:
            text += '\n\n'
            text += _('Total: ${}').format(total)
            return text
    else:
        if total < delivery_min or delivery_min == 0:
            if not is_vip or delivery_for_vip:
                if not is_pickup:
                    total = total+delivery_cost
                    text += '\n\n'
                    text += _('Delivery Fee: {}$').format(delivery_cost)
                    text += '\n'
                    text += _('Total: ${}').format(total)
                else:
                    text += '\n\n'
                    text += _('Total: ${}').format(total)
        else:
            text += '\n\n'
            text += _('Total: ${}').format(total)
        return text


def create_service_notice(trans, is_pickup, order_id, username, product_info, shipping_data,
                          total, delivery_min, delivery_cost, delivery_for_vip):
    _ = trans
    text = _('Order №{} notice:').format(order_id)
    text += '\n\n'
    text += '〰〰〰〰〰〰〰〰〰〰〰〰️'
    text += '\n'
    text += _('Items in cart:')
    text += '\n'

    for title, product_count, price in product_info:
        text += '\n'
        text += _('Product:\n{}').format(title)
        text += '\n'
        text += _('x {} = ${}').format(product_count, price)
        text += '\n'

    is_vip = True if 'vip' in shipping_data else False

    discount = config.get_discount()
    discount_min = config.get_discount_min()
    if is_vip:
        if discount_min > 0 and total >= discount_min:
            text += '\n\n'
            if not discount.endswith('%'):
                discount_str = '{}$'.format(discount)
            else:
                discount_str = discount
            text += _('Discount: {}').format(discount_str)
            total = calculate_discount_total(discount, total)

    if total < delivery_min or delivery_min == 0:
        if not is_vip or delivery_for_vip:
            if not is_pickup:
                total = total + delivery_cost
                text += '\n\n'
                text += _('Delivery Fee: {}$').format(delivery_cost)
                text += '\n'
                text += _('Total: ${}').format(total)
            else:
                text += '\n\n'
                text += _('Total: ${}').format(total)
    else:
        text += '\n\n'
        text += _('Total: ${}').format(total)

    text += '\n'
    text += '〰〰〰〰〰〰〰〰〰〰〰〰️'
    text += '\n'
    text += _('Customer: @{}').format(username)
    text += '\n'
    text += _('Vip Customer') + '\n' if is_vip else ''
    text += '\n'
    text += _('Shipping details:')
    text += '\n'
    for key, value in shipping_data.items():

        if key == 'photo_question':
            text += _('Photo question: ')
            text += value
            text += '\n'
        if key == 'method':
            text += _('Pickup/Delivery: ')
            text += value
            text += '\n'
        if key == 'pickup_location':
            text += _('Pickup location: ')
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
