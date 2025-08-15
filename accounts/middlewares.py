# accounts/middleware.py

from .authentication import get_logged_in_customer


class CustomerAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.customer = get_logged_in_customer(request)
        return self.get_response(request)
