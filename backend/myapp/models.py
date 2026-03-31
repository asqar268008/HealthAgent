from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.validators import MinLengthValidator, EmailValidator
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):

        if not email:
            raise ValueError("Users must have an email address")

        email = self.normalize_email(email)

        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", False)

        user = self.model(email=email, **extra_fields)

        user.set_password(password)
        user.save(using=self._db)

        return user


    def create_superuser(self, email, password=None, **extra_fields):

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):

    email = models.EmailField(
        unique=True,
        db_index=True,
        validators=[EmailValidator()]
    )

    name = models.CharField(
        max_length=255,
        validators=[MinLengthValidator(2)]
    )

    dob = models.DateField(null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)

    gender = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=[
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
            ("prefer_not_to_say", "Prefer not to say"),
        ]
    )

    date_joined = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.email

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name.split()[0] if self.name else self.email

    def clean(self):
        if self.age and (self.age < 0 or self.age > 150):
            raise ValueError("Age must be between 0 and 150")


# =========================
# HEALTH PROFILE
# =========================

class HealthProfile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="health_profile"
    )

    height_cm = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    sleep_hours = models.FloatField(null=True, blank=True)
    resting_heart_rate = models.PositiveIntegerField(null=True, blank=True)
    systolic_bp = models.PositiveIntegerField(null=True, blank=True)
    diastolic_bp = models.PositiveIntegerField(null=True, blank=True)
    fasting_blood_sugar = models.FloatField(null=True, blank=True)
    total_cholesterol = models.FloatField(null=True, blank=True)
    vitamin_deficiency = models.JSONField(default=list, blank=True)

    SMOKING_CHOICES = [
        ("no", "No"),
        ("yes", "Yes"),
        ("former", "Former"),
    ]

    smoking_status = models.CharField(
        max_length=10,
        choices=SMOKING_CHOICES,
        null=True,
        blank=True
    )

    ALCOHOL_CHOICES = [
        ("none", "None"),
        ("moderate", "Moderate"),
        ("high", "High"),
    ]

    alcohol_consumption = models.CharField(
        max_length=20,
        choices=ALCOHOL_CHOICES,
        null=True,
        blank=True
    )

    EXERCISE_CHOICES = [
        ("none", "None"),
        ("low", "Low"),
        ("moderate", "Moderate"),
        ("high", "High"),
    ]

    exercise_frequency = models.CharField(
        max_length=20,
        choices=EXERCISE_CHOICES,
        null=True,
        blank=True
    )

    DIET_CHOICES = [
        ("vegetarian", "Vegetarian"),
        ("non_vegetarian", "Non Vegetarian"),
        ("vegan", "Vegan"),
        ("other", "Other"),
    ]

    diet_type = models.CharField(
        max_length=50,
        choices=DIET_CHOICES,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def bmi(self):
        if self.height_cm and self.weight_kg:
            height_m = self.height_cm / 100
            return round(self.weight_kg / (height_m ** 2), 2)
        return None

    def __str__(self):
        return f"{self.user.email} - Health Profile"

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_health_profile(sender, instance, created, **kwargs):

    if created:
        HealthProfile.objects.get_or_create(user=instance)