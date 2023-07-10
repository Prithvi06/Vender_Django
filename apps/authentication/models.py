from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from organizations.models import Organization


# Create your models here.
class UserManger(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users require an email field")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class DocumentPermission(models.IntegerChoices):
    VIEW_NONE = 0
    VIEW_OWNED = 1
    VIEW_ALL = 2
    EDIT_OWNED = 3
    EDIT_ALL = 4


class User(AbstractUser):
    username = None
    email = models.EmailField(_("Email Address"), unique=True)
    last_visit = models.DateTimeField(null=True, blank=True)
    document_permission = models.PositiveIntegerField(null=True, blank=True, choices=DocumentPermission.choices)
    feature_permission = models.BooleanField(default=True, null=True, blank=True)
    is_invited = models.BooleanField(default=False)

    objects = UserManger()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []


class CreateInvite(models.Model):
    org = models.ForeignKey(Organization, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField()
    is_admin = models.BooleanField(default=False)

    class Meta:
        managed = False

    def save(self, *args, **kwargs):
        return
