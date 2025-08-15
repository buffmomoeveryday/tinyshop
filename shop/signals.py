# shop/signals.py
from django.db.models.signals import post_delete, post_save

from shop.models import Address, Cart, CartItem, Customer, CustomerEvent, Order
from shop.utils import log_customer_event


def log_customer_change(sender, instance, created=False, **kwargs):
    event_map = {
        Customer: ("Customer registered", "Customer updated profile"),
        Address: ("Address added", "Address updated"),
        Order: ("Order placed", "Order updated"),
        Cart: ("Cart created", "Cart updated"),
        CartItem: ("Item added to cart", "Cart item updated"),
    }

    if sender not in event_map or sender is CustomerEvent:
        return

    created_msg, updated_msg = event_map[sender]
    event_type = created_msg if created else updated_msg

    customer = getattr(instance, "customer", None) or getattr(instance, "user", None)

    if not customer:
        return

    log_customer_event(
        customer=customer,
        event_type=event_type,
        metadata={
            "model": sender.__name__,
            "pk": instance.pk,
            "summary": str(instance),
        },
    )


def log_customer_delete(sender, instance, **kwargs):
    delete_map = {
        Customer: "Customer account deleted",
        Address: "Address removed",
        Order: "Order deleted",
        Cart: "Cart deleted",
        CartItem: "Item removed from cart",
    }

    if sender not in delete_map or sender is CustomerEvent:
        return

    customer = getattr(instance, "customer", None) or getattr(instance, "user", None)
    if not customer:
        return

    log_customer_event(
        customer=customer,
        event_type=delete_map[sender],
        metadata={
            "model": sender.__name__,
            "pk": instance.pk,
            "summary": str(instance),
        },
    )


def register_customer_signals():
    tracked_models = [Customer, Address, Order, Cart, CartItem]
    for model in tracked_models:
        post_save.connect(log_customer_change, sender=model, weak=False)
        post_delete.connect(log_customer_delete, sender=model, weak=False)
