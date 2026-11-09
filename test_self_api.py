"""
test_self_api.py
تست API ذخیره اطلاعات سلف.
قبلش سرور را در ترمینال دیگر اجرا کن (python manage.py runserver)
و در همین ترمینال SELF_USER و SELF_PASS را set کن.
اجرا: python test_self_api.py
"""

import os
import random

import requests

BASE = "http://127.0.0.1:8000/api"
n = random.randint(1000, 9999)

# یک کاربر آزمایشی میسازیم
data = {
    "first_name": "Test", "last_name": "User",
    "username": "selftest%d" % n, "email": "selftest%d@example.com" % n,
    "phone_number": "0913000%d" % n,
    "password": "Strong-pass-98765", "confirm_password": "Strong-pass-98765",
}
r = requests.post(BASE + "/auth/register/", json=data)
print("register:", r.status_code)
headers = {"Authorization": "Token " + r.json()["token"]}

print("وضعیت اول:", requests.get(BASE + "/self/profile/", headers=headers).json())

r = requests.post(BASE + "/self/profile/", headers=headers,
                  json={"self_username": os.environ["SELF_USER"], "self_password": "wrong-password"})
print("رمز اشتباه:", r.status_code, r.json())

r = requests.post(BASE + "/self/profile/", headers=headers,
                  json={"self_username": os.environ["SELF_USER"], "self_password": os.environ["SELF_PASS"]})
print("رمز درست:", r.status_code, r.json())

print("وضعیت بعد از ذخیره:", requests.get(BASE + "/self/profile/", headers=headers).json())
print("me:", requests.get(BASE + "/auth/me/", headers=headers).json().get("has_self_profile"))

r = requests.delete(BASE + "/self/profile/", headers=headers)
print("حذف:", r.status_code)
print("وضعیت بعد از حذف:", requests.get(BASE + "/self/profile/", headers=headers).json())