import base64
import json
import uuid

from django.contrib import messages
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.text import slugify
from django_unicorn.components import UnicornView

from shop.models import Product, ProductCategory, ProductImage


class ProductaddView(UnicornView):
    template_name = "backoffice/products/productadd.html"
    images = ""  # Changed from {} to "" to store JSON string
    images_count = "1"
    main_image = ""
    categories = []

    # product
    name: str = ""
    description: str = ""
    category_id: int | None = None
    brand_id: int | None = None

    price: int | None = None
    compare_at_price: int | None = None

    is_available: bool = False
    meta_title: str | None = None
    meta_description: str | None = None
    keywords: str | None = None

    weight: float | None = None
    length: float | None = None
    width: float | None = None
    height: float | None = None

    category_name: str | None = None
    category_description: str | None = None
    parent_category_id: str | None = None

    variants = {}
    proudct_variant_count = "1"

    # modals
    category_modal: bool = False
    brand_modal: bool = False

    def hydrate(self):
        self.categories = list(ProductCategory.objects.all())

    def mount(self):
        print("Main image:", self.main_image)
        print("Images:", self.images)

    def save_category(self):
        if self.category_name and self.category_description:
            try:
                category = ProductCategory(
                    name=self.category_name,
                    description=self.category_description,
                )

                if self.parent_category_id:
                    parent = ProductCategory.objects.get(pk=self.parent_category_id)
                    category.parent_category = parent

                category.save()

                self.category_modal = False
                self.categories = list(ProductCategory.objects.all())

                # Optionally clear form
                self.category_name = ""
                self.category_description = ""
                self.parent_category_id = None

            except Exception as e:
                messages.error(self.request, f"Error saving category: {str(e)}")
        else:
            messages.error(self.request, "Name and Description Required")

    @transaction.atomic()
    def save(self):
        product = Product.objects.create(
            name=self.name,
            description=self.description,
            category_id=self.category_id,
            brand=self.brand_id,
            price=self.price,
            compare_at_price=self.compare_at_price,
            is_available=self.is_available,
            meta_title=self.meta_title,
            meta_description=self.meta_description,
            keywords=self.keywords,
            weight=self.weight,
            length=self.length,
            width=self.width,
            height=self.height,
            slug=f"{slugify(self.name)}-{str(uuid.uuid4())[:8]}",
        )
        # Handle additional images
        if self.images:
            try:
                # Parse the JSON string to get the list of base64 images
                images_list = json.loads(self.images)
                print(f"Parsed {len(images_list)} additional images")

                for i, image_data in enumerate(images_list):
                    print(f"Processing additional image {i + 1}")
                    product_image = ProductImage()
                    product_image.product = product
                    product_image.image = self.convert_base64(image_data)
                    product_image.is_main = False
                    product_image.save()

            except json.JSONDecodeError as e:
                print(f"Error parsing images JSON: {e}")
                messages.error(
                    self.request, f"Error processing additional images: {str(e)}"
                )
            except Exception as e:
                print(f"Error saving additional images: {e}")
                messages.error(
                    self.request, f"Error saving additional images: {str(e)}"
                )

        if self.main_image:
            try:
                print("Processing main image")
                main_image_model = ProductImage()
                main_image_model.product = product
                main_image_model.image = self.convert_base64(self.main_image)
                main_image_model.is_main = True
                main_image_model.save()
                print("Main image saved successfully")
            except Exception as e:
                print(f"Error saving main image: {e}")
                messages.error(self.request, f"Error saving main image: {str(e)}")

        messages.success(request=self.request, message="Product Added Successfully")

    def convert_base64(self, value):
        """Handle image upload from base64"""
        if value:
            try:
                # Handle data URL format: data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD...
                if "base64," in value:
                    format_part, imgstr = value.split(";base64,")
                    ext = format_part.split("/")[-1]
                    # Handle common image extensions
                    if ext == "jpeg":
                        ext = "jpg"
                else:
                    # If it's just base64 without data URL prefix
                    imgstr = value
                    ext = "jpg"  # default extension

                data = ContentFile(
                    base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}"
                )
                return data
            except Exception as e:
                print(f"Error converting base64 image: {e}")
                return None
        return None
