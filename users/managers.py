from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    def create_user(self, email, password, **extraFields):
        if not email:
            raise ValueError(_("The email must be set"))
        user = self.model(email=email, **extraFields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extraFields):
        extraFields.setdefault("is_staff", True)
        extraFields.setdefault("is_superuser", True)

        if extraFields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extraFields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extraFields)
