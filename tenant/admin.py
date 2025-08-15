from django.contrib import admin

from .models import Domain, Employee, ShopTemplate, Tenant

# Register your models here.


admin.site.register(Tenant)
admin.site.register(Domain)
admin.site.register(ShopTemplate)
admin.site.register(Employee)
