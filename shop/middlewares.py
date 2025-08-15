# middleware.py
import time

from accounts.authentication import SESSION_CUSTOMER_KEY
from shop.models import Customer

from .utils import log_customer_event


class CustomerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        customer_id = request.session.get(SESSION_CUSTOMER_KEY)
        if customer_id:
            try:
                request.customer = Customer.objects.get(pk=customer_id)
            except Customer.DoesNotExist:
                request.customer = None
        else:
            request.customer = None

        response = self.get_response(request)
        return response


class CustomerActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if "/backoffice/" in request.path:
            return self.get_response(request)

        if getattr(request, "customer", None):
            now = time.time()
            last_visit = request.session.get("last_visit_timestamp")

            if last_visit and request.user.is_authenticated:
                session_gap = now - last_visit
                if 0 < session_gap < 1800:
                    log_customer_event(
                        customer=request.customer,
                        event_type="time_spent",
                        metadata={"seconds": round(session_gap)},
                        request=request,
                    )

            request.session["last_visit_timestamp"] = now

        response = self.get_response(request)

        if getattr(request, "customer", None):
            log_customer_event(
                customer=request.customer, event_type="page_view", request=request
            )

        return response
