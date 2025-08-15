from functools import wraps

from django.http import HttpRequest, HttpResponseForbidden
from django.views import View

from tenant.models import Employee


def tenant_login_required(func):
    @wraps(func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        user = request.user
        try:
            if not user.is_authenticated:
                return HttpResponseForbidden("Login required")
            Employee.objects.get(user=user, tenant=request.tenant)
        except Employee.DoesNotExist:
            return HttpResponseForbidden("You must be an employee to access this.")

        response = func(request, *args, **kwargs)

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

        response = super().dispatch(request, *args, **kwargs)

        return response
