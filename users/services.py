"""Сервисные функции для взаимодействия с платёжным сервисом Stripe."""

import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_product(name):
    """Создаёт продукт: https://stripe.com/docs/api/products/create."""
    return stripe.Product.create(name=name)


def create_price(product_id, amount):
    """Создаёт цену для продукта: https://stripe.com/docs/api/prices/create.

    amount — в основных единицах (рубли/доллары), Stripe принимает минорные (×100).
    """
    return stripe.Price.create(
        product=product_id,
        unit_amount=int(amount * 100),
        currency=settings.STRIPE_CURRENCY,
    )


def create_checkout_session(price_id):
    """Создаёт Checkout-сессию: https://stripe.com/docs/api/checkout/sessions/create.

    Возвращает объект с полями id (id сессии) и url (ссылка на оплату).
    """
    return stripe.checkout.Session.create(
        success_url=settings.STRIPE_SUCCESS_URL,
        cancel_url=settings.STRIPE_CANCEL_URL,
        line_items=[{'price': price_id, 'quantity': 1}],
        mode='payment',
    )


def retrieve_session(session_id):
    """Возвращает данные сессии: https://stripe.com/docs/api/checkout/sessions/retrieve."""
    return stripe.checkout.Session.retrieve(session_id)
