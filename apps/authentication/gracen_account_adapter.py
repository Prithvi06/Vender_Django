from allauth.account.adapter import DefaultAccountAdapter


class GracenAccountAdapter(DefaultAccountAdapter):
    """
    Adapter to disable allauth new signups
    Use ACCOUNT_ADAPTER = "apps.authentication.gracen_account_adapter.GracenAccountAdapter"

    https://django-allauth.readthedocs.io/en/latest/advanced.html#custom-redirects"""

    def is_open_for_signup(self, request):
        """
        Checks whether or not the site is open for signups.

        Next to simply returning True/False you can also intervene the
        regular flow by raising an ImmediateHttpResponse
        """
        return False
