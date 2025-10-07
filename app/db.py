from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pathlib import Path

from app.config import BASE_DIR

# مسار قاعدة البيانات (SQLite) داخل مجلد data
DB_PATH = BASE_DIR / "data" / "app.db"
# التأكد من وجود المجلد قبل إنشاء القاعدة
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
# رابط الاتصال بقاعدة البيانات
DATABASE_URL = f"sqlite:///{DB_PATH}"

# إنشاء محرك قاعدة البيانات مع إعدادات خاصة بـ SQLite لاستخدامها عبر عدة خيوط
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
# مُنشئ الجلسات للتعامل مع المعاملات
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    # الصنف الأساسي لجميع نماذج SQLAlchemy
    pass


def init_db():
    # استيراد النماذج لضمان تسجيل الجداول قبل الإنشاء
    from app import db_models  # noqa: F401 ensure models are imported
    # إنشاء الجداول إن لم تكن موجودة
    Base.metadata.create_all(bind=engine)
