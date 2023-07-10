from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator

user_model = get_user_model()


class GracenSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a
        social provider, but before the login is actually processed
        (and before the pre_social_login signal is emitted).

        We're trying to solve different use cases:
        - social account already exists, just go on
        - social account has no email or email is unknown, just go on
        - social account's email exists, link social account to existing user
        """

        # Ignore existing social accounts, just do this stuff for new ones
        if sociallogin.is_existing:
            return

        # Find the app user tied to the socialaccount email
        email = (
            sociallogin.email_addresses[0].email
            if sociallogin.email_addresses
            else sociallogin.account.extra_data.get("userPrincipalName")
        )
        user = user_model.objects.filter(email__iexact=email).first()
        if not user:
            return

        # if the session token doesn't exist, isn't for the current user,
        # or isn't valid then bail out
        complete_token = request.session.get("activation_token") or ""
        if not complete_token:
            return

        token_user_id, token = complete_token.split("-", 1)
        if (
            not token_user_id
            or not token
            or str(user.id) != token_user_id
            or not PasswordResetTokenGenerator().check_token(user, token)
        ):
            request.session["activation_token"] = None
            return

        # Activate the user and tie them to the provided socialaccount
        sociallogin.connect(request, user)
        user.is_active = True
        user.save()
