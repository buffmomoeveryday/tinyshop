# accounts/backends.py
from django.contrib.auth.backends import BaseBackend
from django.http import HttpRequest

from shop.models import Customer

SESSION_CUSTOMER_KEY = "_auth_customer_id"


class CustomerBackend(BaseBackend):
    """
    Authenticate using Customer model by email and a custom password check.
    """

    def authenticate(self, request, email=None, password=None, **kwargs):
        if email is None or password is None:
            return None

        try:
            customer = Customer.objects.get(email=email)
        except Customer.DoesNotExist:
            return None

        password_valid = customer.check_password_user(password)
        if password_valid:
            return customer

        return None

    def get_user(self, user_id):
        try:
            customer = Customer.objects.get(pk=user_id)
            return customer
        except Customer.DoesNotExist:
            return None


def customer_login(request: HttpRequest, customer: Customer) -> None:
    """
    Log in the customer manually by setting session data.
    """
    request.session[SESSION_CUSTOMER_KEY] = str(customer.pk)
    request.customer = customer  # Optional convenience


def get_logged_in_customer(request):
    customer_id = request.session.get(SESSION_CUSTOMER_KEY)
    if customer_id:
        try:
            return Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return None
    return None


def customer_logout(request):
    request.session.pop(SESSION_CUSTOMER_KEY, None)
    request.customer = None
