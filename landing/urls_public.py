from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from backoffice.views import stripe_webhook
from landing.components.login_tenant import LoginTenantView

from .views import landing_page, register_view

urlpatterns = [
    path("", landing_page, name="landing-page"),
    path("register/", register_view, name="register"),
    path("login/", LoginTenantView.as_view(), name="login-tenant"),
    path("admin/", admin.site.urls),
    path("stripe/webhook/", stripe_webhook, name="stripe-webhook"),  # type: ignore
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


urlpatterns += [
    path("unicorn/", include("django_unicorn.urls")),
]
