# type:ignore
from django.db.models import QuerySet
from django.shortcuts import redirect
from django.urls import reverse
from django_unicorn.components import UnicornView

from tenant.models import ShopTemplate, Tenant


class SettingsView(UnicornView):
    template_name = "backoffice/settings.html"

    tabs = ["template", "shop"]

    shop_templates: QuerySet[ShopTemplate, ShopTemplate] = []
    my_template = None
    selected_template = None

    def mount(self):
        if not self.request.user.is_authenticated:
            return redirect(reverse("backoffice:login-tenant"))

        self.shop_templates = ShopTemplate.objects.all()
        self.my_template = self.request.tenant.shop_template
        self.selected_template = self.my_template
        return None

    def save_template(self, template_id):
        tenant = Tenant.objects.get(id=self.request.tenant.id)
        shop_template = ShopTemplate.objects.get(id=template_id)
        tenant.shop_template = shop_template
        tenant.save()

    class Meta:
        js_exclude = ["login_url"]
