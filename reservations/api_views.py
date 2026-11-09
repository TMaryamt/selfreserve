"""
reservations/api_views.py
API اتصال به سلف، دیدن منو و دیدن رزروها برای React.
رمز سلف هیچ‌وقت در جواب برگردانده نمیشود.
"""

import requests
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SelfProfile
from .self_client import SelfError
from .services import get_logged_in_client, save_self_credentials


# ------------------------------------------------------------
# ابزارهای کمکی
# ------------------------------------------------------------
def run_with_client(user, action):
    """
    برای این کاربر وارد سلف میشود، تابع action را با کلاینت اجرا میکند
    و نتیجه را به شکل Response برمیگرداند. مشکل‌های سلف را به پیام مناسب تبدیل میکند.
    """
    try:
        client = get_logged_in_client(user)
        return Response(action(client))
    except SelfError as error:
        return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    except (requests.RequestException, ValueError):
        # ValueError یعنی سلف جوابی داده که JSON نبوده
        return Response(
            {"detail": "ارتباط با سامانه سلف برقرار نشد یا جواب نامعتبر بود"},
            status=status.HTTP_502_BAD_GATEWAY,
        )


def profile_status(user):
    profile = SelfProfile.objects.filter(user=user).first()
    if profile is None:
        return {"connected": False, "self_username": None}
    return {"connected": True, "self_username": profile.self_username}


class SelfCredentialsSerializer(serializers.Serializer):
    self_username = serializers.CharField(max_length=100)
    self_password = serializers.CharField(write_only=True)  # فقط ورودی؛ هرگز در خروجی نمیآید


# ------------------------------------------------------------
# اتصال به سلف
# ------------------------------------------------------------
class SelfProfileView(APIView):
    # permission پیش‌فرض (IsAuthenticated) اعمال میشود: فقط کاربر واردشده

    def get(self, request):
        """آیا کاربر اطلاعات سلفش را ثبت کرده؟"""
        return Response(profile_status(request.user))

    def post(self, request):
        """اطلاعات سلف را تست و ذخیره میکند (اگر قبلاً بود، عوض میشود)."""
        serializer = SelfCredentialsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            save_self_credentials(
                request.user,
                serializer.validated_data["self_username"].strip(),
                serializer.validated_data["self_password"],
            )
        except SelfError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(profile_status(request.user))

    def delete(self, request):
        """اتصال به سلف را قطع میکند و اطلاعات ذخیره‌شده را پاک میکند."""
        SelfProfile.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------
# منو
# ------------------------------------------------------------
class MenuView(APIView):
    def get(self, request):
        """وعده‌های قابل رزرو این هفته، با غذاها و سلف‌ها."""
        return run_with_client(request.user, lambda client: client.get_open_meals())


# ------------------------------------------------------------
# رزروهای ثبت‌شده
# ------------------------------------------------------------
def simplify_reservations(client):
    result = []
    for info in client.get_reservations():
        r = info["reserved"]
        result.append({
            "date": info["date"],
            "day_title": info["day_title"],
            "meal_id": r["MealId"],
            "meal_name": info["meal_name"],
            "food_id": r["FoodId"],
            "food_name": r["FoodName"],
            "self_id": r["SelfId"],
            "self_name": r["SelfName"],
            "price": r["Price"],
            "reserve_id": r["ReserveId"],
            "reserve_number": r["ReserveNumber"],
        })
    return result


class ReservationsView(APIView):
    def get(self, request):
        """رزروهایی که الان ثبت شده‌اند."""
        return run_with_client(request.user, simplify_reservations)


# ------------------------------------------------------------
# رزرو و لغو
# ------------------------------------------------------------
class ReserveSerializer(serializers.Serializer):
    # React فقط «کدام وعده، کدام غذا، کدام سلف» را میگوید.
    # قیمت را عمداً از React نمیگیریم؛ سرور خودش از منوی سلف برمیدارد.
    date = serializers.CharField(max_length=10)
    meal_id = serializers.IntegerField()
    food_id = serializers.IntegerField()
    self_id = serializers.IntegerField()


class ReserveView(APIView):
    def post(self, request):
        """یک غذا را برای کاربر رزرو میکند."""
        serializer = ReserveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        def action(client):
            meal = next(
                (m for m in client.get_open_meals()
                 if m["date"] == d["date"] and m["meal_id"] == d["meal_id"]),
                None,
            )
            if meal is None:
                raise SelfError("این وعده الان قابل رزرو نیست")

            food = next((f for f in meal["foods"] if f["food_id"] == d["food_id"]), None)
            if food is None:
                raise SelfError("این غذا در این وعده وجود ندارد")

            self_item = next((s for s in food["selfs"] if s["self_id"] == d["self_id"]), None)
            if self_item is None:
                raise SelfError("این غذا در این سلف ارائه نمیشود")

            result = client.reserve_food(meal, food, self_item)
            return {
                "message": result["StateMessage"],
                "reserve_id": result["ID"],
                "reserve_number": result["ReserveNumber"],
            }

        return run_with_client(request.user, action)


class CancelSerializer(serializers.Serializer):
    reserve_id = serializers.IntegerField()


class CancelView(APIView):
    def post(self, request):
        """یک رزرو را لغو میکند (reserve_id را از فهرست رزروها بردار)."""
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reserve_id = serializer.validated_data["reserve_id"]

        def action(client):
            # فقط بین رزروهای همین کاربر میگردیم، پس نمیشود رزرو دیگران را لغو کرد
            info = next(
                (i for i in client.get_reservations()
                 if i["reserved"]["ReserveId"] == reserve_id),
                None,
            )
            if info is None:
                raise SelfError("رزروی با این شناسه پیدا نشد")

            result = client.cancel_reservation(info)
            return {"message": result["StateMessage"]}

        return run_with_client(request.user, action)