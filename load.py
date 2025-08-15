import os
import random
from datetime import timedelta
from decimal import Decimal

import django
from django.db import IntegrityError
from faker import Faker
from phonenumber_field.phonenumber import PhoneNumber

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
# Replace 'your_project_name' with your actual Django project name
django.setup()

# Import your models
from django.contrib.auth import get_user_model
from django_tenants.utils import tenant_context

# Adjust imports based on your actual app structure
from shop.models import (  # Replace 'shop' with your actual app name
    Address,
    BlogPost,
    Brand,
    Cart,
    CartItem,
    Collection,
    Coupon,
    Customer,
    CustomerEvent,
    InventoryAdjustment,
    Order,
    OrderItem,
    PaymentGateway,
    Product,
    ProductCategory,
    ProductImage,
    ProductVariant,
    Review,
    ShippingMethod,
    SupportTicket,
    TicketMessage,
    Wishlist,
)
from tenant.models import (  # Assuming 'tenant' is a separate app with Employee model
    Employee,
    Tenant,
)

User = get_user_model()  # Get the currently active user model

fake = Faker()


def create_fake_customers(num):
    print(f"Creating {num} customers...")
    customers = []
    for _ in range(num):
        try:
            password = fake.password()
            customer = Customer(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                contact_number=PhoneNumber.from_string(
                    phone_number=fake.phone_number(),
                    region="US",  # Use a region for valid numbers
                ),
                email=fake.unique.email(),
                is_verified=fake.boolean(),
                marketing_opt_in=fake.boolean(),
            )
            customer.set_password(password)  # Use the custom set_password method
            customer.save()
            customers.append(customer)
        except IntegrityError:
            # Handle unique constraint violations for email if they occur (rare with fake.unique)
            continue
    print(f"Created {len(customers)} customers.")
    return customers


def create_fake_addresses(customers, num_per_customer_avg=2):
    print("Creating addresses...")
    addresses = []
    for customer in customers:
        num_addresses = random.randint(
            1, num_per_customer_avg * 2 - 1
        )  # Vary number of addresses
        for i in range(num_addresses):
            address_type = random.choice([t[0] for t in Address.ADDRESS_TYPES])
            is_default = i == 0  # Make the first address default for simplicity
            address = Address.objects.create(
                user=customer,  # Assuming Customer model is the User model for Address ForeignKey
                address_type=address_type,
                full_name=fake.name(),
                phone_number=fake.phone_number(),
                address_line1=fake.street_address(),
                address_line2=fake.secondary_address()
                if fake.boolean(chance_of_getting_true=50)
                else None,
                city=fake.city(),
                state=fake.state_abbr(),
                postal_code=fake.postcode(),
                country=fake.country(),
                is_default=is_default,
            )
            addresses.append(address)
    print(f"Created {len(addresses)} addresses.")
    return addresses


def create_fake_categories(num):
    print(f"Creating {num} categories...")
    categories = []
    for _ in range(num):
        category = ProductCategory.objects.create(
            name=fake.unique.word().capitalize()
            + " "
            + fake.word().capitalize()
            + " Category",
            description=fake.paragraph(nb_sentences=3),
            parent_category=random.choice(categories)
            if categories and fake.boolean(chance_of_getting_true=30)
            else None,
        )
        categories.append(category)
    print(f"Created {len(categories)} categories.")
    return categories


def create_fake_brands(num):
    print(f"Creating {num} brands...")
    brands = []
    for _ in range(num):
        brand = Brand.objects.create(
            name=fake.unique.company(),
            description=fake.paragraph(nb_sentences=2),
            # logo=None # Add logic for fake image if needed
        )
        brands.append(brand)
    print(f"Created {len(brands)} brands.")
    return brands


def create_fake_products(categories, brands, num_products):
    print(f"Creating {num_products} products...")
    products = []
    for _ in range(num_products):
        product = Product.objects.create(
            name=fake.unique.catch_phrase(),
            description=fake.text(max_nb_chars=500),
            category=random.choice(categories) if categories else None,
            brand=random.choice(brands) if brands else None,
            price=Decimal(random.uniform(5.00, 500.00)).quantize(Decimal("0.01")),
            compare_at_price=Decimal(random.uniform(50.00, 600.00)).quantize(
                Decimal("0.01")
            )
            if fake.boolean(chance_of_getting_true=40)
            else None,
            is_available=fake.boolean(chance_of_getting_true=90),
            meta_title=fake.sentence(nb_words=6),
            meta_description=fake.paragraph(nb_sentences=2),
            keywords=", ".join(fake.words(nb=5, unique=True)),
            weight=Decimal(random.uniform(0.1, 10.0)).quantize(Decimal("0.01")),
            length=Decimal(random.uniform(5.0, 50.0)).quantize(Decimal("0.01")),
            width=Decimal(random.uniform(5.0, 50.0)).quantize(Decimal("0.01")),
            height=Decimal(random.uniform(5.0, 50.0)).quantize(Decimal("0.01")),
            views_count=random.randint(0, 1000),
        )
        products.append(product)
    print(f"Created {len(products)} products.")
    return products


def create_fake_product_images(products, num_images_per_product_avg=3):
    print("Creating product images...")
    product_images = []
    for product in products:
        num_images = random.randint(1, num_images_per_product_avg * 2 - 1)
        for i in range(num_images):
            product_image = ProductImage.objects.create(
                product=product,
                image=f"product_images/{fake.uuid4()}.jpg",  # Placeholder for image path
                alt_text=fake.sentence(nb_words=4),
                is_main=(i == 0),
            )
            product_images.append(product_image)
    print(f"Created {len(product_images)} product images.")
    return product_images


def create_fake_product_variants(products, num_variants_per_product_avg=2):
    print("Creating product variants...")
    product_variants = []
    colors = [
        "Red",
        "Blue",
        "Green",
        "Black",
        "White",
        "Yellow",
        "Purple",
        "Orange",
        "Gray",
        "Brown",
    ]
    sizes = ["XS", "S", "M", "L", "XL", "XXL", "One Size"]
    materials = ["Cotton", "Polyester", "Wool", "Leather", "Denim", "Silk", "Nylon"]

    for product in products:
        if fake.boolean(chance_of_getting_true=70):  # Most products have variants
            num_variants = random.randint(1, num_variants_per_product_avg * 2 - 1)
            for _ in range(num_variants):
                price_override = (
                    Decimal(random.uniform(1.00, 100.00)).quantize(Decimal("0.01"))
                    if fake.boolean(chance_of_getting_true=30)
                    else None
                )
                try:
                    variant = ProductVariant.objects.create(
                        product=product,
                        color=random.choice(colors)
                        if fake.boolean(chance_of_getting_true=70)
                        else None,
                        size=random.choice(sizes)
                        if fake.boolean(chance_of_getting_true=70)
                        else None,
                        material=random.choice(materials)
                        if fake.boolean(chance_of_getting_true=30)
                        else None,
                        sku=fake.unique.bothify(text="SKU-####-????"),
                        barcode=fake.unique.ean13(),
                        price_override=price_override,
                        stock_quantity=random.randint(0, 200),
                        is_available=fake.boolean(chance_of_getting_true=95),
                        variant_weight=Decimal(random.uniform(0.01, 5.0)).quantize(
                            Decimal("0.01")
                        )
                        if fake.boolean(chance_of_getting_true=20)
                        else None,
                        variant_length=Decimal(random.uniform(1.0, 30.0)).quantize(
                            Decimal("0.01")
                        )
                        if fake.boolean(chance_of_getting_true=20)
                        else None,
                        variant_width=Decimal(random.uniform(1.0, 30.0)).quantize(
                            Decimal("0.01")
                        )
                        if fake.boolean(chance_of_getting_true=20)
                        else None,
                        variant_height=Decimal(random.uniform(1.0, 30.0)).quantize(
                            Decimal("0.01")
                        )
                        if fake.boolean(chance_of_getting_true=20)
                        else None,
                    )
                    product_variants.append(variant)
                except IntegrityError:
                    # SKU or Barcode might collide if the number of desired unique items is very high
                    continue
    print(f"Created {len(product_variants)} product variants.")
    return product_variants


def create_fake_inventory_adjustments(product_variants, num_adjustments_avg=5):
    print("Creating inventory adjustments...")
    inventory_adjustments = []
    adjustment_types = [t[0] for t in InventoryAdjustment.ADJUSTMENT_TYPES]

    # Get existing Employees or create a dummy Admin user if none exist
    employees = list(Employee.objects.all())
    if not employees:
        print("No Employee found. Creating a dummy superuser for adjustment_by.")
        try:
            admin_user, created = User.objects.get_or_create(
                username="admin",
                email="admin@example.com",
                is_superuser=True,
                is_staff=True,
            )
            if created:
                admin_user.set_password("adminpassword")
                admin_user.save()
            employees.append(admin_user)
        except IntegrityError:
            employees.append(User.objects.get(username="admin"))  # If it already exists

    for variant in product_variants:
        num_adjustments = random.randint(0, num_adjustments_avg * 2 - 1)
        for _ in range(num_adjustments):
            quantity_changed = random.randint(-50, 50)
            if quantity_changed == 0:
                continue
            adjustment_type = random.choice(adjustment_types)
            # Ensure quantity_changed aligns with adjustment_type for realism
            if adjustment_type in ["damage", "transfer_out"] and quantity_changed > 0:
                quantity_changed = -quantity_changed
            elif (
                adjustment_type in ["restock", "return", "transfer_in"]
                and quantity_changed < 0
            ):
                quantity_changed = abs(quantity_changed)
            elif adjustment_type == "initial" and quantity_changed < 0:
                quantity_changed = abs(quantity_changed)

            InventoryAdjustment.objects.create(
                product_variant=variant,
                adjustment_type=adjustment_type,
                quantity_changed=quantity_changed,
                reason=fake.sentence(),
                adjusted_by=random.choice(employees) if employees else None,
                adjustment_date=fake.date_time_between(
                    start_date="-1y", end_date="now"
                ),
            )
    print("Created inventory adjustments.")


def create_fake_orders(customers, products, product_variants, addresses, num_orders):
    print(f"Creating {num_orders} orders...")
    orders = []
    status_choices = [s[0] for s in Order.STATUS_CHOICES]
    payment_status_choices = [ps[0] for ps in Order.PAYMENT_STATUS_CHOICES]

    # Ensure there are enough addresses for customers
    if not addresses:
        print("No addresses found for orders. Skipping order creation.")
        return []

    for _ in range(num_orders):
        customer = random.choice(customers) if customers else None

        # Filter addresses belonging to the selected customer
        customer_addresses = (
            [addr for addr in addresses if addr.user == customer] if customer else []
        )

        shipping_address = (
            random.choice(customer_addresses)
            if customer_addresses
            else (random.choice(addresses) if addresses else None)
        )
        billing_address = (
            random.choice(customer_addresses)
            if customer_addresses
            else (random.choice(addresses) if addresses else None)
        )

        if not shipping_address or not billing_address:
            # Fallback if specific customer has no addresses, or general addresses are missing
            print(
                "Warning: Could not assign shipping/billing address for an order. Skipping order."
            )
            continue

        order_date = fake.date_time_between(start_date="-1y", end_date="now")

        order = Order.objects.create(
            customer=customer,
            order_date=order_date,
            status=random.choice(status_choices),
            total_amount=Decimal("0.00"),  # Will be calculated after items are added
            shipping_cost=Decimal(random.uniform(0.00, 20.00)).quantize(
                Decimal("0.01")
            ),
            discount_amount=Decimal(random.uniform(0.00, 15.00)).quantize(
                Decimal("0.01")
            )
            if fake.boolean(chance_of_getting_true=30)
            else Decimal("0.00"),
            coupon_code_used=fake.word().upper()
            if fake.boolean(chance_of_getting_true=20)
            else None,
            shipping_address=shipping_address,
            billing_address=billing_address,
            payment_status=random.choice(payment_status_choices),
            transaction_id=fake.uuid4()
            if fake.boolean(chance_of_getting_true=80)
            else None,
            payment_method=random.choice(
                ["Credit Card", "PayPal", "COD", "Stripe", "eSewa", "Khalti"]
            ),
            tracking_number=fake.bothify(text="TRK##########")
            if fake.boolean(chance_of_getting_true=70)
            else None,
            shipping_carrier=fake.company()
            if fake.boolean(chance_of_getting_true=70)
            else None,
            customer_notes=fake.sentence()
            if fake.boolean(chance_of_getting_true=30)
            else None,
            admin_notes=fake.paragraph(nb_sentences=1)
            if fake.boolean(chance_of_getting_true=10)
            else None,
        )
        orders.append(order)

        # Create order items for the order
        num_items = random.randint(1, 5)
        for _ in range(num_items):
            if not products:
                continue  # Skip if no products exist
            product = random.choice(products)

            # Filter variants for the chosen product
            available_variants = [v for v in product_variants if v.product == product]
            variant = (
                random.choice(available_variants)
                if available_variants and fake.boolean(chance_of_getting_true=80)
                else None
            )  # Assign variant if exists

            quantity = random.randint(1, 3)
            price_at_purchase = variant.get_price() if variant else product.price

            OrderItem.objects.create(
                order=order,
                product=product,
                product_variant=variant,
                quantity=quantity,
                price_at_purchase=price_at_purchase,
                product_name_snapshot=product.name,
                variant_details_snapshot=str(variant) if variant else None,
                sku_snapshot=variant.sku if variant else None,
            )
        # Recalculate total_amount after adding items
        order.total_amount = order.calculate_total_amount()
        order.save()
    print(f"Created {len(orders)} orders.")
    return orders


def create_fake_carts(customers, products, product_variants, num_carts):
    print(f"Creating {num_carts} carts...")
    carts = []
    for _ in range(num_carts):
        user = (
            random.choice(customers)
            if customers and fake.boolean(chance_of_getting_true=70)
            else None
        )

        # Ensure unique user or session key for the cart
        if user:
            # Check if user already has a cart
            if Cart.objects.filter(user=user).exists():
                continue  # Skip if user already has a cart
            session_key = None
        else:
            session_key = fake.uuid4()
            # Check if session key already exists (unlikely with uuid4)
            if Cart.objects.filter(session_key=session_key).exists():
                continue

        cart = Cart.objects.create(
            user=user,
            session_key=session_key,
        )
        carts.append(cart)

        # Add cart items
        num_items = random.randint(1, 5)
        added_items = set()  # To ensure unique product-variant combos per cart
        for _ in range(num_items):
            if not products:
                continue

            product = random.choice(products)
            available_variants = [v for v in product_variants if v.product == product]
            variant = (
                random.choice(available_variants)
                if available_variants and fake.boolean(chance_of_getting_true=80)
                else None
            )

            item_key = (product.id, variant.id if variant else None)
            if item_key in added_items:
                continue  # Skip if this product-variant combination is already in the cart

            quantity = random.randint(1, 3)
            try:
                CartItem.objects.create(
                    cart=cart,
                    product=product,
                    product_variant=variant,
                    quantity=quantity,
                )
                added_items.add(item_key)
            except IntegrityError:
                # In case unique_together fails due to rare race condition or duplicate logic
                continue
    print(f"Created {len(carts)} carts with items.")
    return carts


def create_fake_reviews(products, customers, num_reviews):
    print(f"Creating {num_reviews} reviews...")
    reviews = []
    if not products or not customers:
        print("Skipping review creation: No products or customers available.")
        return []

    for _ in range(num_reviews):
        product = random.choice(products)
        customer = random.choice(customers)

        # Ensure unique review per customer per product
        if Review.objects.filter(product=product, customer=customer).exists():
            continue

        review = Review.objects.create(
            product=product,
            customer=customer,
            rating=random.randint(1, 5),
            comment=fake.paragraph(nb_sentences=fake.random_int(min=1, max=5))
            if fake.boolean(chance_of_getting_true=80)
            else None,
            is_approved=fake.boolean(chance_of_getting_true=70),
        )
        reviews.append(review)
    print(f"Created {len(reviews)} reviews.")
    return reviews


def create_fake_collections(products, num_collections):
    print(f"Creating {num_collections} collections...")
    collections = []
    if not products:
        print("Skipping collection creation: No products available.")
        return []

    for _ in range(num_collections):
        try:
            collection = Collection.objects.create(
                name=fake.unique.word().capitalize()
                + " "
                + fake.word().capitalize()
                + " Collection",
                description=fake.paragraph(nb_sentences=3),
                is_featured=fake.boolean(chance_of_getting_true=30),
            )
            # Add random products to the collection
            num_products_in_collection = random.randint(3, 15)
            collection_products = random.sample(
                products, min(num_products_in_collection, len(products))
            )
            collection.products.set(collection_products)
            collections.append(collection)
        except IntegrityError:
            continue  # In case of rare slug collision
    print(f"Created {len(collections)} collections.")
    return collections


def create_fake_coupons(num_coupons, products, categories):
    print(f"Creating {num_coupons} coupons...")
    coupons = []
    discount_types = [dt[0] for dt in Coupon.discount_types]

    for _ in range(num_coupons):
        valid_from = fake.date_time_between(start_date="-6m", end_date="now")
        valid_until = valid_from + timedelta(days=random.randint(7, 365))
        discount_type = random.choice(discount_types)

        if discount_type == "free_shipping":
            discount_value = Decimal("0.00")  # Ignored for free shipping
        elif discount_type == "percentage":
            discount_value = Decimal(random.randint(5, 50)).quantize(Decimal("0.01"))
        else:  # fixed
            discount_value = Decimal(random.uniform(5.00, 100.00)).quantize(
                Decimal("0.01")
            )

        try:
            coupon = Coupon.objects.create(
                code=fake.unique.bothify(text="######?#").upper(),
                description=fake.sentence(),
                discount_type=discount_type,
                discount_value=discount_value,
                minimum_order_amount=Decimal(random.uniform(0.00, 200.00)).quantize(
                    Decimal("0.01")
                ),
                is_active=fake.boolean(chance_of_getting_true=80),
                valid_from=valid_from,
                valid_until=valid_until,
                usage_limit=random.randint(10, 500)
                if fake.boolean(chance_of_getting_true=50)
                else None,
                used_count=random.randint(0, 50)
                if fake.boolean(chance_of_getting_true=60)
                else 0,
                per_user_limit=random.randint(1, 5)
                if fake.boolean(chance_of_getting_true=30)
                else None,
            )
            # Optionally add applicable products/categories
            if fake.boolean(chance_of_getting_true=40) and products:
                applicable_prods = random.sample(
                    products, min(random.randint(1, 5), len(products))
                )
                coupon.applicable_products.set(applicable_prods)
            if fake.boolean(chance_of_getting_true=30) and categories:
                applicable_cats = random.sample(
                    categories, min(random.randint(1, 3), len(categories))
                )
                coupon.applicable_categories.set(applicable_cats)

            coupons.append(coupon)
        except IntegrityError:
            continue  # In case of rare code collision
    print(f"Created {len(coupons)} coupons.")
    return coupons


def create_fake_wishlists(customers, products, num_wishlists):
    print(f"Creating {num_wishlists} wishlists...")
    wishlists = []
    if not customers or not products:
        print("Skipping wishlist creation: No customers or products available.")
        return []

    for _ in range(num_wishlists):
        customer = random.choice(customers)
        # Ensure one wishlist per customer
        if Wishlist.objects.filter(customer=customer).exists():
            continue

        wishlist = Wishlist.objects.create(customer=customer)

        # Add random products to the wishlist
        num_products_in_wishlist = random.randint(1, 10)
        wishlist_products = random.sample(
            products, min(num_products_in_wishlist, len(products))
        )
        wishlist.products.set(wishlist_products)
        wishlists.append(wishlist)
    print(f"Created {len(wishlists)} wishlists.")
    return wishlists


def create_fake_blog_posts(num_posts):
    print(f"Creating {num_posts} blog posts...")
    blog_posts = []

    # Get existing Employees or create a dummy Admin user if none exist
    employees = list(Employee.objects.all())
    if not employees:
        print("No Employee found. Creating a dummy superuser for blog author.")
        try:
            admin_user, created = User.objects.get_or_create(
                username="admin",
                email="admin@example.com",
                is_superuser=True,
                is_staff=True,
            )
            if created:
                admin_user.set_password("adminpassword")
                admin_user.save()
            employees.append(admin_user)
        except IntegrityError:
            employees.append(User.objects.get(username="admin"))  # If it already exists

    for _ in range(num_posts):
        try:
            blog_post = BlogPost.objects.create(
                title=fake.unique.sentence(nb_words=8),
                author=random.choice(employees) if employees else None,
                content=fake.text(max_nb_chars=2000),
                featured_image=f"blog_images/{fake.uuid4()}.jpg"
                if fake.boolean(chance_of_getting_true=70)
                else None,
                published_date=fake.date_time_between(start_date="-2y", end_date="now"),
                is_published=fake.boolean(chance_of_getting_true=90),
                meta_title=fake.sentence(nb_words=10)
                if fake.boolean(chance_of_getting_true=80)
                else None,
                meta_description=fake.paragraph(nb_sentences=3)
                if fake.boolean(chance_of_getting_true=80)
                else None,
            )
            blog_posts.append(blog_post)
        except IntegrityError:
            continue  # In case of rare slug collision
    print(f"Created {len(blog_posts)} blog posts.")
    return blog_posts


def create_fake_support_tickets(customers, orders, num_tickets):
    print(f"Creating {num_tickets} support tickets...")
    support_tickets = []
    status_choices = [s[0] for s in SupportTicket.STATUS_CHOICES]
    priority_choices = [p[0] for p in SupportTicket.PRIORITY_CHOICES]

    # Get existing Employees or create a dummy Admin user if none exist
    employees = list(Employee.objects.all())
    if not employees:
        print("No Employee found. Creating a dummy superuser for ticket assignment.")
        try:
            admin_user, created = User.objects.get_or_create(
                username="admin",
                email="admin@example.com",
                is_superuser=True,
                is_staff=True,
            )
            if created:
                admin_user.set_password("adminpassword")
                admin_user.save()
            employees.append(admin_user)
        except IntegrityError:
            employees.append(User.objects.get(username="admin"))  # If it already exists

    if not customers:
        print("Skipping support ticket creation: No customers available.")
        return []

    for _ in range(num_tickets):
        customer = random.choice(customers)
        related_order = (
            random.choice(orders)
            if orders and fake.boolean(chance_of_getting_true=60)
            else None
        )

        status = random.choice(status_choices)
        closed_at = (
            fake.date_time_between(start_date="-6m", end_date="now")
            if status in ["closed", "resolved"]
            else None
        )

        ticket = SupportTicket.objects.create(
            customer=customer,
            order=related_order,
            subject=fake.catch_phrase(),
            description=fake.paragraph(nb_sentences=5),
            status=status,
            priority=random.choice(priority_choices),
            assigned_to=random.choice(employees) if employees else None,
            closed_at=closed_at,
        )
        support_tickets.append(ticket)
    print(f"Created {len(support_tickets)} support tickets.")
    return support_tickets


def create_fake_ticket_messages(support_tickets, num_messages_per_ticket_avg=3):
    print("Creating ticket messages...")

    # Get existing Employees or create a dummy Admin user if none exist
    employees = list(Employee.objects.all())
    if not employees:
        print("No Employee found. Creating a dummy superuser for message sender.")
        try:
            admin_user, created = User.objects.get_or_create(
                username="admin",
                email="admin@example.com",
                is_superuser=True,
                is_staff=True,
            )
            if created:
                admin_user.set_password("adminpassword")
                admin_user.save()
            employees.append(admin_user)
        except IntegrityError:
            employees.append(User.objects.get(username="admin"))  # If it already exists

    if not support_tickets or not employees:
        print("Skipping ticket message creation: No tickets or employees available.")
        return

    for ticket in support_tickets:
        num_messages = random.randint(1, num_messages_per_ticket_avg * 2 - 1)
        for i in range(num_messages):
            sender = random.choice(employees)  # Messages can be from staff

            # Ensure message timestamp is after ticket creation
            sent_at = fake.date_time_between(
                start_date=ticket.created_at, end_date="now"
            )

            TicketMessage.objects.create(
                ticket=ticket,
                sender=sender,
                message=fake.paragraph(nb_sentences=2),
                sent_at=sent_at,
            )
    print("Created ticket messages.")


def create_fake_payment_gateways(num):
    print(f"Creating {num} payment gateways...")
    gateways = []
    gateway_types = [gt[0] for gt in PaymentGateway.GATEWAY_TYPES]
    for _ in range(num):
        try:
            gateway = PaymentGateway.objects.create(
                name=fake.unique.company() + " Pay",
                gateway_type=random.choice(gateway_types),
                is_active=fake.boolean(chance_of_getting_true=80),
                api_key=fake.sha256(raw_output=False),
                secret_key=fake.sha256(raw_output=False),
                publishable_key=fake.sha256(raw_output=False),
                settings_json={"mode": "test", "currency": "USD"},  # Example JSON
            )
            gateways.append(gateway)
        except IntegrityError:
            continue  # In case of rare name collision
    print(f"Created {len(gateways)} payment gateways.")
    return gateways


def create_fake_shipping_methods(num):
    print(f"Creating {num} shipping methods...")
    methods = []
    for _ in range(num):
        try:
            method = ShippingMethod.objects.create(
                name=fake.unique.bs() + " Shipping",
                description=fake.sentence(),
                cost=Decimal(random.uniform(0.00, 50.00)).quantize(Decimal("0.01")),
                is_active=fake.boolean(chance_of_getting_true=90),
                min_order_value=Decimal(random.uniform(0.00, 100.00)).quantize(
                    Decimal("0.01")
                ),
                max_weight=Decimal(random.uniform(10.0, 100.0)).quantize(
                    Decimal("0.01")
                )
                if fake.boolean(chance_of_getting_true=50)
                else None,
                estimated_delivery_days=random.choice(
                    [
                        "1-2 business days",
                        "3-5 business days",
                        "5-10 business days",
                        "Next Day Delivery",
                    ]
                ),
            )
            methods.append(method)
        except IntegrityError:
            continue  # In case of rare name collision
    print(f"Created {len(methods)} shipping methods.")
    return methods


def create_fake_customer_events(customers, products, orders, num_events):
    print(f"Creating {num_events} customer events...")
    event_types = [
        "view_product",
        "add_to_cart",
        "remove_from_cart",
        "checkout_started",
        "purchase_completed",
        "login",
        "logout",
        "search",
    ]

    if not customers:
        print("Skipping customer event creation: No customers available.")
        return

    for _ in range(num_events):
        customer = random.choice(customers)
        event_type = random.choice(event_types)
        metadata = {}

        if (
            event_type in ["view_product", "add_to_cart", "remove_from_cart"]
            and products
        ):
            product = random.choice(products)
            metadata["product_id"] = product.id
            metadata["product_name"] = product.name
            if event_type in ["add_to_cart", "remove_from_cart"]:
                metadata["quantity"] = random.randint(1, 3)
        elif event_type in ["checkout_started", "purchase_completed"] and orders:
            order = random.choice(orders)
            metadata["order_id"] = order.id
            metadata["total_amount"] = str(
                order.total_amount
            )  # Convert Decimal to string for JSON
        elif event_type == "search":
            metadata["query"] = fake.word()
            metadata["results_count"] = random.randint(0, 20)

        CustomerEvent.objects.create(
            customer=customer,
            event_type=event_type,
            metadata=metadata,
            timestamp=fake.date_time_between(start_date="-6m", end_date="now"),
        )
    print(f"Created {num_events} customer events.")


# --- Main execution block ---
def run():
    print("--- Starting Fake Data Generation ---")
    # Clear existing data (OPTIONAL - uncomment with caution!)
    # print("Clearing existing data...")
    # CustomerEvent.objects.all().delete()
    # SupportTicket.objects.all().delete()
    # TicketMessage.objects.all().delete()
    # CartItem.objects.all().delete()
    # Cart.objects.all().delete()
    # OrderItem.objects.all().delete()
    # Order.objects.all().delete()
    # InventoryAdjustment.objects.all().delete()
    # ProductVariant.objects.all().delete()
    # ProductImage.objects.all().delete()
    # Product.objects.all().delete()
    # ProductCategory.objects.all().delete()
    # Brand.objects.all().delete()
    # Address.objects.all().delete()
    # Customer.objects.all().delete()
    # Review.objects.all().delete()
    # Collection.objects.all().delete()
    # Coupon.objects.all().delete()
    # Wishlist.objects.all().delete()
    # BlogPost.objects.all().delete()
    # PaymentGateway.objects.all().delete()
    # ShippingMethod.objects.all().delete()
    # print("Data cleared.")

    # Number of records to create
    NUM_CUSTOMERS = 50
    NUM_CATEGORIES = 10
    NUM_BRANDS = 15
    NUM_PRODUCTS = 100
    NUM_ORDERS = 70
    NUM_CARTS = 30
    NUM_REVIEWS = 150
    NUM_COLLECTIONS = 5
    NUM_COUPONS = 10
    NUM_WISHLISTS = 20
    NUM_BLOG_POSTS = 10
    NUM_SUPPORT_TICKETS = 40
    NUM_PAYMENT_GATEWAYS = 5
    NUM_SHIPPING_METHODS = 3
    NUM_CUSTOMER_EVENTS = 200

    # 1. Core Users and Addresses
    customers = create_fake_customers(NUM_CUSTOMERS)
    addresses = create_fake_addresses(customers)

    # 2. Product Catalog
    categories = create_fake_categories(NUM_CATEGORIES)
    brands = create_fake_brands(NUM_BRANDS)
    products = create_fake_products(categories, brands, NUM_PRODUCTS)
    product_images = create_fake_product_images(products)
    product_variants = create_fake_product_variants(products)
    create_fake_inventory_adjustments(
        product_variants
    )  # Doesn't return list, just creates

    # 3. Orders and Carts
    orders = create_fake_orders(
        customers, products, product_variants, addresses, NUM_ORDERS
    )
    carts = create_fake_carts(customers, products, product_variants, NUM_CARTS)

    # 4. Marketing & Engagement
    reviews = create_fake_reviews(products, customers, NUM_REVIEWS)
    collections = create_fake_collections(products, NUM_COLLECTIONS)
    coupons = create_fake_coupons(NUM_COUPONS, products, categories)
    wishlists = create_fake_wishlists(customers, products, NUM_WISHLISTS)
    blog_posts = create_fake_blog_posts(NUM_BLOG_POSTS)

    # 5. Customer Service
    support_tickets = create_fake_support_tickets(
        customers, orders, NUM_SUPPORT_TICKETS
    )
    create_fake_ticket_messages(support_tickets)  # Doesn't return list, just creates

    # 6. Payment & Shipping Configuration
    payment_gateways = create_fake_payment_gateways(NUM_PAYMENT_GATEWAYS)
    shipping_methods = create_fake_shipping_methods(NUM_SHIPPING_METHODS)

    # 7. Customer Events
    create_fake_customer_events(customers, products, orders, NUM_CUSTOMER_EVENTS)

    print("--- Fake Data Generation Complete! ---")


if __name__ == "main":
    tenant = Tenant.objects.get(name="johnelton")
    with tenant_context(tenant):
        run()
