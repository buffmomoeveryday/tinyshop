from typing import ClassVar, List

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django_unicorn.components import UnicornView
from icecream import ic

from landing.tasks import create_tenant
from tenant.models import Domain

User = get_user_model()


class RegisterTenantView(UnicornView):
    template_name = "auth/register-tenant.html"
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    domain_name: str = ""
    error: bool = False
    store_name: str = ""
    password: str = ""

    black_listed: ClassVar[List[str]] = ["admin.com", "tinyshop.com"]
    restricted_extensions: ClassVar[List[str]] = [".com", ".in", ".com.np"]

    def register_tenant(self):
        try:
            if not all(
                [
                    self.first_name,
                    self.last_name,
                    self.email,
                    self.domain_name,
                    self.store_name,
                    self.password,
                ]
            ):
                messages.error(self.request, "Please fill in all the details")
                return

            create_tenant.delay(
                first_name=self.first_name,
                last_name=self.last_name,
                email=self.email,
                store_name=self.store_name,
                password=self.password,
            )
            messages.success(
                self.request,
                "Registered successfully. Please check your email",
            )
            return
        except Exception as e:
            self.error = True
            ic(e)
            raise ValidationError(
                {"detail": str(e)},
                code="required",
            )

    def check_domain(self):
        if any(ext in self.domain_name for ext in [".com", ".in", ".com.np"]):
            raise ValidationError(
                {
                    "domain_name": "We only support subdomain now please enter a first name of the domain"
                }
            )

        if self.domain_name in self.black_listed:
            print("validation error")
            raise ValidationError(
                {"domain_name": "Domain name is blacklisted."},
                code="required",
            )

        domain = Domain.objects.filter(domain=self.domain_name).exists()
        if domain:
            raise ValidationError(
                {"domain_name": "Domain Already Exists"}, code="invalid"
            )
