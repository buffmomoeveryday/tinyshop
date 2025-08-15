from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse
from django_unicorn.components import UnicornView

from tenant.models import Employee


class LoginView(UnicornView):
    template_name = "backoffice/login.html"
    username: str = ""
    password: str = ""

    auth_error: bool = False

    def login_user(self):
        try:
            user = authenticate(
                request=self.request,
                username=self.username,
                password=self.password,
            )

            if not user:
                raise Employee.DoesNotExist

            employee = Employee.objects.get(
                user=user,
                tenant=self.request.tenant,  # type:ignore
            )

            if not user and employee:
                raise Employee.DoesNotExist

            login(request=self.request, user=user)
            self.auth_error = False
            messages.success(request=self.request, message="Login Successfull")
            return redirect(reverse("backoffice:dashboard"))

        except Employee.DoesNotExist as _:
            messages.error(request=self.request, message="Login failed")
            self.auth_error = True
            raise ValidationError({"username": "", "password": ""}, code="invalid")
            raise ValidationError({"username": "", "password": ""}, code="invalid")
