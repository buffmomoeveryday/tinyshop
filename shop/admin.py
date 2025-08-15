# -*- coding: utf-8 -*-
from django import forms
from django.contrib import admin
from django.contrib.auth.hashers import make_password

from .models import (
    Address,
    BlogPost,
    Brand,
    Cart,
    CartItem,
    Collection,
    Coupon,
    Customer,
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


class CustomerAdminForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = "__all__"
        widgets = {"password": forms.PasswordInput(render_value=True)}

    def clean_password(self):
        password = self.cleaned_data["password"]
        if self.instance.pk and self.instance.password == password:
            return password  # Already hashed
        return make_password(password)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    form = CustomerAdminForm
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "first_name",
        "last_name",
        "contact_number",
        "email",
        "password",
        "is_verified",
        "marketing_opt_in",
    )
    list_filter = ("created_at", "updated_at", "is_verified", "marketing_opt_in")
    date_hierarchy = "created_at"
    fields = (
        "first_name",
        "last_name",
        "contact_number",
        "email",
        "password",
        "is_verified",
        "marketing_opt_in",
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "user",
        "address_type",
        "full_name",
        "phone_number",
        "address_line1",
        "address_line2",
        "city",
        "state",
        "postal_code",
        "country",
        "is_default",
    )
    list_filter = ("created_at", "updated_at", "user", "is_default")
    date_hierarchy = "created_at"


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "name",
        # "slug",
        "description",
        "parent_category",
    )
    list_filter = ("created_at", "updated_at", "parent_category")
    # prepopulated_fields = {"slug": ["name"]}
    date_hierarchy = "created_at"


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "name",
        "description",
        "logo",
    )
    list_filter = ("created_at", "updated_at")
    date_hierarchy = "created_at"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "name",
        "description",
        "category",
        "brand",
        "price",
        "compare_at_price",
        "is_available",
        "meta_title",
        "meta_description",
        "keywords",
        "weight",
        "length",
        "width",
        "height",
        "views_count",
    )
    list_filter = (
        "created_at",
        "updated_at",
        "category",
        "brand",
        "is_available",
    )
    date_hierarchy = "created_at"


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "product",
        "image",
        "alt_text",
        "is_main",
    )
    list_filter = ("created_at", "updated_at", "product", "is_main")
    date_hierarchy = "created_at"


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "product",
        "color",
        "size",
        "material",
        "sku",
        "barcode",
        "price_override",
        "stock_quantity",
        "is_available",
        "variant_weight",
        "variant_length",
        "variant_width",
        "variant_height",
    )
    list_filter = ("created_at", "updated_at", "product", "is_available")
    date_hierarchy = "created_at"


@admin.register(InventoryAdjustment)
class InventoryAdjustmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "product_variant",
        "adjustment_type",
        "quantity_changed",
        "reason",
        "adjusted_by",
        "adjustment_date",
    )
    list_filter = (
        "created_at",
        "updated_at",
        "product_variant",
        "adjusted_by",
        "adjustment_date",
    )
    date_hierarchy = "created_at"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "customer",
        "order_date",
        "status",
        "total_amount",
        "shipping_cost",
        "discount_amount",
        "coupon_code_used",
        "shipping_address",
        "billing_address",
        "payment_status",
        "transaction_id",
        "payment_method",
        "tracking_number",
        "shipping_carrier",
        "tracking_url",
        "customer_notes",
        "admin_notes",
        "refund_amount",
        "refund_reason",
        "refunded_at",
    )
    list_filter = (
        "created_at",
        "updated_at",
        "customer",
        "order_date",
        "shipping_address",
        "billing_address",
        "refunded_at",
    )
    date_hierarchy = "created_at"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "order",
        "product",
        "product_variant",
        "quantity",
        "price_at_purchase",
        "product_name_snapshot",
        "variant_details_snapshot",
        "sku_snapshot",
    )
    list_filter = (
        "created_at",
        "updated_at",
        "order",
        "product",
        "product_variant",
    )
    date_hierarchy = "created_at"


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "updated_at", "user", "session_key")
    list_filter = ("created_at", "updated_at", "user")
    date_hierarchy = "created_at"


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "cart",
        "product",
        "product_variant",
        "quantity",
    )
    list_filter = (
        "created_at",
        "updated_at",
        "cart",
        "product",
        "product_variant",
    )
    date_hierarchy = "created_at"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "product",
        "customer",
        "rating",
        "comment",
        "is_approved",
    )
    list_filter = (
        "created_at",
        "updated_at",
        "product",
        "customer",
        "is_approved",
    )
    date_hierarchy = "created_at"


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "name",
        "slug",
        "description",
        "is_featured",
    )
    list_filter = ("created_at", "updated_at", "is_featured")
    raw_id_fields = ("products",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ["name"]}
    date_hierarchy = "created_at"


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "code",
        "description",
        "discount_type",
        "discount_value",
        "minimum_order_amount",
        "is_active",
        "valid_from",
        "valid_until",
        "usage_limit",
        "used_count",
        "per_user_limit",
    )
    list_filter = (
        "created_at",
        "updated_at",
        "is_active",
        "valid_from",
        "valid_until",
    )
    raw_id_fields = ("applicable_products", "applicable_categories")
    date_hierarchy = "created_at"


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "updated_at", "customer")
    list_filter = ("created_at", "updated_at", "customer")
    raw_id_fields = ("products",)
    date_hierarchy = "created_at"


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "title",
        "slug",
        "author",
        "content",
        "featured_image",
        "published_date",
        "is_published",
        "meta_title",
        "meta_description",
    )
    list_filter = (
        "created_at",
        "updated_at",
        "author",
        "published_date",
        "is_published",
    )
    search_fields = ("slug",)
    date_hierarchy = "created_at"


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "customer",
        "order",
        "subject",
        "description",
        "status",
        "priority",
        "assigned_to",
        "closed_at",
    )
    list_filter = (
        "created_at",
        "updated_at",
        "customer",
        "order",
        "assigned_to",
        "closed_at",
    )
    date_hierarchy = "created_at"


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "ticket",
        "sender",
        "message",
        "sent_at",
    )
    list_filter = ("created_at", "updated_at", "ticket", "sender", "sent_at")
    date_hierarchy = "created_at"


@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "name",
        "gateway_type",
        "is_active",
        "api_key",
        "secret_key",
        "publishable_key",
        "settings_json",
    )
    list_filter = ("created_at", "updated_at", "is_active")
    search_fields = ("name",)
    date_hierarchy = "created_at"


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "updated_at",
        "name",
        "description",
        "cost",
        "is_active",
        "min_order_value",
        "max_weight",
        "estimated_delivery_days",
    )
    list_filter = ("created_at", "updated_at", "is_active")
    search_fields = ("name",)
    date_hierarchy = "created_at"
