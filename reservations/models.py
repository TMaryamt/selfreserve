from django.conf import settings
from django.db import models

from .crypto import decrypt_text, encrypt_text


class SelfProfile(models.Model):
    """اطلاعات ورود کاربر به سامانه سلف (جدا از حساب خود اپ)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    self_username = models.CharField(max_length=100)
    encrypted_password = models.TextField()  # رمز سلف، فقط به شکل رمزنگاری‌شده
    updated_at = models.DateTimeField(auto_now=True)

    def set_self_password(self, raw_password):
        self.encrypted_password = encrypt_text(raw_password)

    def get_self_password(self):
        return decrypt_text(self.encrypted_password)

    def __str__(self):
        return "SelfProfile of %s" % self.user.username