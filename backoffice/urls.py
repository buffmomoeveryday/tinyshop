# type:ignore
from django.urls import path

from backoffice.components.customer_detail import CustomerDetailView
from backoffice.components.customers import CustomersView
from backoffice.components.login import LoginView
from backoffice.components.product import ProductView

from . import views
from ._views import product, reports

# from backoffice.components.product_detail import ProductDetailView
# from backoffice.components.productadd import ProductaddView
# from backoffice.components.tenant_settings import SettingsView


app_name = "backoffice"  # noqa: F811

urlpatterns = [
    path("login/", LoginView.as_view(), name="login-tenant"),
    path("logout/", views.logout_user, name="logout-tenant"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("chat/", views.chat_with_database, name="chat-with-database"),
    path("orders/", views.orders, name="orders-tenant"),
    path("customers/", CustomersView.as_view(), name="customers-tenant"),
    path(
        "customers/<int:id>/",
        CustomerDetailView.as_view(),
        name="customers-details-tenant",
    ),
    path("settings/", views.tenant_settings, name="settings-tenant"),
]


product_urls = [
    path("products/add", product.products_add, name="product-add-tenant"),
    path(
        "product/<int:product_id>/detail",
        product.product_detail,
        name="product-detail-tenant",
    ),
    path(
        "products/",
        ProductView.as_view(),
        name="products-tenant",
    ),
    path(
        "htmx/product/<int:product_id>/add-variant",
        product.htmx_product_variant_add,
        name="htmx_product_add_variant",
    ),
    path(
        "htmx/product/remove-variant/<int:variant_id>",
        product.htmx_product_variant_remove,
        name="htmx_product_remove_variant",
    ),
    path(
        "htmx/product/edit-variant/<int:variant_id>",
        product.htmx_product_variant_edit,
        name="htmx_product_edit_variant",
    ),
    path(
        "htmx/brand/add",
        product.htmx_add_brand,
        name="add-brand",
    ),
    path(
        "htmx/category/add",
        product.htmx_add_category,
        name="add-category",
    ),
    path(
        "htmx/product/info/<int:product_id>",
        product.htmx_product_edit,
        name="htmx-product-edit",
    ),
]

payment_urls = [
    path(
        "subscription-payment",
        views.subscription_payment,
        name="payment",
    ),
    path(
        "subscription-payment/confirmed",
        views.payment_confirmed,
        name="payment-confirmed",
    ),
    path(
        "subscription-payment/cancelled",
        views.payment_cancelled,
        name="payment-cancelled",
    ),
]


heartbeat = [
    path("online", views.get_online_browser_count, name="online"),
]


reports = [
    path("reports/", reports.reports, name="reports"),
    path("reports/api/", reports.reports_api, name="reports_api"),
]

urlpatterns += product_urls
urlpatterns += payment_urls
urlpatterns += heartbeat
urlpatterns += reports
