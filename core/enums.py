from enum import Enum


class StripeEvents(str, Enum):
    TINYSHOP_SUBSCRIPTION = "tinyshop_subscription"
    CUSTOMER_CHECKOUT = "customer_payment"
