import traceback

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt

from tenant.models import Domain  # Adjust the import to your app

# Make sure these are defined in your project
from .tasks import create_tenant


def landing_page(request):
    """
    Render the landing page.
    """
    return render(request, "landing/landing.html")


def login_view(request):
    if request.method == "POST":
        user = request.POST.get("username")
        password = request.POST.get("password")
        if not user or password:
            messages.error(request, "Username and password errors are")
            return redirect(reverse("landing:login"))
        else:
            user = authenticate(request=request, username=user, password=password)
            if user is None:
                messages.error(request, "Invalid username or password")
                return redirect(reverse("landing:login"))
            else:
                login(request=request, user=user)
                messages.success(request, "Logged in successfully")
                return redirect(reverse("backoffice:dashboard"))

    return render(request=request, template_name="auth/login.html")


black_listed = ["admin.com", "tinyshop.com"]
restricted_extensions = [".com", ".in", ".com.np"]


black_listed = ["www", "admin", "mail", "shop", "blog"]  # Example blacklist


@csrf_exempt
def register_view(request):
    context = {}
    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")
        contact_number = request.POST.get("contact_number", "")
        store_name = request.POST.get("store_name", "").strip()

        # Initialize error dict
        errors = {}

        # Basic required fields validation
        required_fields = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "password": password,
            "confirm_password": confirm_password,
            "contact_number": contact_number,
            "store_name": store_name,
        }

        for field, value in required_fields.items():
            if not value:
                errors[field] = "This field is required."

        # Password match check
        if password and confirm_password and password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."

        # Generate and validate the domain name from the store name
        if store_name:
            # e.g., "My Awesome Store" becomes "my-awesome-store"
            domain_name = slugify(store_name)

            if domain_name in black_listed:
                # Attach the error to the user-facing field 'store_name'
                errors["store_name"] = "This store name is not allowed."

            if Domain.objects.filter(domain=domain_name).exists():
                errors["store_name"] = "This store name is already taken."

        if errors:
            context["errors"] = errors
            context.update(required_fields)
            return render(request, "auth/register-tenant.html", context)

        try:
            domain_name = slugify(store_name)
            create_tenant.delay(  # type:ignore
                first_name=first_name,
                last_name=last_name,
                email=email,
                store_name=store_name,
                password=password,
            )
            messages.success(
                request, "Registered successfully. Please check your email."
            )
            return redirect(reverse_lazy("shop:login"))

        except Exception as e:
            print(traceback.format_exc())
            context["errors"] = {"non_field_error": f"Registration failed: {str(e)}"}
            context.update(required_fields)
            return render(request, "auth/register-tenant.html", context)

    return render(request, "auth/register-tenant.html")
    return render(request, "auth/register-tenant.html")
