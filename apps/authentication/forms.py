# -*- encoding: utf-8 -*-
# pylint: disable=modelform-uses-exclude
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from organizations.backends import invitation_backend
from organizations.models import OrganizationUser

from .models import CreateInvite, DocumentPermission

ROLE_CHOICES = [
    (False, "User"),
    (True, "Admin"),
]

ACTIVE_STATUS_CHOICES = [(False, "Blocked"), (True, "Not Blocked")]


class UserRegistrationForm(UserCreationForm):
    email = forms.CharField(disabled=True, widget=forms.TextInput(attrs={"class": "form-control"}))
    first_name = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"class": "form-control"})
        self.fields["password2"].widget.attrs.update({"class": "form-control"})

    def is_valid(self) -> bool:
        result = super().is_valid()
        if result:
            self.cleaned_data["username"] = self.cleaned_data["email"]
        return result

    class Meta(UserCreationForm.Meta):
        fields = ["email", "first_name", "last_name"]


class OrganizationUserInviteForm(forms.ModelForm):
    """
    Form class for inviting users into an organization.
    """

    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control"}))
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.Select(attrs={"class": "form-control"}))

    class Meta:
        model = CreateInvite
        exclude = ["org"]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            others = OrganizationUser.objects.select_related().filter(user__email__iexact=email)
            if others:
                other_names = [o.organization.name for o in others]
                raise ValidationError(
                    f"User is already a member of other oganization(s); {other_names}", "ambiguous-user-organization"
                )
        return email

    def save(self, *args, **kwargs):
        """
        Save changes to linked user model
        """
        request = self.initial["request"]
        host = request.META["HTTP_HOST"]
        self.instance.user = invitation_backend().invite_by_email(
            self.cleaned_data["email"],
            request=self.initial["request"],
            **{
                "first_name": self.cleaned_data["first_name"],
                "last_name": self.cleaned_data["last_name"],
                "organization": self.initial["organization"],
                "domain": {"domain": host, "name": host},
                "scheme": request.scheme,
                "inviter": self.initial["user"],
            },
        )
        self.instance.user.first_name = self.cleaned_data["first_name"]
        self.instance.user.last_name = self.cleaned_data["last_name"]
        self.instance.user.email = self.cleaned_data["email"]
        self.instance.is_admin = self.cleaned_data["role"]
        self.instance.user.save()

        OrganizationUser.objects.create(
            user=self.instance.user, organization=self.initial["organization"], is_admin=self.instance.is_admin
        )

        return super().save(*args, **kwargs)


class OrganizationUserEditForm(forms.ModelForm):
    """
    Form class for editing OrganizationUsers *and* the linked user model.
    """

    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control"}))
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    new_password1 = forms.CharField(
        label="New Password",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "id": "Password1"}),
    )
    new_password2 = forms.CharField(
        label="Confirm Password",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    document_permission = forms.ChoiceField(
        choices=DocumentPermission.choices,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    is_active = forms.CharField(label="Block User Sign-in:", widget=forms.RadioSelect(choices=ACTIVE_STATUS_CHOICES))

    class Meta:
        model = OrganizationUser
        exclude = ("organization", "user", "is_admin")

    def __init__(self, *args, **kwargs):
        super(OrganizationUserEditForm, self).__init__(*args, **kwargs)
        self.fields["first_name"].initial = self.instance.user.first_name
        self.fields["last_name"].initial = self.instance.user.last_name
        self.fields["email"].initial = self.instance.user.email
        self.fields["role"].initial = self.instance.is_admin
        self.fields["is_active"].initial = self.instance.user.is_active
        self.fields["document_permission"].initial = self.instance.user.document_permission

    def clean_new_password2(self):
        pass1 = self.cleaned_data.get("new_password1")
        pass2 = self.cleaned_data.get("new_password2")
        if (pass1 or pass2) and pass1 != pass2:
            raise ValidationError("Passwords do not match.", "password-mismatch")
        return pass2

    def save(self, *args, **kwargs):
        """
        Save changes to linked user model
        """
        self.instance.user.first_name = self.cleaned_data["first_name"]
        self.instance.user.last_name = self.cleaned_data["last_name"]
        self.instance.user.email = self.cleaned_data["email"]
        if self.cleaned_data["is_active"]:
            self.instance.user.is_active = self.cleaned_data["is_active"]
        if self.cleaned_data["document_permission"]:
            self.instance.user.document_permission = self.cleaned_data["document_permission"]
        if self.cleaned_data["new_password2"]:
            self.instance.user.set_password(self.cleaned_data["new_password2"])
        self.instance.user.save()
        self.instance.is_admin = self.cleaned_data["role"]
        return super(OrganizationUserEditForm, self).save(*args, **kwargs)
