from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMessage
from organizations.backends.defaults import InvitationBackend

from .forms import UserRegistrationForm


class GracenInvitationBackend(InvitationBackend):
    success_url = settings.INVITATION_SUCCESS_URL
    form_class = UserRegistrationForm

    def get_success_url(self):
        return self.success_url

    def email_message(self, user, subject_template, body_template, sender=None, message_class=EmailMessage, **kwargs):
        result = super().email_message(user, subject_template, body_template, sender, message_class, **kwargs)
        result.content_subtype = "html"
        return result

    def activate_view(self, request, user_id, token):
        """
        If the user+token is valid then stuff the token into the session so
        that it can be used later by the pre_social_login signal in order
        to connect the site user to a SocialAccount.
        """

        try:
            user = self.user_model.objects.get(id=user_id, is_active=False)
            if PasswordResetTokenGenerator().check_token(user, token):
                request.session["activation_token"] = f"{user_id}-{token}"
            print(f"Request Session activation_token set to {token}")
        except self.user_model.DoesNotExist:
            request.session["activation_token"] = None
            print("Request Session activation_token set to None")

        return super().activate_view(request, user_id, token)
