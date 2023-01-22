from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import AbstractUser, PermissionsMixin
from django.db import models
import logging
import base64
import uuid
import secrets


class TimeStampMixin(models.Model):
    """
    abstract timestamp mixin base model for created_at, updated_at field
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """
    abstract soft delete mixin base model for is_deleted field
    """

    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True


class UserManager(BaseUserManager):
    """
    Custom account model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    use_in_migrations = True

    def create_user(
        self,
        email=None,
        password=None,
        **extra_fields,
    ):
        """
        Create and save a User with the given email and password.
        """
        extra_fields.setdefault("is_superuser", False)

        if not email:
            raise ValueError("Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)

        user.save(using=self._db)
        logging.info(f"User [{user.id}] 회원가입")
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_deleted", False)

        # TODO: more details on access key and secret key
        extra_fields.setdefault(
            "access_key",
            base64.urlsafe_b64encode(uuid.uuid4().bytes).decode("utf8").rstrip("=\n"),
        )
        extra_fields.setdefault("secret_key", secrets.token_hex(32))
        extra_fields.setdefault("service_name", "Chat Box")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email=email, password=password, **extra_fields)


class User(AbstractBaseUser, TimeStampMixin, SoftDeleteMixin, PermissionsMixin):
    id = models.BigAutoField(primary_key=True)
    email = models.EmailField(max_length=64, unique=True, null=False)
    access_key = models.CharField(max_length=22, null=False, blank=False)
    secret_key = models.CharField(max_length=64, null=False, blank=False)
    service_name = models.CharField(max_length=50, null=False, blank=False)
    service_domain = models.CharField(max_length=200, null=True, blank=False)
    service_expl = models.CharField(max_length=200, null=False, blank=False)
    profile_name = models.CharField(max_length=50, null=False, blank=True, default="")
    description = models.CharField(max_length=200, null=False, blank=True, default="")
    profile_image = models.ImageField(
        blank=False, null=True, upload_to="user_profiles/"
    )

    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can log into this admin site.",
    )

    objects = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["profile_name", "service_name", "service_expl"]

    class Meta:
        db_table = "user"
        unique_together = ["email"]

    def __str__(self):
        return f"[{self.id}] {self.get_username()}"

    def __repr__(self):
        return f"User({self.id}, {self.get_username()})"
