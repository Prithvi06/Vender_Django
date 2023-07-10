# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.apps import AppConfig
from django.apps import apps as global_apps
from django.conf import settings
from django.core.management.color import no_style
from django.db import DEFAULT_DB_ALIAS, connections, router
from django.db.models.signals import post_migrate


def register_default_sites(sender, **kwargs):
    """Post Migration callback used to register default Site entries."""
    ensure_site_is_registered("example.com", "example.com", 1)
    ensure_site_is_registered("stage.gracen.io", "Gracen (stage)")
    ensure_site_is_registered("testbank1.gracen.io", "Gracen TestBank-1")
    ensure_site_is_registered("testmortgage1.gracen.io", "Gracen TestMortgage-1")
    ensure_site_is_registered("app.gracen.io", "Gracen")


def ensure_site_is_registered(domain: str, name: str, desired_id: int = None) -> None:
    """Ensure a given Site entry exists and creates it if it does not."""
    from django.contrib.sites.models import Site

    if desired_id and not Site.objects.filter(pk=desired_id).exists():
        # update an item with the desired id
        Site.objects.create(id=desired_id, domain=domain, name=name or domain)
    elif desired_id:
        # create an item with the desired id
        site = Site.objects.get(pk=desired_id)
        site.domain = domain
        site.name = name or domain
        site.save()
    elif not Site.objects.filter(domain__iexact=domain).exists():
        # create an item with the next sequence id
        Site.objects.create(domain=domain, name=name or domain)

    if desired_id:
        # We set an explicit pk instead of relying on auto-incrementation,
        # so we need to reset the database sequence.
        using = DEFAULT_DB_ALIAS
        sequence_sql = connections[using].ops.sequence_reset_sql(no_style(), [Site])
        if sequence_sql:
            with connections[using].cursor() as cursor:
                for command in sequence_sql:
                    cursor.execute(command)


class VendorConfig(AppConfig):
    """Vendor AppConfig"""

    name = "apps.vendor"
    label = "vendor"

    def ready(self) -> None:
        post_migrate.connect(register_default_sites, sender=self)
