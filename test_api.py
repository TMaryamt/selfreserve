"""
test_api.py
تست API ثبت‌نام و ورود. اول سرور را در یک ترمینال دیگر اجرا کن:
    python manage.py runserver
بعد در این ترمینال:
    python test_api.py
"""

import random

import requests

BASE = "http://127.0.0.1:8000/api/auth"
n = random.randint(1000, 9999)

data = {
    "first_name": "Test",
    "last_name": "User",
    "username": "apitest%d" % n,
    "email": "apitest%d@example.com" % n,
    "phone_number": "0912000%d" % n,
    "password": "Strong-pass-98765",
    "confirm_password": "Strong-pass-98765",
}

r = requests.post(BASE + "/register/", json=data)
print("register:", r.status_code, r.json().get("user"))
headers = {"Authorization": "Token " + r.json()["token"]}

r = requests.get(BASE + "/me/", headers=headers)
print("me:", r.status_code)

r = requests.post(BASE + "/login/", json={"username": data["username"], "password": data["password"]})
print("login ok:", r.status_code)

r = requests.post(BASE + "/login/", json={"username": data["username"], "password": "wrong"})
print("login bad:", r.status_code, r.json())

r = requests.post(BASE + "/register/", json={**data, "confirm_password": "other"})
print("register bad:", r.status_code, r.json())

r = requests.post(BASE + "/logout/", headers=headers)
print("logout:", r.status_code)

r = requests.get(BASE + "/me/", headers=headers)
print("me after logout:", r.status_code)