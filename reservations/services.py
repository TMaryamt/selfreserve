"""
services.py
منطق اصلی اپ reservations، جدا از صفحه‌ها و API.
هر جای دیگر (API، زمان‌بند و ...) فقط همین توابع را صدا میزند.
"""

import requests

from .models import Food, SelfProfile
from .self_client import SelfClient, SelfError


def _login_or_raise(username, password):
    """وارد سلف میشود و کلاینت واردشده را برمیگرداند. هر مشکلی را به SelfError تبدیل میکند."""
    client = SelfClient()
    try:
        client.login(username, password)
    except requests.RequestException:
        # مشکل شبکه، تایم‌اوت یا خطای سرور سلف
        raise SelfError("ارتباط با سامانه سلف برقرار نشد، کمی بعد دوباره تلاش کن")
    return client


def save_self_credentials(user, self_username, self_password):
    """
    اول با همین اطلاعات وارد سلف میشود. فقط اگر ورود موفق بود،
    اطلاعات را (با رمز رمزنگاری‌شده) ذخیره میکند.
    اگر ورود ناموفق باشد SelfError میدهد و چیزی ذخیره نمیشود.
    """
    _login_or_raise(self_username, self_password)

    profile, _ = SelfProfile.objects.get_or_create(
        user=user,
        defaults={"self_username": self_username},
    )
    profile.self_username = self_username
    profile.set_self_password(self_password)
    profile.save()
    return profile


def get_logged_in_client(user):
    """
    برای این کاربر وارد سلف میشود و کلاینت آماده (واردشده) را برمیگرداند.
    اگر کاربر هنوز اطلاعات سلف ثبت نکرده باشد SelfError میدهد.
    """
    try:
        profile = SelfProfile.objects.get(user=user)
    except SelfProfile.DoesNotExist:
        raise SelfError("این کاربر هنوز اطلاعات سلف را ثبت نکرده است")

    return _login_or_raise(profile.self_username, profile.get_self_password())


def update_food_catalog(menu):
    """
    همه غذاهای این منو (حتی وعده‌های غیرفعال) را به فهرست غذاهای ما اضافه میکند.
    menu همان جواب خام سلف است (client.get_menu()).
    """
    for day in menu:
        for meal in day.get("Meals", []):
            type_names = {t["ID"]: t["Name"] for t in meal.get("FoodTypeMenu", [])}
            for food in meal.get("FoodMenu", []):
                Food.objects.update_or_create(
                    food_id=food["FoodId"],
                    defaults={
                        "name": " ".join(food["FoodName"].split()),
                        "food_type": food["FoodType"],
                        "food_type_name": type_names.get(food["FoodType"], ""),
                    },
                )