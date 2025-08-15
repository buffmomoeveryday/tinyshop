import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import QuerySet, Sum
from django.utils.text import slugify
from phonenumber_field.modelfields import PhoneNumberField

from core.models import BaseModel

User = get_user_model()


########################
# chat models
########################
class ChatMessage(BaseModel):
    incomming_message = models.CharField()
    outgoing_message = models.CharField()
    explanation = models.CharField(null=True,blank=True)


class CustomerEvent(models.Model):
    customer = models.ForeignKey(
        "Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=100)
    path = models.CharField(max_length=500, blank=True)
    method = models.CharField(max_length=10, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    referrer = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} - {self.customer or 'Anonymous'}"


class Customer(BaseModel):
    orders: QuerySet["Order"]
    first_name = models.CharField(verbose_name="first name", max_length=255)
    last_name = models.CharField(verbose_name="last name", max_length=255)
    contact_number = PhoneNumberField(verbose_name="user's contact number", null=True)
    email = models.EmailField(verbose_name="user's email", unique=True)
    password = models.CharField(verbose_name="Password")
    is_verified = models.BooleanField(default=False)
    marketing_opt_in = models.BooleanField(verbose_name="User's marketing preferene")

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password_user(self, raw_password):
        return check_password(raw_password, self.password)

    def get_total_orders(self):
        return self.orders.count()

    def get_total(self):
        """Returns the total value of all 'paid' or 'completed' orders."""
        valid_statuses = [
            "paid",
            "refunded",
            "partially_refunded",
        ]
        return sum(
            (
                order.total_amount
                for order in self.orders.filter(payment_status__in=valid_statuses)
            ),
            Decimal("0.00"),
        )

    @property
    def username(self):
        return self.email

    @property
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"


class Address(BaseModel):
    """
    Model to store multiple addresses per user (shipping, billing, etc.)
    """

    ADDRESS_TYPES = [
        ("billing", "Billing Address"),
        ("shipping", "Shipping Address"),
        ("both", "Both Billing & Shipping"),
    ]

    user = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="addresses"
    )
    address_type = models.CharField(
        max_length=20, choices=ADDRESS_TYPES, default="shipping"
    )
    full_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)

    class Meta:  # type:ignore
        verbose_name_plural = "Addresses"

    def __str__(self):
        return f"{self.full_name or self.user.username}'s {self.get_address_type_display()} Address ({self.city})"  # type:ignore

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(
                user=self.user,
                address_type=self.address_type,
                is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


# ===========================================================================
# 2. Product Catalog Models (Categories, Brands, Products, Variants, Images)
# ===========================================================================


class ProductCategory(BaseModel):
    """
    Model for organizing products into categories (supports hierarchy).
    """

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, editable=False)
    description = models.TextField(blank=True, null=True)
    parent_category = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subcategories",
    )

    class Meta:  # type:ignore
        verbose_name_plural = "Product Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(BaseModel):
    """
    Model for product brands or manufacturers.
    """

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, editable=False)
    description = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to="brand_logos/", blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(BaseModel):
    """
    Core product model.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, editable=False)
    description = models.TextField()
    category = models.ForeignKey(
        ProductCategory, on_delete=models.SET_NULL, null=True, related_name="products"
    )
    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )

    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    compare_at_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Original price for display (e.g., if product is on sale)",
    )

    is_available = models.BooleanField(default=True)

    # SEO fields
    meta_title = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="SEO Title Tag (defaults to product name)",
    )
    meta_description = models.TextField(
        blank=True, null=True, help_text="SEO Meta Description"
    )
    keywords = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Comma-separated keywords for SEO",
    )

    # Shipping/Physical attributes (base product dimensions/weight)
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Weight in kg or lbs (define unit)",
    )
    length = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Length in cm or inches (define unit)",
    )
    width = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Width in cm or inches (define unit)",
    )
    height = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Height in cm or inches (define unit)",
    )

    # Basic view count for popularity tracking
    views_count = models.PositiveIntegerField(default=0)

    class Meta:  # type:ignore
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.meta_title:  # Auto-populate meta_title if empty
            self.meta_title = self.name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def get_main_image(self):
        main_image = self.images.filter(is_main=True).first()  # type:ignore
        if main_image and main_image.image:
            return main_image.image.url
        fallback_image = self.images.first()  # type:ignore
        if fallback_image and fallback_image.image:
            return fallback_image.image.url
        return None


class ProductImage(BaseModel):
    """
    Images associated with a product.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="product_images/")
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    is_main = models.BooleanField(default=False)

    class Meta:  # type:ignore
        ordering = ["-is_main", "created_at"]  # Main image first, then by creation date

    def __str__(self):
        return f"Image for {self.product.name}"


class ProductVariant(BaseModel):
    """
    Model for different versions of a product (e.g., color, size).
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    color = models.CharField(max_length=100, blank=True, null=True)
    size = models.CharField(max_length=100, blank=True, null=True)
    material = models.CharField(max_length=100, blank=True, null=True)

    sku = models.CharField(max_length=100, unique=True, blank=True, null=True)
    barcode = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        help_text="E.g., UPC, EAN, ISBN",
    )  # Barcode/GTIN

    price_override = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Overrides the product's base price if set",
    )
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    is_available = models.BooleanField(default=True)

    variant_weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Specific weight for this variant (overrides product weight)",
    )
    variant_length = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Specific length for this variant",
    )
    variant_width = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Specific width for this variant",
    )
    variant_height = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Specific height for this variant",
    )

    def get_price(self):
        """Returns the variant's price, or the product's base price if not overridden."""
        return (
            self.price_override
            if self.price_override is not None
            else self.product.price
        )

    def __str__(self):
        variant_name = f"{self.product.name}"
        attributes = []
        if self.color:
            attributes.append(self.color)
        if self.size:
            attributes.append(self.size)
        if self.material:
            attributes.append(self.material)

        if attributes:
            variant_name += f" ({', '.join(attributes)})"
        return variant_name


class InventoryAdjustment(BaseModel):
    """
    Records changes to inventory stock levels, useful for auditing.
    """

    ADJUSTMENT_TYPES = [
        ("initial", "Initial Stock"),
        ("restock", "Restock"),
        ("return", "Customer Return"),
        ("damage", "Damage/Loss"),
        ("audit", "Inventory Audit Correction"),
        ("transfer_in", "Transfer In"),
        ("transfer_out", "Transfer Out"),
        ("other", "Other"),
    ]

    product_variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="inventory_adjustments"
    )
    adjustment_type = models.CharField(max_length=50, choices=ADJUSTMENT_TYPES)
    quantity_changed = models.IntegerField(
        help_text="Positive for additions, negative for reductions"
    )
    reason = models.TextField(blank=True, null=True)
    adjusted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Staff member who made the adjustment",
    )
    adjustment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        action = "added" if self.quantity_changed > 0 else "removed"
        return f"{abs(self.quantity_changed)} units {action} from {self.product_variant} ({self.adjustment_type})"


# ===========================================================================
# 3. Order & Cart Models
# ===========================================================================
class PaymentMethodChoices(models.TextChoices):
    STRIPE = "stripe"


class OrderStatusChoices(models.TextChoices):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatusChoices(models.TextChoices):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class Order(BaseModel):
    """
    Represents a customer's order.
    """

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=50, choices=OrderStatusChoices.choices, default="pending"
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    shipping_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    coupon_code_used = models.CharField(max_length=50, blank=True, null=True)

    # Link to the Address model for shipping and billing
    shipping_address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shipped_orders",
    )
    billing_address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="billed_orders",
    )

    payment_status = models.CharField(
        max_length=50,
        choices=PaymentStatusChoices.choices,
        default="pending",
    )
    transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Transaction ID from payment gateway",
    )
    payment_method = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        choices=PaymentMethodChoices.choices,
        help_text="e.g., 'Credit Card', 'PayPal', 'COD'",
    )

    # Shipping tracking
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    shipping_carrier = models.CharField(max_length=100, blank=True, null=True)
    tracking_url = models.URLField(max_length=500, blank=True, null=True)

    # Customer notes/instructions
    customer_notes = models.TextField(blank=True, null=True)

    # Admin notes
    admin_notes = models.TextField(
        blank=True, null=True, help_text="Internal notes for staff"
    )

    # Refund details (if applicable)
    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    refund_reason = models.TextField(blank=True, null=True)
    refunded_at = models.DateTimeField(blank=True, null=True)

    class Meta:  # type:ignore
        ordering = ["-order_date"]

    def __str__(self):
        return f"Order {self.pk} by {self.customer.username if self.customer else 'Guest'} - {self.status}"

    def calculate_total_amount(self):
        """Calculates the total amount of the order from its items, shipping, and discount."""
        item_total = sum(item.get_total_price() for item in self.items.all())  # type:ignore
        total = item_total + self.shipping_cost - self.discount_amount
        return max(Decimal("0.00"), total)


class OrderItem(BaseModel):
    """
    Details each product within an Order.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_items",
        help_text="Link to Product for historical reference",
    )
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
        help_text="Link to ProductVariant for historical reference",
    )
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price_at_purchase = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Price of the item when the order was placed",
    )

    # Snapshots of product/variant details for accurate historical record keeping
    product_name_snapshot = models.CharField(max_length=255)
    variant_details_snapshot = models.CharField(
        max_length=255, blank=True, null=True, help_text="e.g., 'Color: Red, Size: M'"
    )
    sku_snapshot = models.CharField(max_length=100, blank=True, null=True)

    def get_total_price(self):
        return self.quantity * self.price_at_purchase

    def __str__(self):
        return f"{self.quantity} x {self.product_name_snapshot} (Order {self.order.id})"


class Cart(BaseModel):
    """
    Represents a customer's shopping cart.
    Can be linked to a User or an anonymous session.
    """

    user = models.OneToOneField(
        Customer, on_delete=models.CASCADE, null=True, blank=True, related_name="cart"
    )
    session_key = models.CharField(
        max_length=40,
        unique=True,
        blank=True,
        null=True,
        help_text="For anonymous users, corresponds to Django session key",
    )

    def __str__(self):
        if self.user:
            return f"Cart of {self.user.username}"
        elif self.session_key:
            return f"Guest Cart ({self.session_key[:10]}...)"

        return f"Cart {self.pk}"

    def cart_count(self):
        """
        Calculates the total number of individual product units in the cart.
        """
        return (
            self.items.aggregate(total_quantity=Sum("quantity"))["total_quantity"] or 0  # type:ignore
        )

    def get_cart_total(self):
        """
        Calculate the total price of all items in the cart.
        """
        from decimal import Decimal

        total = Decimal("0.00")
        for item in self.items.all():  # type:ignore
            total += item.get_item_price()
        return total


class CartItem(BaseModel):
    """
    Details a product and its quantity within a Cart.
    """

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="cart_items"
    )
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cart_items",
    )
    quantity = models.IntegerField(validators=[MinValueValidator(1)])

    class Meta:  # type:ignore
        unique_together = ("cart", "product", "product_variant")
        ordering = ["-created_at"]

    def get_item_price(self):
        """Calculates the total price for this cart item (quantity * variant/product price)."""
        if self.product_variant:
            return self.product_variant.get_price() * self.quantity
        return self.product.price * self.quantity

    def __str__(self):
        if self.product_variant:
            return f"{self.quantity} x {self.product_variant.product.name} ({self.product_variant})"
        return f"{self.quantity} x {self.product.name}"


# ===========================================================================
# 4. Marketing & Engagement Models (Reviews, Collections, Coupons, Blog)
# ===========================================================================


class Review(BaseModel):
    """
    Customer product reviews and ratings.
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1)], help_text="Rating from 1 to 5"
    )
    comment = models.TextField(blank=True, null=True)
    is_approved = models.BooleanField(
        default=False, help_text="Admin approval status for review publication"
    )

    class Meta:  # type:ignore
        unique_together = ("product", "customer")  # One review per customer per product
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review ({self.rating}/5) for {self.product.name} by {self.customer.username}"


class Collection(BaseModel):
    """
    Groups products into marketing collections (e.g., 'New Arrivals', 'Summer Sale').
    """

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, editable=False)
    description = models.TextField(blank=True, null=True)
    products = models.ManyToManyField(Product, related_name="collections", blank=True)
    is_featured = models.BooleanField(
        default=False, help_text="Mark as a featured collection for homepage display"
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Coupon(BaseModel):
    """
    Manages discount codes.
    """

    discount_types = [
        ("percentage", "Percentage"),
        ("fixed", "Fixed Amount"),
        ("free_shipping", "Free Shipping"),  # Specialized type for free shipping
    ]

    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    discount_type = models.CharField(max_length=20, choices=discount_types)
    discount_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Value of discount (e.g., 10 for 10% or $10). Ignored if type is Free Shipping.",
    )
    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Minimum order total required to use this coupon.",
    )
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    usage_limit = models.IntegerField(
        null=True,
        blank=True,
        help_text="Total number of times this coupon can be used across all users",
    )
    used_count = models.IntegerField(default=0)  # Tracks global usage

    # Usage tracking per user
    per_user_limit = models.IntegerField(
        null=True, blank=True, help_text="Max times a single user can use this coupon"
    )

    # Applicable to specific products/categories
    applicable_products = models.ManyToManyField(
        Product,
        blank=True,
        related_name="coupons",
        help_text="Leave empty to apply to all products",
    )
    applicable_categories = models.ManyToManyField(
        ProductCategory,
        blank=True,
        related_name="coupons",
        help_text="Leave empty to apply to all categories",
    )

    def is_valid(self, order_total=None, user=None):
        """Checks if the coupon is currently valid based on dates, limits, and order total."""
        now = datetime.datetime.now()
        if not self.is_active:
            return False, "Coupon is not active."
        if now < self.valid_from:
            return False, "Coupon is not yet valid."
        if now > self.valid_until:
            return False, "Coupon has expired."
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return False, "Coupon has reached its maximum usage limit."
        if order_total is not None and order_total < self.minimum_order_amount:
            return False, f"Minimum order of ${self.minimum_order_amount} required."
        if user and self.per_user_limit is not None:
            user_uses = Order.objects.filter(
                customer=user, coupon_code_used=self.code
            ).count()
            if user_uses >= self.per_user_limit:
                return False, "You have exceeded the usage limit for this coupon."
        return True, "Coupon is valid."

    def __str__(self):
        return self.code


class Wishlist(BaseModel):
    """
    Allows users to save products they are interested in.
    """

    customer = models.OneToOneField(
        Customer, on_delete=models.CASCADE, related_name="wishlist"
    )
    products = models.ManyToManyField(Product, related_name="wishlists", blank=True)

    def __str__(self):
        return f"Wishlist of {self.customer.full_name}"


class BlogPost(BaseModel):
    """
    For content marketing (blog posts, articles).
    """

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, editable=False)
    author = models.ForeignKey(
        "tenant.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blog_posts",
    )
    content = models.TextField()
    featured_image = models.ImageField(upload_to="blog_images/", blank=True, null=True)
    published_date = models.DateTimeField(auto_now_add=True)

    is_published = models.BooleanField(default=True)

    # SEO fields for blog posts
    meta_title = models.CharField(max_length=255, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)

    class Meta:  # type:ignore
        ordering = ["-published_date"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# ===========================================================================
# 5. Customer Service Models
# ===========================================================================


class SupportTicket(BaseModel):
    """
    Model for customer support inquiries.
    """

    STATUS_CHOICES = [
        ("open", "Open"),
        ("pending", "Pending Customer Reply"),
        ("closed", "Closed"),
        ("resolved", "Resolved"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="support_tickets",
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_tickets",
        help_text="Related order, if any",
    )
    subject = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="medium"
    )
    assigned_to = models.ForeignKey(
        "tenant.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
        help_text="Staff member assigned to this ticket",
    )

    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Ticket #{self.pk}: {self.subject} ({self.status})"


class TicketMessage(BaseModel):
    """
    Individual messages within a support ticket.
    """

    ticket = models.ForeignKey(
        SupportTicket, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        "tenant.Employee",
        on_delete=models.CASCADE,
        related_name="sent_ticket_messages",
    )  # Customer or staff
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender.username} on ticket {self.ticket.id} at {self.sent_at.strftime('%Y-%m-%d %H:%M')}"


# ===========================================================================
# 6. Payment & Shipping Configuration
# ===========================================================================


class PaymentGateway(BaseModel):
    """
    Configuration for different payment gateways (e.g., Stripe, PayPal).
    Note: For production, sensitive keys should be stored securely (e.g., encrypted fields, environment variables).
    """

    GATEWAY_TYPES = [
        ("stripe", "Stripe"),
        ("paypal", "PayPal"),
        ("razorpay", "Razorpay"),
        ("esewa", "eSewa (Nepal specific)"),
        ("khalti", "Khalti (Nepal specific)"),
        ("cod", "Cash On Delivery"),
    ]
    name = models.CharField(max_length=100, unique=True)
    gateway_type = models.CharField(max_length=50, choices=GATEWAY_TYPES)
    is_active = models.BooleanField(default=True)
    api_key = models.CharField(
        max_length=255, blank=True, null=True, help_text="API Key (store securely)"
    )
    secret_key = models.CharField(
        max_length=255, blank=True, null=True, help_text="Secret Key (store securely)"
    )
    publishable_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Publishable Key (for client-side integration)",
    )
    settings_json = models.JSONField(
        blank=True,
        null=True,
        help_text="Store additional gateway-specific settings as JSON",
    )

    def __str__(self):
        return self.name


class ShippingMethod(BaseModel):
    """
    Defines available shipping options and their costs.
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    is_active = models.BooleanField(default=True)

    # Rules for applicability (can be extended significantly)
    min_order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Minimum order total for this method to be available",
    )
    max_weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Maximum total order weight for this method",
    )
    estimated_delivery_days = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="e.g., '3-5 business days', 'Next Day'",
    )

    def __str__(self):
        return f"{self.name} (${self.cost})"
