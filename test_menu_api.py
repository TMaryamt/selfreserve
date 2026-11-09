"""
test_menu_api.py
تست API منو و رزروها.
قبلش سرور را در ترمینال دیگر اجرا کن و در همین ترمینال SELF_USER و SELF_PASS را set کن.
اجرا: python test_menu_api.py
"""

import os
import random

import requests

BASE = "http://127.0.0.1:8000/api"
n = random.randint(1000, 9999)

data = {
    "first_name": "Test", "last_name": "User",
    "username": "menutest%d" % n, "email": "menutest%d@example.com" % n,
    "phone_number": "0914000%d" % n,
    "password": "Strong-pass-98765", "confirm_password": "Strong-pass-98765",
}
r = requests.post(BASE + "/auth/register/", json=data)
print("register:", r.status_code)
headers = {"Authorization": "Token " + r.json()["token"]}

# قبل از ثبت اطلاعات سلف
r = requests.get(BASE + "/self/menu/", headers=headers)
print("منو بدون اتصال به سلف:", r.status_code, r.json())

r = requests.post(BASE + "/self/profile/", headers=headers,
                  json={"self_username": os.environ["SELF_USER"], "self_password": os.environ["SELF_PASS"]})
print("اتصال به سلف:", r.status_code)

# منو
r = requests.get(BASE + "/self/menu/", headers=headers)
print("منو:", r.status_code, "- تعداد وعده:", len(r.json()))
first = r.json()[0]
print("اولین وعده:", first["date"], first["meal_name"], "- تعداد غذا:", len(first["foods"]))

# رزروها
r = requests.get(BASE + "/self/reservations/", headers=headers)
print("رزروها:", r.status_code)
for item in r.json():
    print(" -", item["date"], item["meal_name"], item["food_name"])

# پاکسازی
print("حذف اتصال:", requests.delete(BASE + "/self/profile/", headers=headers).status_code)