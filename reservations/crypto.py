"""
crypto.py
رمزنگاری و رمزگشایی متن با کلیدی که در متغیر محیطی SELF_ENCRYPTION_KEY است.
"""

import os

from cryptography.fernet import Fernet


def _get_fernet():
    key = os.environ.get("SELF_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("متغیر محیطی SELF_ENCRYPTION_KEY تنظیم نشده است")
    return Fernet(key.encode())


def encrypt_text(text):
    """متن عادی را میگیرد و متن رمزنگاری‌شده برمیگرداند."""
    return _get_fernet().encrypt(text.encode()).decode()


def decrypt_text(token):
    """متن رمزنگاری‌شده را میگیرد و متن اصلی را برمیگرداند."""
    return _get_fernet().decrypt(token.encode()).decode()