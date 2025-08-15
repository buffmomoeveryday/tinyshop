from django_pony_express.services.base import BaseEmailService


class WelcomeEmail(BaseEmailService):
    template_name = "landing/emails/welcome_email.html"
    template_txt_name = (
        # Path to your email template
        "landing/emails/welcome_email.txt"
    )

    def get_context_data(self, **kwargs):
        return {
            "employee": kwargs.get("employee"),
        }
