"""
self_client.py
کلاینت ورود به سامانه سلف (IdentityServer با response_mode=form_post)

ورود: requests + bs4
دریافت منو: درخواست JSON به API خود سایت (با کوکی‌های ورود)
جاهای TODO را با اطلاعات واقعی از F12 > Network پر کن.
"""

import html
import json
import os
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ------------------------------------------------------------
# تنظیمات سایت
# ------------------------------------------------------------
BASE_URL = "https://self.pgu.ac.ir"

# آدرسی که در مرورگر باز میکنی. وقتی وارد نشده باشی، سایت خودش به صفحه ورود
# (و آدرس authorize با state و nonce تازه) هدایت میکند.
START_URL = BASE_URL + "/"

USERNAME_FIELD = "username"
PASSWORD_FIELD = "password"

MENU_PATH = "/api/v0/Reservation"    # API برنامه غذایی (از F12 پیدا شد)
RESERVE_PATH = "/api/v0/Reservation" # رزرو و لغو، هر دو با POST به همین آدرس (از F12 پیدا شد)

# درخواست‌های API در مرورگر هدر Authorization نداشتند، پس فعلاً فقط با کوکی کار میکنیم.
# اگر API خطای 401 داد، این را True کن.
USE_BEARER = False

TIMEOUT = 15  # ثانیه


class SelfError(Exception):
    """خطای مخصوص خودمان برای مشکلات سامانه سلف."""


class SelfClient:
    def __init__(self):
        # Session کوکی‌ها را بین درخواست‌ها نگه میدارد
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        })
        self.token = None  # access_token بعد از ورود (اگر سایت بدهد)

    # --------------------------------------------------------
    # ابزارهای کمکی برای خواندن صفحه‌ها
    # --------------------------------------------------------
    @staticmethod
    def _read_model(page_text):
        # اطلاعات صفحه ورود داخل <script id="modelJson"> است، به شکل JSON
        # که علامت‌هایش با کد HTML نوشته شده (مثل &quot;)؛ پس اول باید باز شود
        soup = BeautifulSoup(page_text, "html.parser")
        script = soup.find("script", {"id": "modelJson"})
        if script is None:
            return None
        return json.loads(html.unescape(script.get_text()))

    @staticmethod
    def _find_auto_form(response):
        # بعد از ورود موفق، سایت یک صفحه با فرم مخفی میدهد
        # که شامل id_token و access_token است (response_mode=form_post)
        soup = BeautifulSoup(response.text, "html.parser")
        form = soup.find("form")
        if form is None or not form.get("action"):
            return None

        fields = {
            field["name"]: field.get("value", "")
            for field in form.find_all("input")
            if field.get("name")
        }
        if "id_token" not in fields and "access_token" not in fields:
            return None

        return urljoin(response.url, form["action"]), fields

    # --------------------------------------------------------
    # 1) ورود
    # --------------------------------------------------------
    def login(self, username, password):
        # مرحله 1: سایت را باز میکنیم؛ به صفحه ورود هدایت میشویم
        page = self.session.get(START_URL, timeout=TIMEOUT)
        page.raise_for_status()

        model = self._read_model(page.text)
        if model is None:
            raise SelfError(
                "صفحه ورود پیدا نشد (آدرس نهایی: %s). START_URL را چک کن." % page.url
            )

        # مرحله 2: آدرس ورود (با signin) و توکن امنیتی را از modelJson برمیداریم
        login_url = urljoin(page.url, model["loginUrl"])
        xsrf = model["antiForgery"]

        data = {
            xsrf["name"]: xsrf["value"],
            USERNAME_FIELD: username,
            PASSWORD_FIELD: password,
        }

        # مرحله 3: ارسال فرم ورود (هدایت‌ها خودکار دنبال میشوند)
        response = self.session.post(login_url, data=data, timeout=TIMEOUT)
        response.raise_for_status()

        # مرحله 4: اگر ورود موفق بود، یک فرم خودکار با توکن‌ها آمده است
        result = self._find_auto_form(response)
        if result is None:
            error = None
            failed_model = self._read_model(response.text)
            if failed_model:
                error = failed_model.get("errorMessage")
            raise SelfError("ورود ناموفق بود: %s" % (error or "پیام خطایی نیامد"))

        action, fields = result
        self.token = fields.get("access_token")

        # مرحله 5: همان کاری که مرورگر میکند؛ فرم را به سایت اصلی میفرستیم
        # تا سایت ما را وارد کند (کوکی ورود در Session ذخیره میشود)
        callback = self.session.post(action, data=fields, timeout=TIMEOUT)
        callback.raise_for_status()

    # --------------------------------------------------------
    # ابزار کمکی برای صدا زدن API سایت
    # --------------------------------------------------------
    def _headers(self):
        # این دو هدر را مرورگر هم برای درخواست‌های API میفرستد
        headers = {
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
        }
        if USE_BEARER and self.token:
            headers["Authorization"] = "Bearer " + self.token
        return headers

    def api_get(self, path, params=None):
        response = self.session.get(
            BASE_URL + path, params=params, headers=self._headers(), timeout=TIMEOUT
        )
        response.raise_for_status()
        return response.json()

    def api_post(self, path, payload):
        response = self.session.post(
            BASE_URL + path, json=payload, headers=self._headers(), timeout=TIMEOUT
        )
        response.raise_for_status()
        return response.json()

    # --------------------------------------------------------
    # 2) برنامه غذایی
    # --------------------------------------------------------
    def get_menu(self):
        # navigation=0 یعنی هفته جاری؛ lastdate خالی است (مثل مرورگر)
        return self.api_get(MENU_PATH, params={"lastdate": "", "navigation": 0})

    def get_open_meals(self, menu=None):
        """
        از جواب کامل سایت فقط وعده‌هایی را برمیگرداند که الان قابل رزرو هستند
        (MealState برابر 0 یعنی «فعال») و غذا و سلف‌هایشان را ساده میکند.
        اگر menu داده نشود، خودش منو را از سایت میگیرد.
        """
        if menu is None:
            menu = self.get_menu()

        result = []
        for day in menu:
            for meal_index, meal in enumerate(day.get("Meals", [])):
                if meal.get("MealState") != 0:
                    continue

                # نام نوع غذاها (مثل «غذا») در FoodTypeMenu است
                type_names = {t["ID"]: t["Name"] for t in meal.get("FoodTypeMenu", [])}

                foods = []
                for food in meal.get("FoodMenu", []):
                    foods.append({
                        "food_id": food["FoodId"],
                        "food_name": " ".join(food["FoodName"].split()),
                        "food_type": food["FoodType"],
                        "food_type_name": type_names.get(food["FoodType"], ""),
                        "selfs": [
                            {
                                "self_id": s["SelfId"],
                                "self_name": s["SelfName"],
                                "price": s["Price"],      # قیمت کامل غذا
                                "yarane": s["Yarane"],    # سهم یارانه
                            }
                            for s in food.get("SelfMenu", [])
                        ],
                    })

                result.append({
                    "date": day["DayDate"],
                    "day_title": day["DayTitle"],
                    "day_index": day["DayId"],
                    "meal_row_id": meal["Id"],        # شناسه این وعده در این روز
                    "meal_id": meal["MealId"],        # 1 صبحانه، 2 ناهار، 3 شام
                    "meal_index": meal_index,         # جایگاه وعده در لیست روز
                    "meal_name": meal["MealName"],
                    "foods": foods,
                })
        return result

    def get_reserved_raw(self):
        """
        رزروهای ثبت‌شده را همان‌طور که سایت در فیلد LastReserved میدهد برمیگرداند.
        (برای دیدن ساختارش در تست؛ بعداً مرتبش میکنیم)
        """
        found = []
        for day in self.get_menu():
            for meal in day.get("Meals", []):
                if meal.get("LastReserved"):
                    found.append({
                        "date": day["DayDate"],
                        "meal_name": meal["MealName"],
                        "last_reserved": meal["LastReserved"],
                    })
        return found

    # --------------------------------------------------------
    # 3) رزرو
    # --------------------------------------------------------
    def reserve_food(self, meal, food, self_item):
        """
        meal، food و self_item همان دیکشنری‌هایی هستند که get_open_meals میدهد.
        درخواستی را میفرستد که مرورگر هم هنگام رزرو میفرستد.
        """
        # مبلغی که دانشجو میپردازد = قیمت کامل - یارانه (در رزرو واقعی همین دیده شد)
        student_pays = self_item["price"] - self_item["yarane"]

        item = {
            "Row": 1,
            "Id": meal["meal_row_id"],
            "Date": meal["date"],
            "MealId": meal["meal_id"],
            "FoodId": food["food_id"],
            "FoodName": food["food_name"],
            "SelfId": self_item["self_id"],
            "LastCounts": 0,
            "Counts": 1,
            "Price": student_pays,
            "SobsidPrice": self_item["yarane"],
            "PriceType": 2,
            "State": 0,
            "Type": 1,
            "OP": 1,
            "OpCategory": 1,
            "Provider": 1,
            "Saved": 0,
            "MealName": meal["meal_name"],
            "DayName": meal["day_title"],
            "SelfName": self_item["self_name"],
            "DayIndex": meal["day_index"],
            "MealIndex": meal["meal_index"],
        }

        # سایت لیست میگیرد و لیست هم برمیگرداند
        result = self.api_post(RESERVE_PATH, [item])
        first = result[0]

        # StateCode برابر 0 یعنی «با موفقیت ثبت شد»
        if first.get("StateCode") != 0:
            raise SelfError("رزرو انجام نشد: %s" % first.get("StateMessage"))
        return first


    # --------------------------------------------------------
    # 4) رزروهای ثبت‌شده و لغو
    # --------------------------------------------------------
    def get_reservations(self):
        """
        فهرست مرتب رزروهای ثبت‌شده. هر مورد علاوه بر خود رزرو (reserved)،
        اطلاعات روز و وعده را هم دارد، چون برای لغو لازم است.
        """
        found = []
        for day in self.get_menu():
            for meal_index, meal in enumerate(day.get("Meals", [])):
                for reserved in meal.get("LastReserved", []):
                    found.append({
                        "date": day["DayDate"],
                        "day_title": day["DayTitle"],
                        "day_index": day["DayId"],
                        "meal_index": meal_index,
                        "meal_name": meal["MealName"],
                        "reserved": reserved,
                    })
        return found

    def cancel_reservation(self, info):
        """
        info یکی از موردهای get_reservations است.
        درخواستی را میفرستد که مرورگر هنگام حذف رزرو میفرستد
        (Counts برابر 0 و LastCounts برابر تعداد قبلی).
        """
        r = info["reserved"]

        item = {
            "Row": 1,
            "Id": r["Id"],
            "Date": info["date"],
            "MealId": r["MealId"],
            "FoodId": r["FoodId"],
            "FoodName": r["FoodName"],
            "SelfId": r["SelfId"],
            "SelfName": r["SelfName"],
            "Counts": 0,
            "LastCounts": r["Count"],
            "Price": r["Price"],
            "PriceType": r["PriceType"],
            "State": r["ReserveState"],
            "Type": r["FoodType"],
            "TypeTitle": r["FoodTypeTitle"],
            "OP": r["Op"],
            "OPTitle": r["OpTitle"],
            "ReserveNumber": r["ReserveNumber"],
            "ReserveId": r["ReserveId"],
            "Provider": 1,
            "Saved": 0,
            "MealName": info["meal_name"],
            "DayName": info["day_title"],
            "DayIndex": info["day_index"],
            "MealIndex": info["meal_index"],
        }

        result = self.api_post(RESERVE_PATH, [item])
        first = result[0]

        # StateCode برابر 4 یعنی «با موفقیت حذف شد»
        if first.get("StateCode") != 4:
            raise SelfError("لغو انجام نشد: %s" % first.get("StateMessage"))
        return first


# ------------------------------------------------------------
# تست دستی: python reservations\self_client.py
# ------------------------------------------------------------
if __name__ == "__main__":
    username = os.environ.get("SELF_USER")
    password = os.environ.get("SELF_PASS")

    if not username or not password:
        raise SystemExit("اول SELF_USER و SELF_PASS را تنظیم کن")

    client = SelfClient()
    client.login(username, password)
    print("ورود موفق بود")

    meals = client.get_open_meals()
    print("تعداد وعده‌های قابل رزرو:", len(meals))
    for meal in meals:
        print(meal["date"], meal["day_title"], meal["meal_name"], "- تعداد غذا:", len(meal["foods"]))

    print()
    print("رزروهای ثبت‌شده (خام):")
    print(json.dumps(client.get_reserved_raw(), ensure_ascii=False, indent=2))