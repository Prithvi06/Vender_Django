"""
Gracen custom session expiration middleware module.
"""

from django.contrib.auth import logout
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

from apps.authentication.models import User

MAX_INACTIVITY_SECONDS = 60 * 60 * 24


class SessionExpiredMiddleware(MiddlewareMixin):  # pylint: disable=too-few-public-methods
    """Gracen custom session expiration middleware."""

    def process_request(self, request):
        """
        Automatically log out a user if their session has been inactive for
        more than MAX_INACTIVITY_SECONDS.
        """

        # bail out if we don't have the needed data
        if not request or not request.user or not request.user.is_authenticated:
            return

        # if DB user is not found logout and exit
        user = User.objects.filter(pk=request.user.pk).first()
        if not user:
            logout(request)
            return

        # if DB user is not active clear last_vist, logout, and exit
        if not user.is_active:
            user.last_visit = None
            user.save()
            logout(request)
            return

        # establish age of last activity
        last_activity = user.last_visit or user.last_login
        now = timezone.now()
        age = (now - last_activity).total_seconds()

        # if age exceeds max value clear last_vist, logout, and exit
        if age > MAX_INACTIVITY_SECONDS:
            user.last_visit = None
            user.save()
            logout(request)
            return

        # update last_vist
        user.last_visit = now
        user.save()
