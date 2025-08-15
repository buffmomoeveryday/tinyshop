# type:ignore
from django.shortcuts import get_object_or_404
from django_unicorn.views import UnicornView

from shop.models import Cart, CartItem, Product, ProductVariant


class CartView(UnicornView):
    template_name = "cart/cart.html"
    cart: Cart | None = None

    def hydrate(self):
        self.cart, created = Cart.objects.get_or_create(user=self.request.customer)

    def remove_from_cart(self, cart_item_id):
        print("called")
        if not self.cart:
            return

        try:
            cart_item = self.cart.items.get(id=cart_item_id)
            product_name = cart_item.product.name
            cart_item.delete()

        except CartItem.DoesNotExist:
            # Optional: Add an error message
            if hasattr(self, "parent") and hasattr(self.parent, "call"):
                self.parent.call("showMessage", "Item not found in cart", "error")

    def increment_product(self, cart_item_id):
        """Increase quantity of a cart item by 1"""
        if not self.cart:
            return

        try:
            cart_item = self.cart.items.get(id=cart_item_id)
            cart_item.quantity += 1
            cart_item.save()
        except CartItem.DoesNotExist:
            pass

    def decrement_product(self, cart_item_id):
        """Decrease quantity of a cart item by 1, remove if quantity becomes 0"""
        if not self.cart:
            return

        try:
            cart_item = self.cart.items.get(id=cart_item_id)
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                # Remove item if quantity would be 0
                self.remove_from_cart(cart_item_id)
        except CartItem.DoesNotExist:
            pass

    def update_quantity(self, cart_item_id, new_quantity):
        """Update the quantity of a cart item to a specific value"""
        if not self.cart:
            return

        try:
            new_quantity = int(new_quantity)
            if new_quantity <= 0:
                self.remove_from_cart(cart_item_id)
                return

            cart_item = self.cart.items.get(id=cart_item_id)
            cart_item.quantity = new_quantity
            cart_item.save()

        except (CartItem.DoesNotExist, ValueError):
            pass

    def add_to_cart(self, product_id, variant_id=None, quantity=1):
        """Add a product (with optional variant) to the cart"""
        if not self.cart:
            return

        try:
            product = get_object_or_404(Product, id=product_id)
            variant = None

            if variant_id:
                variant = get_object_or_404(
                    ProductVariant, id=variant_id, product=product
                )

            # Check if item already exists in cart
            cart_item, created = self.cart.items.get_or_create(
                product=product,
                product_variant=variant,
                defaults={"quantity": quantity},
            )

            if not created:
                # Item already exists, increase quantity
                cart_item.quantity += quantity
                cart_item.save()

        except (Product.DoesNotExist, ProductVariant.DoesNotExist):
            pass

    def clear_cart(self):
        """Remove all items from the cart"""
        if self.cart:
            self.cart.clear()

    def get_cart_summary(self):
        """Get cart summary data for display"""
        if not self.cart:
            return {"total": 0, "count": 0, "items": []}

        return {
            "total": self.cart.get_cart_total(),
            "count": self.cart.cart_count(),
            "items": self.cart.items.all(),
        }
