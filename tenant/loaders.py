# template_loader.py (create this as a separate file)
import os

from django.conf import settings
from django.db import connection
from django.template import Origin, TemplateDoesNotExist
from django.template.loaders.base import Loader
from icecream import ic  # type:ignore


class TenantTemplateLoader(Loader):
    def get_template_sources(self, template_name, skip=None):
        """Generate template sources based on tenant's shop template"""
        try:
            tenant = connection.tenant  # type:ignore

            template_dirs = getattr(settings, "TEMPLATES", [{}])[0].get("DIRS", [])
            for base_dir in template_dirs:
                if not tenant or tenant.schema_name == "public":
                    shared_template_path = os.path.join(
                        base_dir, "shared", template_name
                    )

                    if os.path.exists(shared_template_path):
                        yield Origin(
                            name=shared_template_path,
                            template_name=template_name,
                            loader=self,
                        )
                    else:
                        pass

                    continue

                template_identifier = tenant.get_template_slug()
                tenant_template_path = os.path.join(
                    base_dir,
                    "tenant",
                    "shop_templates",
                    template_identifier,
                    template_name,
                )

                if os.path.exists(tenant_template_path):
                    yield Origin(
                        name=tenant_template_path,
                        template_name=template_name,
                        loader=self,
                    )
                else:
                    pass

                default_template_path = os.path.join(
                    base_dir,
                    "tenant",
                    "shop",
                    template_name,
                )

                if os.path.exists(default_template_path):
                    yield Origin(
                        name=default_template_path,
                        template_name=template_name,
                        loader=self,
                    )
                else:
                    pass

        except Exception as e:
            import traceback

            ic(f"🚨 Exception in TenantTemplateLoader: {e}")
            ic(f"Traceback: {traceback.format_exc()}")
            return

    def get_contents(self, origin):
        """Read template file contents"""
        try:
            with open(origin.name, encoding=self.engine.file_charset) as fp:
                content = fp.read()

                return content
        except (FileNotFoundError, IOError) as e:
            ic(f"Error: {e}")
            raise TemplateDoesNotExist(origin)
