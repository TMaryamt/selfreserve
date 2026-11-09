"""
test_preferences_api.py
تست API فهرست غذاها و ترجیحات.
قبلش سرور را در ترمینال دیگر اجرا کن و در همین ترمینال SELF_USER و SELF_PASS را set کن.
اجرا: python test_preferences_api.py
"""

import os
import random

import requests

BASE = "http://127.0.0.1:8000/api"
n = random.randint(1000, 9999)

data = {
    "first_name": "Test", "last_name": "User",
    "username": "preftest%d" % n, "email": "preftest%d@example.com" % n,
    "phone_number": "0917000%d" % n,
    "password": "Strong-pass-98765", "confirm_password": "Strong-pass-98765",
}
r = requests.post(BASE + "/auth/register/", json=data)
headers = {"Authorization": "Token " + r.json()["token"]}

r = requests.post(BASE + "/self/profile/", headers=headers,
                  json={"self_username": os.environ["SELF_USER"], "self_password": os.environ["SELF_PASS"]})
print("اتصال به سلف:", r.status_code)

print("تعداد غذاها قبل از گرفتن منو:", len(requests.get(BASE + "/self/foods/", headers=headers).json()))

r = requests.get(BASE + "/self/menu/", headers=headers)
print("منو:", r.status_code)
first_food = r.json()[0]["foods"][0]
print("نمونه غذا در منو:", first_food["food_name"], "- نوع:", first_food["food_type_name"])

foods = requests.get(BASE + "/self/foods/", headers=headers).json()
print("تعداد غذاها بعد از گرفتن منو:", len(foods))
ids = [f["food_id"] for f in foods]

# ذخیره ترجیحات
body = {
    "priorities": ids[:3],
    "disliked": ids[3:4],
    "fallback": "skip_and_notify",
    "slots": [
        {"day_of_week": 1, "meal_id": 2, "self_id": None, "self_name": ""},
        {"day_of_week": 2, "meal_id": 3, "self_id": None, "self_name": ""},
    ],
}
r = requests.put(BASE + "/self/preferences/", headers=headers, json=body)
print("ذخیره:", r.status_code)
d = r.json()
print(" اولویت‌ها:", [p["name"] for p in d["priorities"]])
print(" نمیخورم:", [p["name"] for p in d["disliked"]])
print(" گزینه آخر:", d["fallback"], "| تعداد وعده‌های برنامه:", len(d["slots"]))

# حذف اولویت اول (بقیه یکی بالا میآیند)
r = requests.put(BASE + "/self/preferences/", headers=headers, json={"priorities": ids[1:3]})
print("بعد از حذف اولویت اول:", [p["name"] for p in r.json()["priorities"]])
print("نمیخورم دست نخورده:", len(r.json()["disliked"]))

# خطاها
r = requests.put(BASE + "/self/preferences/", headers=headers, json={"priorities": [ids[3]]})
print("غذای نمیخورم در اولویت:", r.status_code)
r = requests.put(BASE + "/self/preferences/", headers=headers, json={"priorities": [999999]})
print("غذای ناشناس:", r.status_code, r.json())

# پاکسازی
print("حذف اتصال:", requests.delete(BASE + "/self/profile/", headers=headers).status_code)