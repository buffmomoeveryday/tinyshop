from enum import Enum


class EventType(Enum):
    SIGNUP = "signup"
    LOGIN = "login"
    PRODUCT_VIEW = "product_view"
    ADD_TO_CART = "add_to_cart"
    REMOVE_FROM_CART = "remove_from_cart"
    CHECKOUT_START = "checkout_start"
    PURCHASE = "purchase"
    SEARCH = "search"




# log_customer_event(customer, "product_view", {"product_id": product_id})

# | `event_type`       | metadata                   |
# | ------------------ | -------------------------- |
# | `signup`           | `{}`                       |
# | `login`            | `{}`                       |
# | `product_view`     | `{ "product_id": 123 }`    |
# | `add_to_cart`      | `{ "product_id": 123 }`    |
# | `remove_from_cart` | `{ "product_id": 123 }`    |
# | `checkout_start`   | `{ "cart_value": 199.99 }` |
# | `purchase`         | `{ "order_id": 456 }`      |
# | `search`           | `{ "query": "hoodie" }`    |
