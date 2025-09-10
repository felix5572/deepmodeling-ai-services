from django.db import models
from django.utils import timezone
# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):
    user_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        unique=True,
        help_text="Unique identifier for the user user__workos__a1b2c345-1789-xxx or user__django__a31v41d5v0"
    )

    auth_provider = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        default="django",
        help_text="Authentication provider django, workos, bohrium, etc."
    )

    external_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="External system user identifier"
    )

    organization = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="User organization/tenant"
    )

    
    # supabase__a1b2c345-1789-xxx or django__1234567890

    