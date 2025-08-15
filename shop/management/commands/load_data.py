import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context
from faker import Faker

from shop.models import (
    Address,
    Brand,
    Customer,
    Order,
    OrderItem,
    Product,
    ProductCategory,
)


class Command(BaseCommand):
    help = "Load fake data into the database"

    def __init__(self):
        super().__init__()
        self.faker = Faker()

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting to load fake data..."))
        with schema_context("johnelton"):
            self.create_fake_customers(10)
            self.create_fake_categories(5)
            self.create_fake_brands(5)
            self.create_fake_products(20)
            self.create_fake_orders(10)

        self.stdout.write(self.style.SUCCESS("Successfully loaded fake data!"))

    def create_fake_customers(self, num_customers):
        for _ in range(num_customers):
            first_name = self.faker.first_name()
            last_name = self.faker.last_name()
            email = self.faker.email()
            password = self.faker.password()
            contact_number = self.faker.phone_number()
            marketing_opt_in = random.choice([True, False])

            customer = Customer(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
                contact_number=contact_number,
                marketing_opt_in=marketing_opt_in,
            )
            customer.set_password(password)
            customer.save()

            # Create an address for the customer
            self.create_fake_address(customer)

    def create_fake_address(self, customer):
        address_type = random.choice(Address.ADDRESS_TYPES)[0]
        full_name = f"{customer.first_name} {customer.last_name}"
        phone_number = self.faker.phone_number()
        address_line1 = self.faker.street_address()
        address_line2 = self.faker.secondary_address()
        city = self.faker.city()
        state = self.faker.state()
        postal_code = self.faker.postcode()
        country = self.faker.country()
        is_default = random.choice([True, False])

        address = Address(
            user=customer,
            address_type=address_type,
            full_name=full_name,
            phone_number=phone_number,
            address_line1=address_line1,
            address_line2=address_line2,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
            is_default=is_default,
        )
        address.save()

    def create_fake_categories(self, num_categories):
        for _ in range(num_categories):
            name = self.faker.word().capitalize()
            description = self.faker.text()

            category = ProductCategory(name=name, description=description)
            category.save()

    def create_fake_brands(self, num_brands):
        for _ in range(num_brands):
            name = self.faker.company()
            description = self.faker.text()
            logo = None  # You can add logic to generate a fake logo if needed

            brand = Brand(name=name, description=description, logo=logo)
            brand.save()

    def create_fake_products(self, num_products):
        categories = ProductCategory.objects.all()
        brands = Brand.objects.all()

        for _ in range(num_products):
            name = self.faker.word().capitalize()
            description = self.faker.text()
            category = random.choice(categories) if categories else None
            brand = random.choice(brands) if brands else None
            price = Decimal(random.uniform(10, 1000)).quantize(Decimal("0.01"))
            compare_at_price = (
                Decimal(random.uniform(price, price + 100)).quantize(Decimal("0.01"))
                if random.choice([True, False])
                else None
            )
            is_available = random.choice([True, False])
            meta_title = name
            meta_description = description
            keywords = self.faker.words()
            weight = Decimal(random.uniform(0.1, 10)).quantize(Decimal("0.01"))
            length = Decimal(random.uniform(1, 50)).quantize(Decimal("0.01"))
            width = Decimal(random.uniform(1, 50)).quantize(Decimal("0.01"))
            height = Decimal(random.uniform(1, 50)).quantize(Decimal("0.01"))
            views_count = random.randint(0, 1000)

            product = Product(
                name=name,
                description=description,
                category=category,
                brand=brand,
                price=price,
                compare_at_price=compare_at_price,
                is_available=is_available,
                meta_title=meta_title,
                meta_description=meta_description,
                keywords=keywords,
                weight=weight,
                length=length,
                width=width,
                height=height,
                views_count=views_count,
            )
            product.save()

    def create_fake_orders(self, num_orders):
        customers = Customer.objects.all()
        products = Product.objects.all()

        for _ in range(num_orders):
            customer = random.choice(customers) if customers else None
            order_date = self.faker.date_time_this_year()
            status = random.choice([status[0] for status in Order.STATUS_CHOICES])
            total_amount = Decimal(random.uniform(10, 1000)).quantize(Decimal("0.01"))
            shipping_cost = Decimal(random.uniform(1, 50)).quantize(Decimal("0.01"))
            discount_amount = Decimal(random.uniform(0, 50)).quantize(Decimal("0.01"))
            coupon_code_used = (
                self.faker.word().upper() if random.choice([True, False]) else None
            )
            shipping_address = Address.objects.filter(user=customer).first()
            billing_address = Address.objects.filter(user=customer).first()
            payment_status = random.choice(
                [status[0] for status in Order.PAYMENT_STATUS_CHOICES]
            )
            transaction_id = self.faker.uuid4()
            payment_method = random.choice(["Credit Card", "PayPal", "COD"])
            tracking_number = (
                self.faker.uuid4() if random.choice([True, False]) else None
            )
            shipping_carrier = self.faker.company() if tracking_number else None
            tracking_url = self.faker.url() if tracking_number else None
            customer_notes = self.faker.text() if random.choice([True, False]) else None
            admin_notes = self.faker.text() if random.choice([True, False]) else None
            refund_amount = (
                Decimal(random.uniform(0, total_amount)).quantize(Decimal("0.01"))
                if status in ["refunded", "partially_refunded"]
                else Decimal("0.00")
            )
            refund_reason = self.faker.text() if refund_amount > 0 else None
            refunded_at = (
                self.faker.date_time_this_year() if refund_amount > 0 else None
            )

            order = Order(
                customer=customer,
                order_date=order_date,
                status=status,
                total_amount=total_amount,
                shipping_cost=shipping_cost,
                discount_amount=discount_amount,
                coupon_code_used=coupon_code_used,
                shipping_address=shipping_address,
                billing_address=billing_address,
                payment_status=payment_status,
                transaction_id=transaction_id,
                payment_method=payment_method,
                tracking_number=tracking_number,
                shipping_carrier=shipping_carrier,
                tracking_url=tracking_url,
                customer_notes=customer_notes,
                admin_notes=admin_notes,
                refund_amount=refund_amount,
                refund_reason=refund_reason,
                refunded_at=refunded_at,
            )
            order.save()

            # Create order items for the order
            self.create_fake_order_items(order, products)

    def create_fake_order_items(self, order, products):
        num_items = random.randint(1, 5)
        for _ in range(num_items):
            product = random.choice(products) if products else None
            quantity = random.randint(1, 5)
            price_at_purchase = product.price if product else Decimal("0.01")

            order_item = OrderItem(
                order=order,
                product=product,
                quantity=quantity,
                price_at_purchase=price_at_purchase,
                product_name_snapshot=product.name if product else "Unknown Product",
            )
            order_item.save()
