"""
reservations/api_views.py
API اتصال به سلف، دیدن منو و دیدن رزروها برای React.
رمز سلف هیچ‌وقت در جواب برگردانده نمیشود.
"""

import requests
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    DislikedFood,
    Food,
    FoodPreference,
    FoodPriority,
    MealSlot,
    SelfProfile,
)
from .self_client import SelfError
from .services import get_logged_in_client, save_self_credentials, update_food_catalog


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
        """وعده‌های قابل رزرو این هفته، با غذاها، نوع غذا و سلف‌ها."""

        def action(client):
            menu = client.get_menu()
            update_food_catalog(menu)  # غذاهای تازه به فهرست غذاها اضافه میشوند
            return client.get_open_meals(menu)

        return run_with_client(request.user, action)


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


# ------------------------------------------------------------
# فهرست غذاها
# ------------------------------------------------------------
class FoodsView(APIView):
    def get(self, request):
        """همه غذاهایی که تا الان در منوی سلف دیده‌ایم (برای ساختن لیست اولویت)."""
        foods = Food.objects.all()
        return Response([
            {
                "food_id": f.food_id,
                "name": f.name,
                "food_type": f.food_type,
                "food_type_name": f.food_type_name,
            }
            for f in foods
        ])


# ------------------------------------------------------------
# ترجیحات: اولویت غذاها، غذاهای نمیخورم، گزینه آخر و برنامه دلخواه
# ------------------------------------------------------------
class SlotSerializer(serializers.Serializer):
    day_of_week = serializers.IntegerField(min_value=0, max_value=6)
    meal_id = serializers.IntegerField(min_value=1, max_value=3)
    self_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    self_name = serializers.CharField(required=False, allow_blank=True, default="")


class PreferencesSerializer(serializers.Serializer):
    # همه فیلدها اختیاری‌اند: فیلدی که نفرستی، همان‌طور که بود میماند
    priorities = serializers.ListField(child=serializers.IntegerField(), required=False)
    disliked = serializers.ListField(child=serializers.IntegerField(), required=False)
    fallback = serializers.ChoiceField(
        choices=[c[0] for c in FoodPreference.FALLBACK_CHOICES], required=False
    )
    slots = SlotSerializer(many=True, required=False)

    def validate(self, data):
        errors = {}

        for key in ("priorities", "disliked"):
            ids = data.get(key)
            if ids is not None and len(set(ids)) != len(ids):
                errors[key] = ["یک غذا نمیتواند دو بار در این لیست باشد"]

        all_ids = list(data.get("priorities", [])) + list(data.get("disliked", []))
        known = set(Food.objects.filter(food_id__in=all_ids).values_list("food_id", flat=True))
        unknown = sorted(set(all_ids) - known)
        if unknown:
            errors["foods"] = ["غذای نامعتبر: %s" % ", ".join(str(i) for i in unknown)]

        slots = data.get("slots")
        if slots is not None:
            keys = [(s["day_of_week"], s["meal_id"]) for s in slots]
            if len(set(keys)) != len(keys):
                errors["slots"] = ["برای هر روز و وعده فقط یک سلف میشود تعیین کرد"]

        if errors:
            raise serializers.ValidationError(errors)
        return data


def preferences_data(user):
    preference = FoodPreference.objects.filter(user=user).first()
    return {
        "priorities": [
            {
                "food_id": p.food.food_id,
                "name": p.food.name,
                "food_type_name": p.food.food_type_name,
            }
            for p in FoodPriority.objects.filter(user=user).select_related("food")
        ],
        "disliked": [
            {"food_id": d.food.food_id, "name": d.food.name}
            for d in DislikedFood.objects.filter(user=user).select_related("food")
        ],
        "fallback": preference.fallback if preference else FoodPreference.ANY_AVAILABLE,
        "slots": [
            {
                "day_of_week": s.day_of_week,
                "meal_id": s.meal_id,
                "self_id": s.self_id,
                "self_name": s.self_name,
            }
            for s in MealSlot.objects.filter(user=user)
        ],
    }


class PreferencesView(APIView):
    def get(self, request):
        return Response(preferences_data(request.user))

    def put(self, request):
        """ترجیحات را جایگزین میکند (هر بخشی که نفرستی، تغییر نمیکند)."""
        serializer = PreferencesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        user = request.user

        # یک غذا نباید هم در اولویت‌ها باشد و هم در «نمیخورم»
        final_priorities = d.get("priorities")
        if final_priorities is None:
            final_priorities = FoodPriority.objects.filter(user=user).values_list("food__food_id", flat=True)
        final_disliked = d.get("disliked")
        if final_disliked is None:
            final_disliked = DislikedFood.objects.filter(user=user).values_list("food__food_id", flat=True)
        if set(final_priorities) & set(final_disliked):
            return Response(
                {"detail": "یک غذا نمیتواند هم در اولویت‌ها و هم در «غذاهایی که نمیخورم» باشد"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            if "priorities" in d:
                FoodPriority.objects.filter(user=user).delete()
                foods = {f.food_id: f for f in Food.objects.filter(food_id__in=d["priorities"])}
                FoodPriority.objects.bulk_create([
                    FoodPriority(user=user, food=foods[food_id], position=position)
                    for position, food_id in enumerate(d["priorities"], start=1)
                ])

            if "disliked" in d:
                DislikedFood.objects.filter(user=user).delete()
                foods = {f.food_id: f for f in Food.objects.filter(food_id__in=d["disliked"])}
                DislikedFood.objects.bulk_create([
                    DislikedFood(user=user, food=foods[food_id]) for food_id in d["disliked"]
                ])

            if "fallback" in d:
                FoodPreference.objects.update_or_create(user=user, defaults={"fallback": d["fallback"]})

            if "slots" in d:
                MealSlot.objects.filter(user=user).delete()
                MealSlot.objects.bulk_create([
                    MealSlot(
                        user=user,
                        day_of_week=s["day_of_week"],
                        meal_id=s["meal_id"],
                        self_id=s["self_id"],
                        self_name=s["self_name"],
                    )
                    for s in d["slots"]
                ])

        return Response(preferences_data(user))