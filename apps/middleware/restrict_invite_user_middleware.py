from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.urls import reverse, resolve
from django.utils.deprecation import MiddlewareMixin


class RestrictInviteMemberMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            if request.user.email.endswith("_gracen@gmail.com") and request.user.is_invited:
                url_name = resolve(request.path).view_name.split(".")[-1]
                if url_name not in [
                    "djf_surveys:invite-survey-edit",
                    "djf_surveys:invite-survey-create",
                    "djf_surveys:invite_questionnarie_redirect",
                    "survey-logout",
                    "djf_surveys:question_document_view",
                ]:
                    logout(request)
                    return HttpResponseRedirect(reverse("account_login"))
