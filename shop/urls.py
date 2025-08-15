from django.urls import path

from shop import views

app_name = "shop"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("login/", views.login_customer, name="login"),
    path("profile/", views.profile, name="profile"),
    path("register/", views.register_customer, name="register"),
    path("checkout/", views.stripe_checkout, name="checkout"),
    path("checkout/success", views.stripe_checkout_success, name="checkout-success"),
    path("checkout/cancel", views.stripe_checkout_cancel, name="checkout-success"),
]


products = [
    path("products/", views.products, name="products"),
    path("products/<int:product_id>", views.product_detail, name="product-detail"),
]

orders_urls = [
    path("cart", views.cart_detail, name="cart"),
    path("orders/<int:order_id>", views.order_detail, name="order-detail"),
    path("orders/", views.my_orders, name="my-orders"),
    path("cancel-order/<int:order_id>", views.cancel_order, name="cancel-order"),
]


htmx = [
    path(
        "htmx/cart/count/",
        views.htmx_get_cart,
        name="htmx-get-cart",
    ),
    path(
        "htmx/add-cart/<int:product_id>",
        views.htmx_add_to_cart,
        name="htmx-add-to-cart",
    ),
    path(
        "htmx/remove-cart-item/<int:cart_item_id>",
        views.htmx_remove_from_cart,
        name="htmx-remove-from-cart",
    ),
    path(
        "htmx/update-cart-item-count/<int:cart_item_id>",
        views.htmx_update_cart_item_count,
        name="htmx-update-cart-item-count",
    ),
]


heart_beat_url = [
    path("heartbeat", views.heartbeat, name="heartbeat"),
]


urlpatterns += htmx
urlpatterns += orders_urls
urlpatterns += products
urlpatterns += heart_beat_url
