from django_unicorn.components import UnicornView
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.core.exceptions import ValidationError

from icecream import ic


class LoginTenantView(UnicornView):
    template_name = "auth/login-tenant.html"
    username: str = ""
    password: str = ""

    def mount(self):
        ic(self.request.user)
        return super().mount()

    def login_tenant(self):
        ic(self.username)
        ic(self.password)
        if not self.username or not self.password:
            messages.error(self.request, "Username and password errors are")
            raise ValidationError(
                {
                    "username": "username",
                    "password": "error",
                },
                code="invalid",
            )
        else:
            user = authenticate(
                self.request,
                username=self.username,
                password=self.password,
            )
            ic(user)
            if user is not None:
                login(self.request, user)
                ic("logged in user", user)
            else:
                messages.error(self.request, "Invalid username or password")
                raise ValidationError(
                    {
                        "username": "Invalid username or password",
                        "password": "Invalid username or password",
                    },
                    code="invalid",
                )
