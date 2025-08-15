from django_unicorn.views import UnicornView


class Profile(UnicornView):
    template_name = "profile/profile.html"
