# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from http import HTTPStatus
from typing import Any
from datetime import date
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import CreateView, ListView, UpdateView, View
from organizations.backends import invitation_backend
from organizations.models import Organization, OrganizationUser
from organizations.views.base import ViewFactory
from organizations.views.mixins import AdminRequiredMixin, OrganizationMixin
from apps.authentication.models import User as AuthUser
from django.contrib.auth.hashers import make_password
from .forms import (
    OrganizationUserEditForm,
    OrganizationUserInviteForm,
)
from apps.vendor.models import SurveyToken, VendorSurveyUserAnswer
from apps.vendor.views import get_user_org
import uuid
from django.views.decorators.cache import cache_control
from django.contrib.auth.decorators import login_required

# Create your views here.

base = ViewFactory(Organization)


class OrganizationUserListView(LoginRequiredMixin, OrganizationMixin, AdminRequiredMixin, ListView):
    model = OrganizationUser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["segment"] = ["administrator"]
        return context

    def get_queryset(self):
        return OrganizationUser.objects.filter(organization=self.organization, user__is_invited=False).exclude(
            user__email__endswith="_gracen@gmail.com"
        )


class OrganizationUserInvite(LoginRequiredMixin, OrganizationMixin, AdminRequiredMixin, CreateView):
    template_name = "organizations/organizationuser_form.html"
    form_class = OrganizationUserInviteForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["segment"] = ["administrator"]
        return context

    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        initial["organization"] = self.organization
        initial["user"] = self.request.user
        initial["request"] = self.request
        return initial

    def get_success_url(self) -> str:
        return reverse("org_user_list", kwargs={"organization_pk": self.organization.id})


class OrganizationUserEdit(LoginRequiredMixin, OrganizationMixin, AdminRequiredMixin, UpdateView):
    template_name = "organizations/organizationuser_form.html"
    form_class = OrganizationUserEditForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["segment"] = ["administrator"]
        return context

    def get_object(self):
        # if we don't override this the OrganizationMixin replaces
        # self.instance with Organization which breaks the
        # associated form logic
        org_user_pk = self.kwargs.get("org_user_pk", None)
        return get_object_or_404(OrganizationUser, pk=org_user_pk)

    def get_success_url(self) -> str:
        return reverse("org_user_list", kwargs={"organization_pk": self.organization.id})


class OrganizationUserRemind(LoginRequiredMixin, OrganizationMixin, AdminRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        org_user_pk = kwargs.get("org_user_pk")
        orguser = get_object_or_404(OrganizationUser, pk=org_user_pk)
        host = request.META["HTTP_HOST"]
        invitation_backend().invite_by_email(
            orguser.user.email,
            request=request,
            **{
                "first_name": orguser.user.first_name,
                "last_name": orguser.user.last_name,
                "organization": orguser.organization,
                "domain": {"domain": host, "name": host},
                "scheme": request.scheme,
                "inviter": request.user,
            }
        )

        return HttpResponse(status=HTTPStatus.NO_CONTENT)


class OrganizationUserRemove(LoginRequiredMixin, OrganizationMixin, AdminRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        print("*** OrganizationUserRemove GET")
        org_user_pk = kwargs.get("org_user_pk")
        orguser = get_object_or_404(OrganizationUser, pk=org_user_pk)
        orguser.user.is_active = False
        orguser.user.save()
        orguser.delete()
        print("*** OrganizationUserRemove END")
        return redirect(reverse("org_user_list", kwargs={"organization_pk": self.organization.id}))


def change_password(request):
    if request.method == "POST":
        if not request.user.check_password(request.POST["old_password"]):
            return JsonResponse({"message": "ERROR"})
        user_object = AuthUser.objects.filter(pk=request.user.pk)
        user_object.update(password=make_password(request.POST["new_password"]))
        return JsonResponse({"message": "Password change successfully."})


def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def survey_login(request, token):
    if not is_valid_uuid(token):
        return render(request, "registration/survey_login.html", {"token": False})
    token = SurveyToken.objects.filter(key=token, expiration_date__date__gte=date.today())
    context = {}
    if not token:
        return render(request, "registration/survey_login.html", {"token": False})
    context["org"] = get_user_org(token.first().user)
    context["survey"] = token.first().survey
    context["token"] = True
    if request.method == "POST":
        password = request.POST["password"]
        username = token.first().user.email
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            answer_object = VendorSurveyUserAnswer.objects.filter(survey=token.first().survey)
            if answer_object:
                return HttpResponseRedirect(
                    reverse("djf_surveys:invite-survey-edit", args=[token.first().key, answer_object.first().id])
                )
            return HttpResponseRedirect(
                reverse("djf_surveys:invite-survey-create", args=[token.first().key, token.first().survey.slug])
            )
        else:
            context["msg"] = "Invalid credentials"
            return render(request, "registration/survey_login.html", context)
    return render(request, "registration/survey_login.html", context)


# @cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="account_login")
def survey_logout(request, token):
    logout(request)
    return HttpResponseRedirect(reverse("survey-login", args=[token]))
