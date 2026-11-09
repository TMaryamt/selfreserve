"""
test_flow.py
تست کامل: لغو رزرو چهارشنبه ناهار (جوجه کباب) و رزرو دوباره‌اش با کد.
نتیجه نهایی همان است که قبلاً بود و اعتبارت در آخر تغییری نمیکند.

اجرا: python reservations\\test_flow.py
(قبلش SELF_USER و SELF_PASS را set کن)
"""

import os

from self_client import SelfClient

# رزروی که میخواهیم تست کنیم
TARGET_DATE = "1405/08/20"
TARGET_MEAL_ID = 2     # 2 یعنی ناهار
FOOD_ID = 10           # چلو جوجه کباب
SELF_ID = 11           # مجتمع کوثر (15خرداد)

username = os.environ.get("SELF_USER")
password = os.environ.get("SELF_PASS")
if not username or not password:
    raise SystemExit("اول SELF_USER و SELF_PASS را تنظیم کن")

client = SelfClient()
client.login(username, password)
print("ورود موفق بود")

# ---------- مرحله 1: لغو ----------
reservations = [
    r for r in client.get_reservations()
    if r["date"] == TARGET_DATE and r["reserved"]["MealId"] == TARGET_MEAL_ID
]
if not reservations:
    raise SystemExit("رزرو چهارشنبه ناهار پیدا نشد")

target = reservations[0]
print("رزرو پیدا شد:", target["reserved"]["FoodName"], "- شماره:", target["reserved"]["ReserveNumber"])

input("برای لغو این رزرو Enter بزن (برای انصراف Ctrl+C): ")
result = client.cancel_reservation(target)
print("نتیجه لغو:", result["StateMessage"])

# ---------- مرحله 2: رزرو دوباره ----------
input("برای رزرو دوباره Enter بزن (برای انصراف Ctrl+C): ")

meal = next(
    m for m in client.get_open_meals()
    if m["date"] == TARGET_DATE and m["meal_id"] == TARGET_MEAL_ID
)
food = next(f for f in meal["foods"] if f["food_id"] == FOOD_ID)
self_item = next(s for s in food["selfs"] if s["self_id"] == SELF_ID)

result = client.reserve_food(meal, food, self_item)
print("نتیجه رزرو:", result["StateMessage"], "- شماره رزرو:", result["ReserveNumber"])