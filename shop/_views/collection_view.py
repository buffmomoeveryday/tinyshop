from django.http import HttpRequest
from django.shortcuts import render

from shop.models import Collection


def collection_views(request: HttpRequest):
    collection = Collection.objects.all()
    return render(request=request, template_name="")
