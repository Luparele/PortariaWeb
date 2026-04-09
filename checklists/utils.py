from cryptography.fernet import Fernet
from django.conf import settings
import base64
import hashlib

def get_cipher():
    # Use SECRET_KEY to derive a consistent 32-byte key for Fernet
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    key_base64 = base64.urlsafe_b64encode(key)
    return Fernet(key_base64)

def encrypt_password(password):
    if not password:
        return ""
    cipher = get_cipher()
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password):
    if not encrypted_password:
        return ""
    try:
        cipher = get_cipher()
        return cipher.decrypt(encrypted_password.encode()).decode()
    except Exception:
        return ""
