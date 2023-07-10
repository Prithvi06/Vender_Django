# -*- encoding: utf-8 -*-
"""
Copyright (c) 2021 - present Vendor
"""

from django.apps import apps
from django.contrib import admin

# Register your models here.
for model in apps.get_app_config("vendor").get_models():
    admin.site.register(model)
