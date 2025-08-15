# type:ignore

import json
import logging
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import stripe
from django.conf import settings as djsettings
from django.contrib import messages
from django.contrib.auth import logout
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django_tenants.utils import tenant_context
from stripe.error import APIConnectionError, AuthenticationError, StripeError

from backoffice.models import PaymentSettlement, Stripe
from core.enums import StripeEvents
from shop.models import (
    Address,
    Cart,
    Customer,
    Order,
    OrderItem,
    OrderStatusChoices,
    ProductVariant,
)
from tenant.decorators import tenant_login_required
from tenant.models import ShopTemplate, Tenant

logger = logging.getLogger(__name__)


##################
# Authentication
##################
def login_tenant(request: HttpRequest):
    return render(request=request, template_name="backoffice/login.html")


def logout_user(request: HttpRequest):
    logout(request=request)
    print("user-logout")
    return redirect(reverse("login-tenant"))


##################
# Authentication
##################
@tenant_login_required
def dashboard(request):
    # === Basic Stats ===
    total_customers = Customer.objects.count()
    verified_customers = Customer.objects.filter(is_verified=True).count()
    total_orders = Order.objects.count()
    paid_orders = Order.objects.filter(payment_status="paid").count()

    total_revenue = (
        Order.objects.filter(payment_status="paid").aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )
    total_revenue = round(total_revenue, 2)

    total_products = ProductVariant.objects.values("product").distinct().count()
    low_stock = ProductVariant.objects.filter(stock_quantity__lte=5).count()
    total_stock_units = (
        ProductVariant.objects.aggregate(total=Sum("stock_quantity"))["total"] or 0
    )
    out_of_stock = ProductVariant.objects.filter(stock_quantity=0).count()

    # === Order Status Chart ===
    order_status_counts = Order.objects.values("status").annotate(count=Count("id"))
    order_status_labels = [o["status"].title() for o in order_status_counts]
    order_status_data = [o["count"] for o in order_status_counts]

    # === Revenue Over Time (Last 6 Months) ===
    today = timezone.now().date()
    six_months_ago = today - timedelta(days=180)

    monthly_revenue = (
        Order.objects.filter(
            payment_status="paid", created_at__date__gte=six_months_ago
        )
        .annotate(month=TruncMonth("created_at"))  # ✅ PostgreSQL-safe
        .values("month")
        .annotate(total=Sum("total_amount"))
        .order_by("month")
    )

    # Build dictionary: "YYYY-MM" → revenue
    revenue_dict = {
        item["month"].strftime("%Y-%m"): float(item["total"])
        for item in monthly_revenue
    }

    # Generate all months from six_months_ago to today
    revenue_labels = []
    revenue_values = []
    current = six_months_ago

    while current <= today:
        month_str = current.strftime("%Y-%m")
        revenue_labels.append(month_str)
        revenue_values.append(revenue_dict.get(month_str, 0))

        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    # === Top Selling Products ===
    top_products = (
        OrderItem.objects.values("product_name_snapshot")
        .annotate(
            units_sold=Sum("quantity"),
            price=F("price_at_purchase"),
        )
        .order_by("-units_sold")[:5]
    )

    # Add placeholder category (enhance later if needed)
    for item in top_products:
        item["category"] = "General"

    # === Trial Days Left ===
    remaining_days = 0
    if hasattr(request, "tenant") and request.tenant:
        if hasattr(request.tenant, "trial_end_date") and request.tenant.trial_end_date:
            remaining_days = (request.tenant.trial_end_date.date() - today).days
        elif (
            hasattr(request.tenant, "subscription_end_date")
            and request.tenant.subscription_end_date
        ):
            remaining_days = (request.tenant.subscription_end_date.date() - today).days

    # Prepare context with JSON-serialized data for charts
    context = {
        "total_customers": total_customers,
        "verified_customers": verified_customers,
        "total_orders": total_orders,
        "paid_orders": paid_orders,
        "total_revenue": total_revenue,
        "products_in_stock": total_stock_units,
        "low_stock": low_stock,
        # Charts
        "order_status_labels": json.dumps(order_status_labels),
        "order_status_data": json.dumps(order_status_data),
        "revenue_labels": json.dumps(revenue_labels),
        "revenue_data": json.dumps(revenue_values),
        # Top Products
        "top_products": top_products,
        # Trial Info
        "remaining_days": max(remaining_days, 0),
    }

    return render(request, "backoffice/dashboard/dashboard.html", context)


@tenant_login_required
def orders(request: HttpRequest):
    if request.method == "GET":
        search_query = request.GET.get("search", "").strip()

        qs = Order.objects.select_related("customer").all()

        if search_query:
            qs = qs.filter(
                Q(pk__icontains=search_query)
                | Q(customer__username__icontains=search_query)
                | Q(customer__email__icontains=search_query)
            )

        month_start = now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        orders_this_month = Order.objects.filter(order_date__gte=month_start)

        total_orders = orders_this_month.count()
        pending_count = orders_this_month.filter(
            status=OrderStatusChoices.PENDING
        ).count()
        shipped_count = orders_this_month.filter(
            status=OrderStatusChoices.SHIPPED
        ).count()
        delivered_count = orders_this_month.filter(
            status=OrderStatusChoices.DELIVERED
        ).count()

        context = {
            "orders": qs.order_by("-order_date"),
            "stats": {
                "total_orders": total_orders,
                "pending": pending_count,
                "shipped": shipped_count,
                "delivered": delivered_count,
            },
            "search_query": search_query,
            "order_status": OrderStatusChoices.choices,
        }
        return render(request, "backoffice/orders.html", context)

    if request.method == "POST":
        headers = request.headers.get("Action")

        if headers == "Filter":
            status = request.POST.get("status_filter")
            if status:
                return render(
                    request=request,
                    template_name="backoffice/orders.html",
                    context={
                        "orders": Order.objects.filter(status=status.lower()),
                        "order_status": OrderStatusChoices.choices,
                    },
                )
            else:
                return render(
                    request=request,
                    template_name="backoffice/orders.html",
                    context={
                        "orders": Order.objects.all(),
                        "order_status": OrderStatusChoices.choices,
                    },
                )

        if headers == "ChangeStatus":
            order_id = request.POST.get("order_id")
            status = request.POST.get("change_status")

            order = Order.objects.get(pk=order_id)
            order.status = status
            order.save()
            messages.success(request=request, message="Success")
            return render(
                request=request,
                template_name="backoffice/orders.html",
                context={
                    "orders": Order.objects.all(),
                    "order_status": OrderStatusChoices.choices,
                },
            )


@tenant_login_required
def customers(request: HttpRequest):
    # All customers
    customer_qs = Customer.objects.all()

    # Calculate stats
    total_customers = customer_qs.count()
    start_of_month = timezone.now().replace(day=1)
    new_customers_count = customer_qs.filter(created_at__gte=start_of_month).count()
    active_customers_count = (
        customer_qs.filter(orders__created_at__gte=timezone.now() - timedelta(days=30))
        .distinct()
        .count()
    )

    context = {
        "customers": customer_qs,
        "total_customers": total_customers,
        "active_customers": active_customers_count,
        "new_customers_this_month": new_customers_count,
    }
    return render(request, "backoffice/customers.html", context)


##################
# Stripe and Payments
##################
@tenant_login_required
def payment_for_extended(request):
    return render(request, "backoffice/payment.html", context={})


@csrf_exempt
@tenant_login_required
def subscription_payment(request):
    stripe.api_key = djsettings.STRIPE_SECRET_KEY
    print(request.tenant.id)
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "npr",
                    "product_data": {"name": "Subscription"},
                    "unit_amount": 100_000,
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=f"http://{request.tenant}.localhost:8000/backoffice/subscription-payment/confirmed",
        cancel_url=f"http://{request.tenant}.localhost:8000/backoffice/subscription-payment/cancelled",
        metadata={
            "tenant_id": str(request.tenant.id),
            "user_id": str(request.user.id),
            "plan": "pro_monthly",
            "event": StripeEvents.TINYSHOP_SUBSCRIPTION.value,
        },
    )
    return redirect(session.url, code=303)


# webhook
@csrf_exempt
def stripe_webhook(request):
    logger.info("Received Stripe webhook.")

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    webhook_secret = djsettings.STRIPE_WEBHOOK_SECRET

    if not sig_header:
        logger.warning("Missing Stripe signature header.")
        return HttpResponse(status=400)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        logger.info(f"Webhook event constructed: {event['type']}")
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Signature verification failed: {e}")
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        logger.info("Processing checkout.session.completed event.")
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        total_cents = session.get("amount_total")

        tenant_id = metadata.get("tenant_id")
        customer_event = metadata.get("event")
        using_tinyshop_stripe = metadata.get("using_tinyshop_stripe")

        logger.debug(f"Metadata received: {metadata}")

        if customer_event == StripeEvents.CUSTOMER_CHECKOUT.value:
            logger.info("Processing customer checkout.")
            tenant = Tenant.objects.get(id=tenant_id)
            customer_id = metadata.get("customer_id")
            try:
                with tenant_context(tenant):
                    cart = Cart.objects.filter(user__id=customer_id).first()
                    if not cart:
                        logger.warning(f"No cart found for user {customer_id}")
                        return HttpResponse(status=400)

                    from shop.models import (
                        OrderStatusChoices,
                        PaymentMethodChoices,
                        PaymentStatusChoices,
                    )

                with transaction.atomic():
                    if using_tinyshop_stripe:
                        with tenant_context(tenant):
                            customer = Customer.objects.get(id=customer_id)
                            settlement = PaymentSettlement(
                                amount=Decimal(total_cents) / 100,
                                transaction_date=date.today(),
                                user_id=customer.id,
                            )
                            settlement.save()
                            logger.info(
                                f"PaymentSettlement created for user {customer_id}"
                            )
                            address = Address.objects.get(
                                is_default=True,
                                user=customer,
                            )
                            order = Order.objects.create(
                                customer=Customer.objects.get(id=customer_id),
                                payment_status=PaymentStatusChoices.PAID,
                                status=OrderStatusChoices.PENDING,
                                total_amount=cart.get_cart_total(),
                                shipping_cost=Decimal("0.00"),
                                discount_amount=Decimal("0.00"),
                                transaction_id=session.get("payment_intent"),
                                payment_method=PaymentMethodChoices.STRIPE,
                                address=address,
                            )
                            logger.info(
                                f"Order {order.id} created for user {customer_id}"
                            )

                            for item in cart.items.all():
                                product = item.product
                                variant = item.product_variant
                                price = (
                                    variant.get_price() if variant else product.price
                                )

                                OrderItem.objects.create(
                                    order=order,
                                    product=product,
                                    product_variant=variant,
                                    quantity=item.quantity,
                                    price_at_purchase=price,
                                    product_name_snapshot=product.name,
                                    variant_details_snapshot=str(variant)
                                    if variant
                                    else "",
                                    sku_snapshot=variant.sku
                                    if variant and hasattr(variant, "sku")
                                    else "",
                                )

                            cart.delete()
                            logger.info(f"Order items created for order {order.id}")
            except Exception as e:
                import traceback

                print(traceback.format_exc())
                logger.exception(f"Error processing customer checkout: {e}")
                return HttpResponse(status=500)

        if customer_event == StripeEvents.TINYSHOP_SUBSCRIPTION.value:
            logger.info("Processing tinyshop subscription.")
            tenant = Tenant.objects.get(id=tenant_id)
            tenant.paid_until = date.today() + timedelta(days=30)
            tenant.on_trial = False
            tenant.save()
            print(tenant.paid_until)
        # except Tenant.DoesNotExist:
        #     import traceback

        #     print(traceback.format_exc())
        #     logger.warning(f"Tenant with ID {tenant_id} not found.")
        # except Exception as e:
        # import traceback
    #
    # print(traceback.format_exc())
    #
    # logger.exception(
    # f"Error updating subscription for tenant {tenant_id}: {e}"
    # )
    # return HttpResponse(status=500)

    return HttpResponse("completed")


@csrf_exempt
def payment_confirmed(request):
    return redirect(reverse("backoffice:dashboard"))


@csrf_exempt
def payment_cancelled(request):
    return redirect(reverse("backoffice:dashboard"))


################
# Settings
################
@tenant_login_required
def tenant_settings(request):
    headers = request.headers.get("Action")

    if request.method == "POST":
        if headers == "settings_change":
            template_id = request.POST.get("selected_template")
            tenant: Tenant = request.tenant
            shop_templates = ShopTemplate.objects.all()

            if template_id:
                selected_template_obj = get_object_or_404(ShopTemplate, id=template_id)
                tenant.shop_template = selected_template_obj
                tenant.save()
                selected_template = selected_template_obj

            return render(
                request,
                "backoffice/components/settings/template_selection.html",
                {
                    "shop_templates": shop_templates,
                    "selected_template": selected_template,
                    "my_template": selected_template.name
                    if selected_template
                    else None,
                },
            )

        if headers == "stripe_api_key":
            import stripe

            stripe_public_key = request.POST.get("stripe_public_key")
            stripe_secret_key = request.POST.get("stripe_secret_key")

            stripe.api_key = stripe_secret_key
            try:
                stripe.Account.retrieve()
            except AuthenticationError:
                return render(
                    request=request,
                    template_name="backoffice/components/settings/stripe_setup.html",
                    context={
                        "stripe_public_key": stripe_public_key,
                        "stripe_secret_key": stripe_secret_key,
                        "error": "Invalid Stripe Secret Key. Please check and try again.",
                    },
                )
            except (APIConnectionError, StripeError) as _:
                return render(
                    request=request,
                    template_name="backoffice/components/settings/stripe_setup.html",
                    context={
                        "stripe_public_key": stripe_public_key,
                        "stripe_secret_key": stripe_secret_key,
                        "error": "Some Unexpected Errr",
                    },
                )

            Stripe.objects.first().delete()
            stripe_obj = Stripe.objects.create(
                STRIPE_PUBLIC_KEY=stripe_public_key,
                STRIPE_SECRET_KEY=stripe_secret_key,
            )

            return render(
                request=request,
                template_name="backoffice/components/settings/stripe_setup.html",
                context={
                    "stripe_public_key": stripe_public_key,
                    "stripe_secret_key": stripe_secret_key,
                    "success": "Stripe keys saved successfully.",
                },
            )

    if request.method == "GET":
        shop_templates = ShopTemplate.objects.all()
        selected_template = request.tenant.shop_template

        stripe_obj = Stripe.objects.first()
        stripe_public_key = stripe_obj.STRIPE_PUBLIC_KEY if stripe_obj else None
        stripe_secret_key = stripe_obj.STRsIPE_SECRET_KEY if stripe_obj else None

        return render(
            request=request,
            template_name="backoffice/settings.html",
            context={
                # setting template
                "shop_templates": shop_templates,
                "selected_template": selected_template,
                "my_template": selected_template.name if selected_template else None,
                # stripe
                "stripe_public_key": stripe_public_key if stripe_public_key else None,
                "stripe_secret_key": stripe_secret_key if stripe_secret_key else None,
            },
        )


#############
# HEART BEAT
#############
def get_online_browser_count(request):
    active_browsers = set()
    online_browsers = cache.get("online_browsers_list", [])

    for browser_id in online_browsers:
        if cache.get(f"browser_{browser_id}"):
            active_browsers.add(browser_id)

    if len(active_browsers) != len(online_browsers):
        cache.set("online_browsers_list", list(active_browsers), timeout=None)

    return HttpResponse(len(active_browsers))


############
# ai
############
from shop.models import ChatMessage


def chat_with_database(request):
    headers = request.headers.get("Action")
    from shop.sql_utils import process_nl_query_for_tenant

    messages = ChatMessage.objects.all()

    if request.method == "POST":
        query = request.POST.get("nl_query")
        response = process_nl_query_for_tenant(query, request.tenant)

        ChatMessage.objects.create(
            incomming_message=query,
            outgoing_message=response,
            explanation=response.get("explanation"),
        )

        return render(
            request,
            "backoffice/chat/chat_component.html",
            {
                "chat_messages": ChatMessage.objects.all(),
            },
        )

    return render(
        request,
        "backoffice/chat/chat.html",
        {
            "chat_messages": messages,
        },
    )
