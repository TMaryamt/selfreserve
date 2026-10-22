from django.shortcuts import render

# Create your views here.
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import PasswordReset, Profile


# ---------------------------------------------------------------
# تابع کمکی: بررسی قوی بودن رمز با قوانین خود جنگو
# (طول حداقل، رمزهای رایج مثل 12345678، فقط عدد نبودن و ...)
# ---------------------------------------------------------------
def password_errors(password, user=None):
    try:
        validate_password(password, user=user)
        return []
    except ValidationError as e:
        return list(e.messages)


# ---------------------------------------------------------------
# ورود
# ---------------------------------------------------------------
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').lower().strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')
            return redirect('login')

    return render(request, 'accounts/login.html')


# ---------------------------------------------------------------
# ثبت‌نام
# ---------------------------------------------------------------
def register_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip().capitalize()
        last_name = request.POST.get('last_name', '').strip().capitalize()
        username = request.POST.get('username', '').lower().strip().replace(' ', '')
        email = request.POST.get('email', '').lower().strip()
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        has_error = False

        if not username:
            has_error = True
            messages.error(request, 'username is required')
        elif User.objects.filter(username=username).exists():
            has_error = True
            messages.error(request, 'username already exists!')

        if not email:
            has_error = True
            messages.error(request, 'email is required')
        elif User.objects.filter(email=email).exists():
            has_error = True
            messages.error(request, 'this email already exists')

        if not phone_number:
            has_error = True
            messages.error(request, 'phone number is required')
        elif Profile.objects.filter(phone_number=phone_number).exists():
            has_error = True
            messages.error(request, 'this phone number belongs to another account')

        if password != confirm_password:
            has_error = True
            messages.error(request, 'passwords do not match')

        for error in password_errors(password):
            has_error = True
            messages.error(request, error)

        if not has_error:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            Profile.objects.create(user=user, phone_number=phone_number)
            messages.success(request, 'Account created. Login now')
            return redirect('login')

        # خطا داشتیم: فرم دوباره نشان داده میشود، با مقادیری که کاربر زده بود
        # (رمز عمداً برنگردانده میشود)
        return render(request, 'accounts/register.html', {
            'first_name': first_name,
            'last_name': last_name,
            'username': username,
            'email': email,
            'phone_number': phone_number,
        })

    return render(request, 'accounts/register.html')


# ---------------------------------------------------------------
# خروج
# ---------------------------------------------------------------
def logout_view(request):
    logout(request)
    messages.success(request, 'Logout successful.')
    return redirect('login')


# ---------------------------------------------------------------
# فراموشی رمز
# ---------------------------------------------------------------
def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').lower().strip()
        user = User.objects.filter(email=email).first()

        if user:
            reset = PasswordReset.objects.create(user=user)
            path = reverse('reset-password', kwargs={'reset_id': reset.reset_id})
            link = request.build_absolute_uri(path)

            EmailMessage(
                'Reset your password',
                f'Reset your password using the link below:\n\n{link}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
            ).send(fail_silently=True)

        # پیام عمداً در هر دو حالت (ایمیل هست / نیست) یکسان است
        messages.success(request, 'If this email is registered, a reset link was sent.')
        return redirect('password-reset-sent')

    return render(request, 'accounts/forgot_password.html')


# ---------------------------------------------------------------
# صفحه «ایمیل ارسال شد» (بدون reset_id)
# ---------------------------------------------------------------
def password_reset_sent(request):
    return render(request, 'accounts/password_reset_sent.html')


# ---------------------------------------------------------------
# تعیین رمز جدید
# ---------------------------------------------------------------
def reset_password(request, reset_id):
    try:
        reset = PasswordReset.objects.get(reset_id=reset_id)
    except PasswordReset.DoesNotExist:
        messages.error(request, 'Invalid reset id')
        return redirect('forgot-password')

    # انقضا برای GET و POST هر دو چک میشود
    if timezone.now() > reset.created_when + timedelta(minutes=10):
        reset.delete()
        messages.error(request, 'Reset link has expired')
        return redirect('forgot-password')

    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        has_error = False

        if password != confirm_password:
            has_error = True
            messages.error(request, 'Passwords do not match')

        for error in password_errors(password, user=reset.user):
            has_error = True
            messages.error(request, error)

        if has_error:
            return redirect('reset-password', reset_id=reset_id)

        user = reset.user
        user.set_password(password)
        user.save()
        reset.delete()

        messages.success(request, 'Password reset successful. Proceed to login')
        return redirect('login')

    return render(request, 'accounts/reset_password.html')
