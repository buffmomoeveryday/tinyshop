from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from tenant.models import Tenant, Domain, Employee
from django.contrib.auth import get_user_model
import logging


logger = logging.getLogger(__name__)
User = get_user_model()


class TenantService:
    @staticmethod
    @transaction.atomic
    def register_tenant(
        first_name,
        last_name,
        email,
        store_name,
        password,
    ) -> tuple[Tenant, Employee]:
        tenant = Tenant.objects.create(
            name=store_name,
            schema_name=store_name,
            on_trial=True,
            trial_expire_date=timezone.now() + timedelta(days=7),
            paid_until=timezone.now() + timedelta(days=7),
        )

        store_name = store_name.split(" ")[0]
        Domain.objects.create(
            domain=f"{store_name}.localhost", tenant=tenant, is_primary=True
        )

        user = User.objects.create_user(  # type:ignore
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        employee = Employee.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            username=email,
            email=email,
            tenant=tenant,
            is_owner=True,
        )
        return tenant, employee
