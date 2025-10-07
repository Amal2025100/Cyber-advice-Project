from __future__ import annotations
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    # معرّف المستخدم الأساسي
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # البريد الإلكتروني فريد ويستخدم لتسجيل الدخول
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    # تخزين هاش كلمة المرور وليس النص الصريح
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # تاريخ الإنشاء
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # علاقة واحد-إلى-متعدد مع سجل الأسئلة
    history: Mapped[list[QuestionHistory]] = relationship("QuestionHistory", back_populates="user", cascade="all, delete-orphan")


class QuestionHistory(Base):
    __tablename__ = "question_history"

    # سجل لأسئلة المستخدم والتصنيف والنصيحة المعادة
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    advice: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # مرجع إلى المستخدم المالك للسجل
    user: Mapped[User] = relationship("User", back_populates="history")
