from datetime import timedelta

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django_htmx.http import HttpResponseClientRefresh

from shop.models import Customer, CustomerEvent
from tenant.decorators import tenant_login_required


@tenant_login_required
def customers_view(request: HttpRequest):
    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    customer_qs = Customer.objects.all()

    if start_of_month.month == 12:
        start_of_next_month = start_of_month.replace(
            year=start_of_month.year + 1,
            month=1,
        )
    else:
        start_of_next_month = start_of_month.replace(month=start_of_month.month + 1)

    new_customers_this_month = customer_qs.filter(
        created_at__gte=start_of_month,
        created_at__lt=start_of_next_month,
    ).count()

    active_customers_count = (
        customer_qs.filter(
            orders__created_at__gte=timezone.now() - timedelta(days=30),
        )
        .distinct()
        .count()
    )

    return render(
        request=request,
        template_name="backoffice/customers/customers.html",
        context={
            "customers": customer_qs,
            "total_customers": customer_qs.count,
            "new_customers_this_month": new_customers_this_month,
            "active_customers_count": active_customers_count,
        },
    )


@tenant_login_required
def customer_detail_view(request: HttpRequest, customer_id: int):
    customer = Customer.objects.prefetch_related(
        "orders",
        "addresses",
        "orders__items",
        "orders__items__product",
    ).get(pk=customer_id)

    total_orders = customer.get_total_orders()
    total_spent = customer.get_total()

    recent_orders = customer.orders.all()[:5]

    recent_events = CustomerEvent.objects.filter(
        customer=customer,
    ).exclude(path__in=["/heartbeat", "/htmx/cart/count/", "/favicon.ico"])[:10]

    return render(
        request,
        "backoffice/customers/customer_detail.html",
        {
            "customer": customer,
            "total_orders": total_orders,
            "total_spent": total_spent,
            "recent_orders": recent_orders,
            "recent_events": recent_events,
            "addresses": customer.addresses.all(),
        },
    )


@tenant_login_required
def htmx_customer_block(request: HttpRequest, customer_id: int):
    if request.method == "POST":
        customer = get_object_or_404(Customer, pk=customer_id)
        if customer.block:
            customer.block = False
        else:
            customer.block = True

        customer.save()
        return HttpResponseClientRefresh()

    return HttpResponse("")
