import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render

from shop.models import Brand, Product, ProductCategory, ProductImage, ProductVariant
from tenant.decorators import tenant_login_required

logger = logging.getLogger(__name__)


@tenant_login_required
def products(request: HttpRequest):
    products = Product.objects.select_related("product_category").all()
    context = {"products": products}
    return render(
        request=request,
        template_name="backoffice/products.html",
        context=context,
    )


@tenant_login_required
def product_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id)

    if request.method == "GET":
        variants = product.variants.all()  # type:ignore
        images = product.images.all()  # type:ignore
        return render(
            request=request,
            template_name="backoffice/products/product_detail.html",
            context={
                "product": product,
                "variants": variants,
                "images": images,
            },
        )

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_variant":
            variant_data = {
                "product": product,
                "sku": request.POST.get("sku", ""),
                "barcode": request.POST.get("barcode", ""),
                "color": request.POST.get("color", ""),
                "size": request.POST.get("size", ""),
                "material": request.POST.get("material", ""),
                "price_override": request.POST.get("price_override") or None,
                "stock_quantity": int(request.POST.get("stock_quantity", 0)),
                "is_available": request.POST.get("is_available") == "on",
                "weight": request.POST.get("variant_weight") or None,
                "length": request.POST.get("variant_length") or None,
                "width": request.POST.get("variant_width") or None,
                "height": request.POST.get("variant_height") or None,
            }

            # Validate required fields
            if not variant_data["sku"]:
                messages.error(request, "SKU is required")
            else:
                try:
                    # Check if SKU already exists
                    if product.variants.filter(sku=variant_data["sku"]).exists():  # type:ignore
                        messages.error(
                            request,
                            f"SKU '{variant_data['sku']}' already exists for this product",
                        )
                    else:
                        # Convert string values to appropriate types
                        if variant_data["price_override"]:
                            variant_data["price_override"] = float(
                                variant_data["price_override"]
                            )
                        if variant_data["weight"]:
                            variant_data["weight"] = float(variant_data["weight"])
                        if variant_data["length"]:
                            variant_data["length"] = float(variant_data["length"])
                        if variant_data["width"]:
                            variant_data["width"] = float(variant_data["width"])
                        if variant_data["height"]:
                            variant_data["height"] = float(variant_data["height"])

                        # Create the variant (assuming you have a ProductVariant model)
                        ProductVariant.objects.create(**variant_data)
                        messages.success(
                            request,
                            f"Variant with SKU '{variant_data['sku']}' added successfully",
                        )

                except (ValueError, TypeError) as e:
                    messages.error(request, f"Invalid data provided: {str(e)}")
                except Exception as e:
                    messages.error(request, f"Error creating variant: {str(e)}")

        elif action == "remove_variant":
            variant_id = request.POST.get("variant_id")
            try:
                variant = get_object_or_404(
                    ProductVariant, pk=variant_id, product=product
                )
                sku = variant.sku
                variant.delete()
                messages.success(
                    request, f"Variant with SKU '{sku}' removed successfully"
                )
            except Exception as e:
                messages.error(request, f"Error removing variant: {str(e)}")

        # Redirect to avoid re-submission on refresh
        return redirect("product_detail", product_id=product_id)


@tenant_login_required
def products_add(request):
    context = {
        "brands": Brand.objects.all(),
        "categories": ProductCategory.objects.all(),
    }

    if request.method == "POST" and request.FILES:
        product = Product()
        product.name = request.POST.get("name")
        product.price = request.POST.get("price")
        product.description = request.POST.get("description")
        product.brand = Brand.objects.filter(id=request.POST.get("brand")).first()
        product.category = ProductCategory.objects.filter(
            id=request.POST.get("product_category")
        ).first()
        product.compare_at_price = request.POST.get("compare_at_price")
        product.is_available = request.POST.get("is_available") == "on"
        product.meta_title = request.POST.get("meta_title")
        product.meta_description = request.POST.get("meta_description")
        product.keywords = request.POST.get("keywords")
        product.weight = request.POST.get("weight")
        product.length = request.POST.get("length")
        product.width = request.POST.get("width")
        product.height = request.POST.get("height")

        product.save()

        main_image = request.FILES.get("main_image")
        secondary_images = request.FILES.get("images")

        product_image = ProductImage.objects.create(
            product=product,
            image=main_image,
            alt_text=product.name,
            is_main=True,
        )

        for image in secondary_images:
            ProductImage.objects.create(
                product=product,
                image=image,
                alt_text=product.name,
                is_main=False,
            )

    return render(
        request=request,
        template_name="backoffice/products/productadd.html",
        context=context,
    )


@tenant_login_required
def htmx_search_products(request):
    if request.method == "GET":
        from django.db.models import Q

        search_query = request.GET.get("search", "").strip()
        category_filter = request.GET.get("category", "")
        status_filter = request.GET.get("status", "")
        sort_by = request.GET.get("sort", "name")  # Default sorting

        q = Q()

        if search_query:
            q &= Q(name__icontains=search_query) | Q(
                category__name__icontains=search_query
            )

        if category_filter and category_filter != "all":
            q &= Q(category__id=category_filter)

        if status_filter and status_filter != "all":
            q &= Q(status=status_filter)

        # Define allowed sort fields to prevent injection
        allowed_sort_fields = [
            "name",
            "-name",
            "price",
            "-price",
            "created_at",
            "-created_at",
        ]
        sort_field = sort_by if sort_by in allowed_sort_fields else "name"

        products = Product.objects.filter(q).order_by(sort_field)

        context = {"products": products}
        return render(
            request=request,
            template_name="backoffice/components/product_search_results.html",
            context=context,
        )


@tenant_login_required
def htmx_add_brand(request):
    if request.method == "POST":
        brand_name = request.POST.get("brand_name")
        brand_description = request.POST.get("brand_description")

        brand_logo = []

        if request.FILES:
            brand_logo = request.FILES.get("brand_logo", None)

        Brand.objects.create(
            name=brand_name,
            description=brand_description,
            logo=brand_logo if brand_logo else None,
        )
        brands = Brand.objects.all()
        context = {"brands": brands}
        return render(
            request=request,
            template_name="backoffice/components/brand_dropdown.html",
            context=context,
        )


@tenant_login_required
def htmx_add_category(request):
    if request.method == "POST":
        category_name = request.POST.get("category_name")
        parent_category = request.POST.get("parent_category_id")
        description = request.POST.get("description")

        ProductCategory.objects.create(
            name=category_name,
            parent_category=parent_category if parent_category else None,
            description=description,
        )

        return render(
            request=request,
            template_name="backoffice/components/category_dropdown.html",
            context={"categories": ProductCategory.objects.all()},
        )

    if request.method == "GET":
        return render(
            request=request,
            template_name="backoffice/components/category_dropdown.html",
            context={"categories": ProductCategory.objects.all()},
        )


@tenant_login_required
def htmx_product_variant_add(request, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, pk=product_id)

        sku = request.POST.get("sku", "").strip()
        barcode = request.POST.get("barcode", "").strip()
        color = request.POST.get("color", "").strip()
        size = request.POST.get("size", "").strip()
        material = request.POST.get("material", "").strip()
        stock_quantity = int(request.POST.get("stock_quantity", 0)) or 0
        is_available = request.POST.get("is_available") in ["on", "true", "1"]

        # Convert optional fields to Decimal or None
        def to_decimal_or_none(value):
            try:
                return Decimal(value) if value else None
            except (InvalidOperation, ValueError):
                return None

        price_override = to_decimal_or_none(request.POST.get("price_override"))
        variant_weight = to_decimal_or_none(request.POST.get("variant_weight"))
        variant_length = to_decimal_or_none(request.POST.get("variant_length"))
        variant_width = to_decimal_or_none(request.POST.get("variant_width"))
        variant_height = to_decimal_or_none(request.POST.get("variant_height"))

        # Save variant
        ProductVariant.objects.create(
            product=product,
            sku=sku or None,
            barcode=barcode or None,
            color=color or None,
            size=size or None,
            material=material or None,
            price_override=price_override,
            stock_quantity=stock_quantity,
            is_available=is_available,
            variant_weight=variant_weight,
            variant_length=variant_length,
            variant_width=variant_width,
            variant_height=variant_height,
        )

        variants = ProductVariant.objects.filter(product=product)

        return render(
            request=request,
            template_name="backoffice/components/variant-table.html",
            context={"variants": variants},
        )


@tenant_login_required
def htmx_product_variant_edit(request, variant_id, product_id):
    action = request.headers.get("Action ")

    if request.method == "POST":
        product = get_object_or_404(Product, pk=product_id)

        if action == "FormRequest":
            return render(
                request=request,
                template_name="products/variant_update_form.html",
                context={
                    "product": product,
                },
            )

        sku = request.POST.get("sku", "").strip()
        barcode = request.POST.get("barcode", "").strip()
        color = request.POST.get("color", "").strip()
        size = request.POST.get("size", "").strip()
        material = request.POST.get("material", "").strip()
        stock_quantity = int(request.POST.get("stock_quantity", 0)) or 0
        is_available = request.POST.get("is_available") in ["on", "true", "1"]

        # Convert optional fields to Decimal or None
        def to_decimal_or_none(value):
            try:
                return Decimal(value) if value else None
            except (InvalidOperation, ValueError):
                return None

        price_override = to_decimal_or_none(request.POST.get("price_override"))
        variant_weight = to_decimal_or_none(request.POST.get("variant_weight"))
        variant_length = to_decimal_or_none(request.POST.get("variant_length"))
        variant_width = to_decimal_or_none(request.POST.get("variant_width"))
        variant_height = to_decimal_or_none(request.POST.get("variant_height"))

        # Save variant
        ProductVariant.objects.update(
            product=product,
            sku=sku or None,
            barcode=barcode or None,
            color=color or None,
            size=size or None,
            material=material or None,
            price_override=price_override,
            stock_quantity=stock_quantity,
            is_available=is_available,
            variant_weight=variant_weight,
            variant_length=variant_length,
            variant_width=variant_width,
            variant_height=variant_height,
        )

        variants = ProductVariant.objects.filter(product=product)

        return render(
            request=request,
            template_name="backoffice/components/variant-table.html",
            context={"variants": variants},
        )


@tenant_login_required
def htmx_product_variant_remove(request, variant_id):
    if request.method == "POST":
        variant = ProductVariant.objects.get(id=variant_id)
        variant.delete()
        variants = ProductVariant.objects.filter(product__id=variant.product.id)
        context = {"variants": variants}
        return render(
            request=request,
            template_name="backoffice/components/variant-table.html",
            context=context,
        )


def htmx_product_edit(request: HttpRequest, product_id: int):
    headers = request.headers.get("Type")

    if request.method == "POST":
        # Get all form data
        product_category = request.POST.get("product_category")
        brand = request.POST.get("brand")
        name = request.POST.get("name")
        sku = request.POST.get("sku")
        price = request.POST.get("price")
        compare_at = request.POST.get("compare_at_price")
        weight = request.POST.get("weight")
        length = request.POST.get("length")
        width = request.POST.get("width")
        height = request.POST.get("height")
        meta_title = request.POST.get("meta_title")
        keywords = request.POST.get("keywords")
        meta_description = request.POST.get("meta_description")
        is_available = request.POST.get("is_available")
        description = request.POST.get("description")

        product = Product.objects.get(pk=product_id)

        if name:
            product.name = name.strip()

        # if sku:
        #     product.sku = sku.strip()
        # else:
        #     product.sku = None

        if product_category:
            product.category_id = int(product_category)  # type:ignore
        else:
            product.category_id = None  # type:ignore

        if brand:
            product.brand_id = int(brand)  # type:ignore
        else:
            product.brand_id = None  # type:ignore

        if price:
            product.price = float(price)

        if compare_at:
            product.compare_at_price = float(compare_at)
        else:
            product.compare_at_price = None

        if weight:
            product.weight = float(weight)
        else:
            product.weight = None

        if length:
            product.length = float(length)
        else:
            product.length = None

        if width:
            product.width = float(width)
        else:
            product.width = None

        if height:
            product.height = float(height)
        else:
            product.height = None

        # Update SEO fields
        if meta_title:
            product.meta_title = meta_title.strip()
        else:
            product.meta_title = None

        if keywords:
            product.keywords = keywords.strip()
        else:
            product.keywords = None

        if meta_description:
            product.meta_description = meta_description.strip()
        else:
            product.meta_description = None

        product.is_available = is_available == "True"

        if description:
            product.description = description.strip()
        else:
            product.description = None

        # Save the product
        product.save()
        product.refresh_from_db()

        return render(
            request=request,
            template_name="backoffice/products/product_info.html",
            context={
                "product": product,
            },
        )

    if request.method == "GET":
        product = Product.objects.get(pk=product_id)

        if headers == "Cancel":
            return render(
                request=request,
                template_name="backoffice/products/product_info.html",
                context={
                    "product": product,
                },
            )

        return render(
            request=request,
            template_name="backoffice/products/product_info_form.html",
            context={
                "product": product,
                "categories": ProductCategory.objects.all(),
                "brands": Brand.objects.all(),
            },
        )
