# type:ignore

import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import connection, transaction
from django.db.models import Count, F, Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.http.request import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django_tenants.urlresolvers import reverse_lazy

from accounts.authentication import CustomerBackend, customer_login
from accounts.decorators import customer_required
from shop.middlewares import log_customer_event
from shop.models import (
    Address,
    Brand,
    Cart,
    CartItem,
    Customer,
    Order,
    OrderItem,
    OrderStatusChoices,
    PaymentMethodChoices,
    PaymentStatusChoices,
    Product,
    ProductCategory,
    ProductVariant,
)


def landing(request: HttpRequest):
    """Landing page view that uses tenant-specific templates"""
    tenant = connection.tenant
    context = {
        "tenant": tenant,
        "tenant_name": tenant.name if tenant else "Default",
        "template_theme": tenant.get_template_slug() if tenant else "theme_1",
    }

    return render(
        request=request,
        template_name="landing.html",
        context=context,
    )


#########################
# login and registraion
#########################
def login_customer(request: HttpRequest):
    next_url = request.GET.get("next") or reverse_lazy("shop:landing")

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        if not all([email, password]):
            messages.error(request, "Both email and password are required.")
            return redirect(f"{reverse_lazy('shop:login')}?next={next_url}")

        backend = CustomerBackend()
        customer = backend.authenticate(request, email=email, password=password)

        if customer:
            customer_login(request, customer)
            return redirect(next_url)
        else:
            messages.error(request, "Invalid email or password.")
            return redirect(f"{reverse_lazy('shop:login')}?next={next_url}")

    return render(request, "auth/login.html", {"next": request.GET.get("next", "")})


def register_customer(request: HttpRequest):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        contact_number = request.POST.get("contact_number", None)
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if not password == confirm_password:
            messages.error(request, "Two Password doesn't match")
            return redirect(reverse_lazy("shop:register"))

        if not all([first_name, last_name, email, password]):
            messages.error(request, "All required fields should be filled up")
            return redirect(reverse_lazy("shop:register"))

        customer = Customer.objects.create(
            first_name=first_name,
            last_name=last_name,
            contact_number=contact_number,
            email=email,
            password=make_password(password),
            marketing_opt_in=True,
        )
        customer_login(request, customer)
        messages.success(request, "Registration Successful")
        return redirect(reverse_lazy("shop:landing"))

    context = {}
    return render(request, "auth/register.html", context)


#########################
# products
#########################


def products(request):
    # Start with a base queryset. We'll add filters to this.
    product_list = (
        Product.objects.all().prefetch_related("category").select_related("brand")
    )

    # --- Filtering Logic ---

    # Get filter parameters from the request
    search_query = request.GET.get("search")
    selected_categories = request.GET.getlist("category")
    selected_brands = request.GET.getlist("brand")
    min_price_str = request.GET.get("min_price")
    max_price_str = request.GET.get("max_price")

    # 1. Search filter
    if search_query:
        product_list = product_list.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    # 2. Category filter
    if selected_categories:
        product_list = product_list.filter(category__id__in=selected_categories)

    # 3. Brand filter
    if selected_brands:
        product_list = product_list.filter(brand__id__in=selected_brands)

    # 4. Price range filter
    min_price = (
        Decimal(min_price_str)
        if min_price_str and min_price_str.replace(".", "", 1).isdigit()
        else None
    )
    max_price = (
        Decimal(max_price_str)
        if max_price_str and max_price_str.replace(".", "", 1).isdigit()
        else None
    )

    if min_price is not None:
        product_list = product_list.filter(price__gte=min_price)
    if max_price is not None:
        product_list = product_list.filter(price__lte=max_price)

    # --- End of Filtering Logic ---

    # Get a list of all brands and categories for the sidebar.
    # It's good practice to get these after applying initial filters
    # so the counts reflect the products currently in the queryset.
    categories = ProductCategory.objects.annotate(
        product_count=Count("products")
    ).order_by("name")
    brands = Brand.objects.annotate(product_count=Count("products")).order_by("name")

    # Paginate the filtered queryset
    paginator = Paginator(product_list, 10)
    page = request.GET.get("page")

    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    return render(
        request=request,
        template_name="product/products.html",
        context={
            "products": products,
            "products_count": product_list.count(),
            "total_pages": paginator.num_pages,
            "categories": categories,
            "brands": brands,
            "selected_categories": [int(id) for id in selected_categories],
            "selected_brands": [int(id) for id in selected_brands],
            "min_price": min_price,
            "max_price": max_price,
            "search_query": search_query,
        },
    )


def product_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    product.main_image = product.images.filter(is_main=True).first()
    context = {"product": product}
    return render(
        request=request,
        template_name="product/product_detail.html",
        context=context,
    )


########################
# cart
########################


@customer_required
def cart_detail(request):
    print("helo")
    if request.customer:
        cart, created = Cart.objects.get_or_create(user=request.customer)
    related_products = Product.objects.order_by("-created_at")[:4]
    return render(
        request,
        "cart/cart.html",
        {
            "cart": cart,
            "related_products": related_products,
        },
    )


def htmx_remove_from_cart(request, cart_item_id):
    try:
        cart_item = CartItem.objects.get(id=cart_item_id)
        cart_item.delete()
    except CartItem.DoesNotExist:
        raise Http404("Cart item not found")

    cart = Cart.objects.get(user=request.customer)

    oob_content = f"""
        <span id="cart-total" class="text-2xl font-bold text-luxe-charcoal" hx-swap-oob="true">
            {cart.get_cart_total()}
        </span>
        <p id="cart-count" class="text-luxe-gray" hx-swap-oob="true">
            {cart.cart_count()} items
        </p>
        <span id="cart-sub-total" class="text-luxe-charcoal font-medium" hx-swap-oob="true">
            ${cart.get_cart_total()}
        </span>
    """

    main_content = render_to_string(
        template_name="components/cart/cart_content.html",
        context={"cart": cart},
        request=request,
    )

    response = HttpResponse(main_content + oob_content, content_type="text/html")
    response["HX-Trigger"] = "cartUpdated"
    return response


def htmx_update_cart_item_count(request, cart_item_id):
    cart_item = CartItem.objects.get(id=cart_item_id)

    if request.headers.get("Action") == "increment":
        cart_item.quantity += 1
        cart_item.save()
        cart_item.refresh_from_db()
        print(cart_item.quantity)

    if request.headers.get("Action") == "decrement":
        if cart_item.quantity > 0:
            cart_item.quantity -= 1
            cart_item.save()

    cart = Cart.objects.get(user=request.customer)

    oob_content = f"""
        <span id="cart-total" class="text-2xl font-bold text-luxe-charcoal" hx-swap-oob="true">
            {cart.get_cart_total()}
        </span>
        <p id="cart-count" class="text-luxe-gray" hx-swap-oob="true">
            {cart.cart_count()} items
        </p>
        <span id="cart-sub-total" class="text-luxe-charcoal font-medium" hx-swap-oob="true">
            ${cart.get_cart_total()}
        </span>
    """

    main_content = render_to_string(
        template_name="components/cart/cart_content.html",
        context={"cart": cart},
        request=request,
    )

    response = HttpResponse(main_content + oob_content, content_type="text/html")
    response["HX-Trigger"] = "cartUpdated"
    return response


def htmx_get_cart(request):
    cart = Cart.objects.filter(user=request.customer).first()
    print(cart)
    if cart:
        return HttpResponse(cart.cart_count())
    return HttpResponse(0)


def htmx_add_to_cart(request, product_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method.")

    print(request.POST)

    if request.customer:
        cart, _ = Cart.objects.get_or_create(user=request.customer)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key)

    product = get_object_or_404(Product, id=product_id)
    variant_id = request.POST.get("variant_id")
    product_variant = None

    try:
        quantity = int(request.POST.get("quantity", 1))
        if quantity < 1:
            quantity = 1
    except (ValueError, TypeError):
        quantity = 1

    if variant_id:
        product_variant = get_object_or_404(
            ProductVariant, id=variant_id, product=product
        )

    # 3. Use a transaction to safely add or update the cart item
    with transaction.atomic():
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            product_variant=product_variant,
            defaults={"quantity": quantity},
        )
        if not created:
            cart_item.quantity = F("quantity") + quantity
            cart_item.save()

    response = HttpResponse(
        render_to_string(
            "components/product/add_to_cart.html",
            context={
                "product": product,
                "request": request,
            },
        )
    )
    response["HX-Trigger"] = "cartUpdated"
    return response


########################
# order
########################


def my_orders(request):
    customer = request.customer
    orders = Order.objects.filter(customer=customer)
    return render(
        request=request,
        template_name="orders/orders.html",
        context={
            "orders": orders,
        },
    )


def order_detail(request, order_id):
    return render(
        request=request,
        template_name="orders/order_detail.html",
        context={
            "order": get_object_or_404(Order, pk=order_id),
        },
    )


def cancel_order(request, order_id):
    if request.method == "POST":
        order = Order.objects.get(pk=order_id, customer=request.customer)
        if order:
            order.status = OrderStatusChoices.CANCELLED
            order.save()
            messages.success(request=request, message="Order Cancelled")
        else:
            messages.error(request=request, message="")

    return redirect(reverse_lazy("shop:my-orders"))


########################
# profile
########################
def profile(request):
    action = request.headers.get("Action")

    if request.method == "POST" and action == "Update":
        address_type = request.POST.get("address_type")
        phone_number = request.POST.get("phone_number")
        address_line1 = request.POST.get("address_line1")
        address_line2 = request.POST.get("address_line2")
        city = request.POST.get("city")
        state = request.POST.get("state")
        postal_code = request.POST.get("postal_code")
        country = request.POST.get("country")
        is_default = request.POST.get("is_default")
        is_default = True if is_default == "on" else False

        address = Address()
        address.user_id = request.customer.id
        address.full_name = f"{request.customer.get_full_name}"
        address.phone_number = phone_number
        address.address_type = address_type
        address.address_line1 = address_line1
        address.address_line2 = address_line2 if address_line2 else None
        address.city = city
        address.state = state
        address.postal_code = postal_code
        address.country = country
        address.is_default = is_default
        address.save()
        response = redirect(reverse("shop:profile"))
        response["Hx-Refresh"] = True
        return redirect(response)

    if request.method == "POST":
        address_type = request.POST.get("address_type")
        phone_number = request.POST.get("phone_number")
        address_line1 = request.POST.get("address_line1")
        address_line2 = request.POST.get("address_line2")
        city = request.POST.get("city")
        state = request.POST.get("state")
        postal_code = request.POST.get("postal_code")
        country = request.POST.get("country")
        is_default = request.POST.get("is_default")
        is_default = True if is_default == "on" else False

        address = Address()
        address.user_id = request.customer.id
        address.full_name = f"{request.customer.get_full_name}"
        address.phone_number = phone_number
        address.address_type = address_type
        address.address_line1 = address_line1
        address.address_line2 = address_line2 if address_line2 else None
        address.city = city
        address.state = state
        address.postal_code = postal_code
        address.country = country
        address.is_default = is_default
        address.save()
        return redirect(to=reverse_lazy("shop:profile"))

    return render(request=request, template_name="profile/profile.html", context={})


########################
# stripe checkout
########################
def get_cart_for_request(request):
    """Returns the Cart instance for authenticated or anonymous user."""
    if request.user.is_authenticated:
        return getattr(request.user.customer, "cart", None)
    session_key = (
        request.session.session_key
        or request.session.save()
        or request.session.session_key
    )
    return Cart.objects.filter(session_key=session_key).first()


def stripe_checkout(request):
    import stripe
    from django.conf import settings as djsettings

    from backoffice.models import Stripe

    from .models import Cart

    stripe_object = Stripe.objects.first()
    api_key_customer = stripe_object.STRIPE_SECRET_KEY if stripe_object else None

    stripe.api_key = (
        api_key_customer if api_key_customer else djsettings.STRIPE_SECRET_KEY
    )

    cart = Cart.objects.filter(user=request.customer).first()
    if not cart or cart.items.count() == 0:
        return HttpResponseBadRequest("Cart is empty")

    line_items = []
    for item in cart.items.select_related(
        "product",
        "product_variant",
    ):
        product = item.product
        variant = item.product_variant

        product_name = str(variant) if variant else product.name
        unit_price = int(item.get_item_price() / item.quantity * 100)  # in cents

        # Get product image (main image fallback)
        image_url = product.get_main_image
        if image_url and not image_url.startswith("http"):
            image_url = request.build_absolute_uri(image_url)

        # Description from variant or product
        description = product.description[:250] if product.description else ""

        line_items.append(
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": product_name,
                        "description": description,
                        "images": [image_url] if image_url else [],
                    },
                    "unit_amount": unit_price,
                },
                "quantity": item.quantity,
            }
        )

    try:
        from core.enums import StripeEvents

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=line_items,
            success_url=request.build_absolute_uri("/checkout/success")
            + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.build_absolute_uri("/checkout/cancel/"),
            metadata={
                "teannt_id": str(request.tenant.id),
                "cart_id": str(cart.id),
                "user": str(request.customer.id)
                if request.user.is_authenticated
                else "guest",
                "event": StripeEvents.CUSTOMER_CHECKOUT.value,
                "using_tinyshop_stripe": False if api_key_customer else True,
                "customer_id": str(request.customer.id) if request.customer else None,
            },
        )
        print(request.tenant)
        return redirect(session.url)

    except Exception as e:
        return HttpResponse(f"Stripe error: {str(e)}", status=500)


def stripe_checkout_success(request):
    import stripe
    from django.conf import settings as djsettings

    from backoffice.models import Stripe

    session_id = request.GET.get("session_id")

    stripe_object = Stripe.objects.first()
    api_key_customer = stripe_object.STRIPE_SECRET_KEY if stripe_object else None

    if not session_id:
        return HttpResponse("Forbidden", status=403)

    if not api_key_customer:
        return redirect(to=reverse_lazy("shop:orders-tenant"))

    stripe.api_key = api_key_customer if api_key_customer else djsettings.STRIPE_API_KEY

    customer_session = stripe.checkout.Session.retrieve(id=session_id)

    if customer_session.payment_status == "paid":
        cart = Cart.objects.filter(user=request.customer)
        if not cart:
            return HttpResponse(status=400)
        with transaction.atomic():
            order = Order.objects.create(
                customer=request.customer,
                payment_status=PaymentStatusChoices.PAID,
                status=OrderStatusChoices.PENDING,
                total_amount=cart.get_cart_total(),
                shipping_cost=Decimal("0.00"),
                discount_amount=Decimal("0.00"),
                transaction_id=session_id,
                payment_method=PaymentMethodChoices.STRIPE,
            )

            for item in cart.items.all():
                product = item.product
                variant = item.product_variant
                price = variant.get_price() if variant else product.price

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_variant=variant,
                    quantity=item.quantity,
                    price_at_purchase=price,
                    product_name_snapshot=product.name,
                    variant_details_snapshot=str(variant) if variant else "",
                    sku_snapshot=variant.sku
                    if variant and hasattr(variant, "sku")
                    else "",
                )

            cart.delete()

        return HttpResponse("Order Confirmed")

    return HttpResponse("Forbidden", status=403)


def stripe_checkout_cancel(request):
    return HttpResponse("Cancled")


########################
# heart beat
########################
@csrf_exempt
def heartbeat(request):
    try:
        data = json.loads(request.body)
        browser_id = data.get("browser_id")
    except Exception:
        browser_id = None

    if browser_id:
        log_customer_event(
            customer=request.customer if request.customer else None,
            event_type="heartbeat",
            metadata={"browser_id": browser_id, "seconds": 15},
            request=request,
        )

        # Set individual browser timeout (this will expire after 60 seconds)
        cache.set(f"browser_{browser_id}", True, timeout=60)

        # Maintain a list of browsers (no timeout on this)
        cache_key = "online_browsers_list"
        online_browsers = cache.get(cache_key, [])
        if browser_id not in online_browsers:
            online_browsers.append(browser_id)
            cache.set(cache_key, online_browsers, timeout=None)

    return JsonResponse({"status": "ok"})
