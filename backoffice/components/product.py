from django.db.models import Q
from django_unicorn.components import UnicornView

from shop.models import Product, ProductCategory


class ProductView(UnicornView):
    template_name = "backoffice/products.html"
    products = []
    categories = []

    search_category = ""
    search_status: bool | None = None
    search_sort_by = ""
    search_product_name = ""

    def hydrate(self):
        self.products = Product.objects.select_related("category").all()
        self.categories = ProductCategory.objects.all()
        first: Product = self.products.first()

    def search(self):
        q = Q()

        if self.search_category:
            q &= Q(category=self.search_category)

        if self.search_status:
            if self.search_status == "Active":
                q &= Q(is_active=True)
            elif self.search_status == "Draft":
                q &= Q(is_active=False)

        if self.search_product_name:
            q &= Q(name=self.search_product_name)

        if self.search_sort_by:
            sort_field = "name"  # default
            if self.search_sort_by == "Price":
                sort_field = "price"
            elif self.search_sort_by == "Date Created":
                sort_field = "-created_at"
            elif self.search_sort_by == "Stock":
                sort_field = "stock"
            self.products = Product.objects.filter(q).order_by(sort_field)
        else:
            self.products = Product.objects.filter(q)
