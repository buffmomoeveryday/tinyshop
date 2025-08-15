from django.utils import timezone
from django_unicorn.components import UnicornView

from shop.models import Customer
from tenant.decorators import TenantLoginRequiredMixin


class CustomersView(TenantLoginRequiredMixin, UnicornView):
    template_name = "backoffice/customers.html"
    customers = []
    new_customers_this_month: int = 0

    def mount(self, *args, **kwargs):
        self.customers = Customer.objects.all()

        now = timezone.now()

        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start_of_month.month == 12:
            start_of_next_month = start_of_month.replace(
                year=start_of_month.year + 1, month=1
            )
        else:
            start_of_next_month = start_of_month.replace(month=start_of_month.month + 1)
        self.new_customers_this_month = Customer.objects.filter(
            created_at__gte=start_of_month, created_at__lt=start_of_next_month
        ).count()
