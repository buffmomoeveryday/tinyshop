# type:ignore

import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy

from tenant.models import Employee

logger = logging.getLogger(__name__)


##################
# Authentication
##################
def login_tenant(request: HttpRequest):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            user = authenticate(request=request, username=username, password=password)
            if not user:
                raise Employee.DoesNotExist

            employee = Employee.objects.get(user=user, tenant=request.tenant)

            if not user and employee:
                raise Employee.DoesNotExist

            login(request=request, user=user)
            messages.success(request=request, message="Login Successfull")
            return redirect(reverse("backoffice:dashboard"))

        except Employee.DoesNotExist as _:
            messages.error(request=request, message="Login failed")
            return redirect(reverse("backoffice:login-tenant"))

    return render(request=request, template_name="backoffice/auth/login.html")


def logout_tenant(request: HttpRequest):
    logout(request=request)
    return redirect(reverse_lazy("backoffice:login-tenant"))
