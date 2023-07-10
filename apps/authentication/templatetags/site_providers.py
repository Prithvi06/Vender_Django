"""
Template tags used during authentication.
"""

from allauth.socialaccount import providers
from allauth.socialaccount.models import SocialApp
from django import template
from django.contrib.sites.shortcuts import get_current_site

register = template.Library()


@register.simple_tag(takes_context=True)
def get_providers(context):
    """
    Returns a list of social apps configured for the current site
    as determind by the current request.  Requries that the site
    middleware be installed.

    Usage: `{% get_providers as socialaccount_providers %}`

    Then within the template context, `socialaccount_providers` will hold
    a list of social providers configured for the current site.
    """

    request = context.get("request")
    site = request.site or get_current_site(request)
    return (
        [providers.registry.by_id(app.provider) for app in SocialApp.objects.filter(sites__id=site.id)]
        if site
        else providers.registry.get_list()
    )
