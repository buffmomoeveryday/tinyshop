from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django_unicorn.components import UnicornView

from shop.models import Product, ProductVariant


class ProductDetailView(UnicornView):
    template_name = "backoffice/product/product_detail.html"

    product: Product | None = None
    variants: list[ProductVariant | None] = []

    color: str = ""
    size: str = ""
    material: str = ""
    sku: str = ""
    barcode: str = ""
    price_override: float | None = None
    stock_quantity: int | None = None
    is_available: bool = True
    variant_weight: float | None = None
    variant_length: float | None = None
    variant_width: float | None = None
    variant_height: float | None = None

    def mount(self):
        print("000000")
        print(self.template_name)
        print("000000")

    def printHelo(self):
        print("helo")
        print("helo")
        print("helo")
        print("helo")
        print("helo")

    def hydrate(self):
        product_id = self.kwargs.get("product_id")
        self.product = get_object_or_404(Product, pk=product_id)
        self.variants = list(ProductVariant.objects.filter(product__id=product_id))

    def add_variant(self):
        if not self.product:
            return

        ProductVariant.objects.create(
            product=self.product,
            color=self.color,
            size=self.size,
            material=self.material,
            sku=self.sku,
            barcode=self.barcode,
            price_override=self.price_override,
            stock_quantity=self.stock_quantity or 0,
            is_available=self.is_available,
            weight=self.variant_weight,
            length=self.variant_length,
            width=self.variant_width,
            height=self.variant_height,
        )

        self.color = ""
        self.size = ""
        self.material = ""
        self.sku = ""
        self.barcode = ""
        self.price_override = None
        self.stock_quantity = None
        self.is_available = True
        self.variant_weight = None
        self.variant_length = None
        self.variant_width = None
        self.variant_height = None

        # Refresh product with new variant
        self.product.refresh_from_db()

        return HttpResponseRedirect(self.request.build_absolute_uri())
