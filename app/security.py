from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# استخدام خوارزمية pbkdf2_sha256 لتجنّب حد 72 بايت في bcrypt
# هذا الكائن مسؤول عن عمليات هاش كلمة المرور والتحقق منها بأمان
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    # دالة لعمل هاش لكلمة المرور وتخزينها بدلاً من النص الصريح
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    # دالة لمقارنة كلمة المرور المدخلة مع الهاش المخزن
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    # إنشاء توكن JWT يحتوي هوية المستخدم (sub) وتاريخ انتهاء الصلاحية
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"sub": subject, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[str]:
    # فك تشفير التوكن JWT وإرجاع البريد/المعرّف الموجود في الحقل "sub"
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if sub is None:
            return None
        return sub
    except JWTError:
        # في حال كان التوكن غير صالح أو منتهي الصلاحية
        return None
