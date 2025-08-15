from __future__ import annotations

import datetime
from datetime import date

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import (
    BooleanField,
    CharField,
    DateField,
    EmailField,
    ForeignKey,
    OneToOneField,
)
from django.db.utils import OperationalError, ProgrammingError
from django_tenants.models import DomainMixin, TenantMixin  # type:ignore

User = get_user_model()


class Employee(models.Model):
    first_name: CharField[CharField, CharField] = models.CharField(
        max_length=100, verbose_name="First Name"
    )
    last_name: CharField[CharField, CharField] = models.CharField(
        max_length=100, verbose_name="Last Name"
    )
    username: CharField[CharField, CharField] = models.CharField(
        max_length=100, verbose_name="Username"
    )
    email: EmailField[EmailField, EmailField] = models.EmailField(
        unique=True, verbose_name="Email"
    )
    is_active: BooleanField[BooleanField, BooleanField] = models.BooleanField(
        default=True, verbose_name="Is Active"
    )
    tenant: ForeignKey[Tenant, Tenant] = models.ForeignKey(
        "Tenant",
        on_delete=models.CASCADE,
        related_name="employees",
        verbose_name="Tenant",
    )
    user: OneToOneField[User, User] = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="employee",
        verbose_name="User",
        null=True,
        blank=True,
    )
    is_owner: BooleanField[BooleanField, BooleanField] = models.BooleanField(
        default=False,
        verbose_name="Is Owner",
    )

    @property
    def avatar(self):
        return f"https://gravatar.com/avatar/{self.email}"


class ShopTemplate(models.Model):
    name: CharField[CharField, CharField] = models.CharField(
        verbose_name="Template Name", null=True, blank=True
    )
    slug: models.SlugField[models.SlugField, models.SlugField] = models.SlugField(
        max_length=50,
        unique=True,
        help_text="Used for template directory naming",
    )
    screenshot = models.ImageField(verbose_name="screenshop", null=True, blank=True)

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        verbose_name = "Shop Template"
        verbose_name_plural = "Shop Templates"


class Tenant(TenantMixin):
    name: CharField[CharField, CharField] = models.CharField(verbose_name="Tenant Name")
    paid_until: DateField[DateField, DateField] = models.DateField(
        verbose_name="Paid Until"
    )
    on_trial: BooleanField[BooleanField, BooleanField] = models.BooleanField(
        default=True, verbose_name="On Trial"
    )
    trial_expire_date: DateField[DateField, DateField] = models.DateField(
        verbose_name="trial expire date",
        default=None,
        null=True,
    )
    shop_template: ForeignKey[ShopTemplate, ShopTemplate] = models.ForeignKey(
        ShopTemplate,
        on_delete=models.SET_NULL,
        related_name="template",
        null=True,
    )
    auto_create_schema = True
    auto_drop_schema = True

    def get_template_slug(self):
        try:
            if self.shop_template and self.shop_template.slug:
                return self.shop_template.slug

        except (ProgrammingError, OperationalError):
            return "theme_1"

    def remaining(self):
        today = datetime.date.today()
        if self.trial_expire_date:
            return self.trial_expire_date - today  # type: ignore

    def remaining_days(self):
        if self.trial_expire_date:
            delta = self.trial_expire_date - date.today()
            return max(delta.days, 0)
        return 0

    @property
    def trial_expired(self):
        return self.remaining_days() <= 0

    @property
    def payment_expired(self):
        return self.paid_until < date.today()

    @property
    def expired(self):
        if self.paid_until < date.today():
            return True
        if self.on_trial and self.trial_expire_date < date.today():
            return True

        else:
            return False


class Domain(DomainMixin):
    pass
