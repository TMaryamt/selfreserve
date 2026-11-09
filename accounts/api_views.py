"""
accounts/api_views.py
API ثبت‌نام، ورود، خروج و اطلاعات کاربر برای React (همه JSON).
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import EmailMessage
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from reservations.models import SelfProfile

from .models import PasswordReset, Profile
from .serializers import (
    ForgotPasswordSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
)

RESET_LIFETIME = timedelta(minutes=10)  # عمر لینک بازیابی رمز


def user_data(user):
    """اطلاعاتی از کاربر که به React داده میشود (هیچ رمزی در آن نیست)."""
    profile = Profile.objects.filter(user=user).first()
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone_number": profile.phone_number if profile else None,
        "has_self_profile": SelfProfile.objects.filter(user=user).exists(),
    }


class RegisterView(APIView):
    # این دو خط یعنی «برای ثبت‌نام لازم نیست کاربر وارد شده باشد»
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # اگر خطا داشت، خودش 400 برمیگرداند
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key, "user": user_data(user)},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        username = str(request.data.get("username", "")).lower().strip()
        password = str(request.data.get("password", ""))

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {"detail": "نام کاربری یا رمز عبور اشتباه است"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": user_data(user)})


class LogoutView(APIView):
    # permission پیش‌فرض (IsAuthenticated) اینجا هم اعمال میشود، یعنی فقط کاربر واردشده
    def post(self, request):
        request.auth.delete()  # توکن حذف میشود، پس توکن قبلی دیگر کار نمیکند
        return Response({"detail": "خروج انجام شد"})


class MeView(APIView):
    def get(self, request):
        return Response(user_data(request.user))



class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        """لینک بازیابی رمز را ایمیل میکند. جواب همیشه یکسان است."""
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower().strip()

        user = User.objects.filter(email=email).first()
        if user:
            # لینک‌های قبلی این کاربر باطل میشوند؛ فقط آخرین لینک معتبر است
            PasswordReset.objects.filter(user=user).delete()
            reset = PasswordReset.objects.create(user=user)

            # لینک به صفحه React میرود، نه به خود جنگو
            link = "%s/reset-password/%s" % (settings.FRONTEND_URL.rstrip("/"), reset.reset_id)
            if settings.DEBUG:
                # فقط در حالت توسعه: لینک را خوانا در ترمینال سرور چاپ میکنیم
                print("RESET LINK:", link)
            EmailMessage(
                "بازیابی رمز عبور",
                "برای تعیین رمز جدید روی لینک زیر بزنید (10 دقیقه اعتبار دارد):\n\n" + link,
                settings.DEFAULT_FROM_EMAIL,
                [email],
            ).send(fail_silently=True)

        # عمداً در هر دو حالت (ایمیل هست یا نیست) یک پیام میدهیم
        return Response({"detail": "اگر این ایمیل ثبت شده باشد، لینک بازیابی برایش ارسال شد."})


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        """با reset_id که از لینک ایمیل آمده، رمز جدید را ثبت میکند."""
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        reset = PasswordReset.objects.filter(reset_id=d["reset_id"]).select_related("user").first()
        if reset is None:
            return Response({"detail": "لینک بازیابی نامعتبر است"}, status=status.HTTP_400_BAD_REQUEST)

        if timezone.now() > reset.created_when + RESET_LIFETIME:
            reset.delete()
            return Response({"detail": "لینک بازیابی منقضی شده است"}, status=status.HTTP_400_BAD_REQUEST)

        user = reset.user
        try:
            validate_password(d["password"], user=user)
        except DjangoValidationError as error:
            return Response({"password": list(error.messages)}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(d["password"])
        user.save()

        # لینک فقط یک بار قابل استفاده است، و ورودهای قبلی (توکن‌ها) باطل میشوند
        PasswordReset.objects.filter(user=user).delete()
        Token.objects.filter(user=user).delete()

        return Response({"detail": "رمز عبور با موفقیت تغییر کرد"})