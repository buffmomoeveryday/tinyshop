from functools import wraps

from django.http import HttpRequest, HttpResponseForbidden
from django.views import View
from tenant.models import Employee


def tenant_login_required(func):
    @wraps(func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        # Use schema_name instead of schema
        user = request.user

        try:
            if not user.is_authenticated:
                return HttpResponseForbidden("Login required")
            employee = Employee.objects.get(user=user, tenant=request.tenant)
        except Employee.DoesNotExist:
            return HttpResponseForbidden("You must be an employee to access this.")

        print("Before calling the function.")
        response = func(request, *args, **kwargs)
        print("After calling the function.")

        return response

    return wrapper


class TenantLoginRequiredMixin(View):
    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return HttpResponseForbidden("Login required")

        try:
            Employee.objects.get(user=user, tenant=request.tenant)
        except Employee.DoesNotExist:
            return HttpResponseForbidden("You must be an employee to access this.")

        print("Before calling the view.")
        response = super().dispatch(request, *args, **kwargs)
        print("After calling the view.")

        return response
