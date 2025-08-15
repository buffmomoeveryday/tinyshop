from django_unicorn.components import UnicornView

from shop.models import Customer


class CustomerDetailView(UnicornView):
    customer = None
    template_name = "backoffice/customer_detail.html"

    def mount(self, *args, **kwargs):
        id = self.kwargs.get("pk")
        try:
            self.customer = Customer.objects.get(id=id)
        except Customer.DoesNotExist as _:
            pass
