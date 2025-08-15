from shop.models import CustomerEvent


def log_customer_event(customer=None, event_type="", metadata=None, request=None):
    if not event_type:
        raise ValueError("event_type is required")

    data = metadata or {}
    event = CustomerEvent.objects.create(
        customer=customer,
        event_type=event_type,
        path=request.path if request else data.get("path", ""),
        method=request.method if request else data.get("method", ""),
        ip_address=get_client_ip(request) if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "") if request else None,
        referrer=request.META.get("HTTP_REFERER", "") if request else None,
        metadata=data,
    )
    return event


def get_client_ip(request):
    """Get IP address from request headers."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip
