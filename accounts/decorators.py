from urllib.parse import urlencode

from django.shortcuts import redirect
from django.urls import reverse_lazy


def customer_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.customer:
            login_url = reverse_lazy("shop:login")
            next_url = request.get_full_path()
            redirect_url = f"{login_url}?{urlencode({'next': next_url})}"
            return redirect(redirect_url)
        return view_func(request, *args, **kwargs)

    return wrapper
