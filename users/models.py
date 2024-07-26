from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from users.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("email address"), blank=True, unique=True)
    username = models.CharField(_("Username"), max_length=50, blank=True, unique=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = [
        "username",
    ]

    objects = UserManager()

    def __str__(self):
        return str(self.email)

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        return super(User, self).save(*args, **kwargs)
