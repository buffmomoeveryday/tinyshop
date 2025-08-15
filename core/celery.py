# core/celery.py
import os

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
from django.conf import settings
from tenant_schemas_celery.app import CeleryApp as TenantAwareCeleryApp

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
app = TenantAwareCeleryApp("core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
