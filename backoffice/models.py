from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from core.models import BaseModel


class StripeManager(models.Manager):
    def get_solo(self):
        return self.get_or_create(id=1)[0]


class PaymentSettlement(BaseModel):
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_date = models.DateField(null=True, blank=True)
    settled = models.BooleanField(default=False)
    user_id = models.IntegerField(null=True, blank=True)

    #
    settlement_date = models.DateField(null=True, blank=True)
    task_id = models.CharField(max_length=25, null=True)


class Stripe(BaseModel):
    STRIPE_PUBLIC_KEY = models.CharField(max_length=155, null=True, blank=True)
    STRIPE_SECRET_KEY = models.CharField(max_length=155, null=True, blank=True)

    objects = StripeManager()

    def save(self, *args, **kwargs):
        if not self.pk and Stripe.objects.exists():
            raise ValidationError("There can be only one Stripe instance.")
        return super().save(*args, **kwargs)

    def __str__(self):
        return "Stripe Configuration"
