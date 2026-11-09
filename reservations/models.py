from django.conf import settings
from django.db import models

from .crypto import decrypt_text, encrypt_text


class SelfProfile(models.Model):
    """اطلاعات ورود کاربر به سامانه سلف (جدا از حساب خود اپ)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    self_username = models.CharField(max_length=100)
    encrypted_password = models.TextField()  # رمز سلف، فقط به شکل رمزنگاری‌شده
    updated_at = models.DateTimeField(auto_now=True)

    def set_self_password(self, raw_password):
        self.encrypted_password = encrypt_text(raw_password)

    def get_self_password(self):
        return decrypt_text(self.encrypted_password)

    def __str__(self):
        return "SelfProfile of %s" % self.user.username


class Food(models.Model):
    """
    فهرست غذاهایی که تا الان در منوهای سلف دیده‌ایم.
    هر بار منو خوانده شود، غذاهای تازه به این جدول اضافه میشوند.
    """

    food_id = models.IntegerField(unique=True)  # همان FoodId سلف (ثابت است)
    name = models.CharField(max_length=300)
    food_type = models.IntegerField(default=1)
    food_type_name = models.CharField(max_length=100, blank=True)
    first_seen = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class FoodPreference(models.Model):
    """تنظیم کلی ترجیحات هر کاربر (برای وقتی هیچ‌کدام از غذاهای اولویت‌ها در منو نیست)."""

    ANY_AVAILABLE = "any_available"    # هر غذای موجود (بجز لیست سیاه)
    SKIP_AND_NOTIFY = "skip_and_notify"  # رزرو نشود و اعلان بده

    FALLBACK_CHOICES = [
        (ANY_AVAILABLE, "هر غذای موجود (بجز لیست سیاه)"),
        (SKIP_AND_NOTIFY, "رزرو نشود و اعلان بده"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    fallback = models.CharField(max_length=20, choices=FALLBACK_CHOICES, default=ANY_AVAILABLE)


class FoodPriority(models.Model):
    """لیست اولویت غذاهای هر کاربر. position برابر 1 یعنی اولویت اول."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ["position"]
        unique_together = [("user", "position"), ("user", "food")]


class DislikedFood(models.Model):
    """غذاهایی که کاربر نمیخورد (هرگز رزرو نمیشوند)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    food = models.ForeignKey(Food, on_delete=models.CASCADE)

    class Meta:
        unique_together = [("user", "food")]


class MealSlot(models.Model):
    """
    برنامه دلخواه: کاربر کدام روز هفته و کدام وعده را میخواهد و از کدام سلف.
    day_of_week: 0 شنبه ... 6 جمعه (مثل DayId سلف)
    meal_id: 1 صبحانه، 2 ناهار، 3 شام
    self_id خالی یعنی «هر سلفی».
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    day_of_week = models.PositiveSmallIntegerField()
    meal_id = models.PositiveSmallIntegerField()
    self_id = models.IntegerField(null=True, blank=True)
    self_name = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["day_of_week", "meal_id"]
        unique_together = [("user", "day_of_week", "meal_id")]