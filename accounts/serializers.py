"""
accounts/serializers.py
Serializer یعنی «مترجم بین JSON و دیتابیس»: ورودی React را چک میکند و تبدیل میکند.
"""

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from .models import Profile


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    # هر تابع validate_<اسم فیلد> فقط همان فیلد را چک میکند
    def validate_username(self, value):
        value = value.lower().strip().replace(" ", "")
        if not value:
            raise serializers.ValidationError("نام کاربری نمیتواند خالی باشد")
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("این نام کاربری قبلاً ثبت شده است")
        return value

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("این ایمیل قبلاً ثبت شده است")
        return value

    def validate_phone_number(self, value):
        value = value.strip()
        if Profile.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("این شماره تلفن متعلق به حساب دیگری است")
        return value

    # validate بدون اسم، چند فیلد را با هم چک میکند
    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "رمزها یکسان نیستند"})

        user_stub = User(
            username=data["username"],
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
        )
        try:
            validate_password(data["password"], user=user_stub)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)})

        return data

    def create(self, validated_data):
        # atomic یعنی یا کاربر و پروفایل هر دو ساخته شوند، یا هیچکدام
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data["username"],
                email=validated_data["email"],
                password=validated_data["password"],
                first_name=validated_data["first_name"].capitalize(),
                last_name=validated_data["last_name"].capitalize(),
            )
            Profile.objects.create(user=user, phone_number=validated_data["phone_number"])
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    reset_id = serializers.UUIDField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "رمزها یکسان نیستند"})
        return data