"""
test_reset_api.py
تست بازیابی رمز عبور.
قبلش سرور را در ترمینال دیگر اجرا کن (python manage.py runserver).
اجرا: python test_reset_api.py
"""

import random

import requests

BASE = "http://127.0.0.1:8000/api/auth"
n = random.randint(1000, 9999)

data = {
    "first_name": "Test", "last_name": "User",
    "username": "rsttest%d" % n, "email": "rsttest%d@example.com" % n,
    "phone_number": "0916000%d" % n,
    "password": "Old-strong-pass-111", "confirm_password": "Old-strong-pass-111",
}
r = requests.post(BASE + "/register/", json=data)
print("register:", r.status_code)
old_token = r.json()["token"]

# ایمیل ثبت‌نشده: باید همان جواب را بدهد
r = requests.post(BASE + "/forgot-password/", json={"email": "nobody@example.com"})
print("ایمیل ناشناس:", r.status_code, r.json())

# ایمیل واقعی
r = requests.post(BASE + "/forgot-password/", json={"email": data["email"]})
print("ایمیل ثبت‌شده:", r.status_code, r.json())

print()
print("به ترمینال سرور (runserver) نگاه کن. متن ایمیل با یک لینک چاپ شده است.")
print("آخرین بخش لینک (بعد از reset-password/) همان reset_id است.")
reset_id = input("reset_id را اینجا paste کن و Enter بزن: ").strip()

r = requests.post(BASE + "/reset-password/", json={"reset_id": reset_id, "password": "12345678", "confirm_password": "12345678"})
print("رمز ضعیف:", r.status_code, r.json())

r = requests.post(BASE + "/reset-password/", json={"reset_id": reset_id, "password": "New-strong-pass-222", "confirm_password": "other"})
print("رمزهای متفاوت:", r.status_code, r.json())

r = requests.post(BASE + "/reset-password/", json={"reset_id": reset_id, "password": "New-strong-pass-222", "confirm_password": "New-strong-pass-222"})
print("رمز جدید:", r.status_code, r.json())

r = requests.post(BASE + "/reset-password/", json={"reset_id": reset_id, "password": "New-strong-pass-333", "confirm_password": "New-strong-pass-333"})
print("استفاده دوباره از همان لینک:", r.status_code, r.json())

r = requests.get(BASE + "/me/", headers={"Authorization": "Token " + old_token})
print("توکن قبلی بعد از تغییر رمز:", r.status_code)

r = requests.post(BASE + "/login/", json={"username": data["username"], "password": "Old-strong-pass-111"})
print("ورود با رمز قدیمی:", r.status_code)

r = requests.post(BASE + "/login/", json={"username": data["username"], "password": "New-strong-pass-222"})
print("ورود با رمز جدید:", r.status_code)