import logging
from datetime import datetime
from re import sub

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from landing.service import TenantService
from shop.models import Customer, MarketingEmail
from tenant.models import Domain, Employee, Tenant

logger = logging.getLogger(__name__)


def marketing_email(request: HttpRequest):
    marketing_emails = MarketingEmail.objects.prefetch_related("recipients").order_by(
        "-created_at"
    )
    return render(
        request=request,
        template_name="backoffice/marketing/marketing.html",
        context={
            "marketing_emails": marketing_emails,
        },
    )


def marketing_email_create(request: HttpRequest):
    if request.method == "POST":
        selected_customer_ids = request.POST.getlist("customer_ids[]")
        customers = Customer.objects.filter(id__in=selected_customer_ids)

        subject = request.POST.get("subject", "New Marketing Email")
        body = request.POST.get("body", "")

        # Wrap the body in semantic HTML
        html_body = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{subject}</title>
        </head>
        <body>
            <main>
                {body}
            </main>
            <footer>
                <p>&copy; {datetime.now().year} {request.tenant.schema_name.upper()}</p>
            </footer>
        </body>
        </html>
        """

        if customers.exists():
            email = MarketingEmail.objects.create(subject=subject, body=html_body)
            email.recipients.set(customers)
            email.save()

            msg = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=request.user.email,
                to=list(customers.values_list("email", flat=True)),
            )
            msg.attach_alternative(html_body, "text/html")
            msg.send()

            for customer in customers:
                print(f"Sending email to {customer.email}")

            return redirect("backoffice:marketing-email")

    return render(
        request=request,
        template_name="backoffice/marketing/marketing_create.html",
        context={
            "customers": Customer.objects.all(),
        },
    )
