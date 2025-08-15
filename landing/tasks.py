import logging

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from landing.service import TenantService
from tenant.models import Domain, Employee, Tenant

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def create_tenant(
    self,
    first_name,
    last_name,
    email,
    store_name,
    password,
):
    try:
        tenant, employee = TenantService.register_tenant(
            first_name,
            last_name,
            email,
            store_name,
            password,
        )
        send_welcome_email(tenant, employee)

    except Exception as e:
        logger.error(f"Failed to create tenant: {str(e)}")
        raise


def send_welcome_email(tenant: Tenant, employee: Employee):
    subject = f"🎉 Welcome to TinyShop, {employee.first_name}! Your store is ready"
    text_content = render_to_string(
        "emails/welcome_email.txt",
        context={
            "tenant": tenant,
            "employee": employee,
            "domain": Domain.objects.get(tenant=tenant),
        },
    )
    html_content = render_to_string(
        "emails/welcome_email.html",
        context={"tenant": tenant, "employee": employee},
    )
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,  # Changed from text_content to body
        from_email="register@tinyshop.com",
        to=[employee.email],
        headers={"List-Unsubscribe": "<mailto:unsub@example.com>"},
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    msg.send()
