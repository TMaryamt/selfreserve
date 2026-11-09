"""
test_reserve_api.py
تست API رزرو و لغو: یک غذای ارزان رزرو میشود و بلافاصله لغو میشود.
قبلش سرور را در ترمینال دیگر اجرا کن و در همین ترمینال SELF_USER و SELF_PASS را set کن.
اجرا: python test_reserve_api.py
"""

import os
import random

import requests

BASE = "http://127.0.0.1:8000/api"
n = random.randint(1000, 9999)

data = {
    "first_name": "Test", "last_name": "User",
    "username": "rsvtest%d" % n, "email": "rsvtest%d@example.com" % n,
    "phone_number": "0915000%d" % n,
    "password": "Strong-pass-98765", "confirm_password": "Strong-pass-98765",
}
r = requests.post(BASE + "/auth/register/", json=data)
headers = {"Authorization": "Token " + r.json()["token"]}

r = requests.post(BASE + "/self/profile/", headers=headers,
                  json={"self_username": os.environ["SELF_USER"], "self_password": os.environ["SELF_PASS"]})
print("اتصال به سلف:", r.status_code)

menu = requests.get(BASE + "/self/menu/", headers=headers).json()
reserved = requests.get(BASE + "/self/reservations/", headers=headers).json()
reserved_keys = {(x["date"], x["meal_id"]) for x in reserved}

# اولین وعده‌ای که رزرو ندارد و ارزان‌ترین غذایش
target = None
for meal in menu:
    if (meal["date"], meal["meal_id"]) in reserved_keys:
        continue
    best = None
    for food in meal["foods"]:
        for s in food["selfs"]:
            pay = s["price"] - s["yarane"]
            if best is None or pay < best[0]:
                best = (pay, food, s)
    if best:
        target = (meal, best)
        break

if target is None:
    raise SystemExit("وعده بدون رزرو پیدا نشد")

meal, (pay, food, s) = target
print("انتخاب شد:", meal["date"], meal["meal_name"], "-", food["food_name"], "- مبلغ:", pay)
input("برای رزرو Enter بزن (انصراف: Ctrl+C): ")

body = {"date": meal["date"], "meal_id": meal["meal_id"], "food_id": food["food_id"], "self_id": s["self_id"]}

# تست خطا: غذایی که وجود ندارد
r = requests.post(BASE + "/self/reserve/", headers=headers, json={**body, "food_id": 999999})
print("رزرو غذای نامعتبر:", r.status_code, r.json())

r = requests.post(BASE + "/self/reserve/", headers=headers, json=body)
print("رزرو:", r.status_code, r.json())
reserve_id = r.json()["reserve_id"]

reserved = requests.get(BASE + "/self/reservations/", headers=headers).json()
print("تعداد رزروها بعد از رزرو:", len(reserved))

r = requests.post(BASE + "/self/cancel/", headers=headers, json={"reserve_id": reserve_id})
print("لغو:", r.status_code, r.json())

reserved = requests.get(BASE + "/self/reservations/", headers=headers).json()
print("تعداد رزروها بعد از لغو:", len(reserved))

print("حذف اتصال:", requests.delete(BASE + "/self/profile/", headers=headers).status_code)