from __future__ import annotations
from fastapi import FastAPI, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr

from app.config import MODEL_PATH, TRAINING_CSV
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
import joblib
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import pandas as pd
from typing import Optional, List
import re

from app.db import SessionLocal, init_db
from sqlalchemy.orm import Session
from app.db_models import User
from app.security import hash_password, verify_password, create_access_token, decode_token

# تطبيق واجهة برمجة FastAPI لنصائح الأمن السيبراني
app = FastAPI(title="Cyber Security Advice API", version="2.0.0")

class AskRequest(BaseModel):
    # طلب السؤال من المستخدم
    question: str

class AskResponse(BaseModel):
    # الاستجابة تتضمن التصنيف المقترح، النصيحة، ومصادرها
    category: str
    advice: str
    sources: list[str]


class SignupRequest(BaseModel):
    # بيانات التسجيل
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    # بيانات تسجيل الدخول
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    # استجابة تتضمن توكن JWT
    access_token: str
    token_type: str = "bearer"


# No persistent history objects; we keep responses ephemeral on the frontend


def _startup():
    # تهيئة التطبيق عند الإقلاع: تحميل النموذج والبيانات المساندة وتmount الواجهة الثابتة
    # Load model if available; else allow cold start without model
    app.state.model = None
    if MODEL_PATH.exists():
        app.state.model = joblib.load(MODEL_PATH)
    # Predefined advice per category (Arabic)
    app.state.advice = {
        "phishing": (
            "تأكد من عنوان المرسل والروابط قبل النقر. لا تُدخل بياناتك في صفحات غير موثوقة. "
            "فعّل المصادقة متعددة العوامل، وأبلغ عن الرسالة إن كانت مشبوهة."
        ),
        "passwords": (
            "استخدم كلمات مرور طويلة وفريدة مع مدير كلمات المرور. فعّل المصادقة متعددة العوامل "
            "ولا تعِد استخدام نفس الكلمة في أكثر من موقع."
        ),
        "malware": (
            "حدّث النظام ومضاد الفيروسات. لا تفتح المرفقات المشبوهة. افصل الجهاز عن الشبكة وابدأ فحصاً كاملاً، "
            "واستعد من النسخ الاحتياطية إن لزم."
        ),
        "networks": (
            "فعّل تشفير WPA2/WPA3، وبدّل كلمة مرور الراوتر الافتراضية. حدّث الراوتر دورياً، وفعّل جدار الحماية."
        ),
        "incident_response": (
            "غيّر كلمات المرور وفعّل MFA فوراً. أوقف الجلسات المشبوهة، راجع السجلات، تواصل مع الدعم الأمني، "
            "واجرِ فحوصات للأجهزة."
        ),
        "general": (
            "اتبع أفضل الممارسات الأساسية: تحديثات، كلمات مرور قوية، MFA، وحذر من الروابط والمرفقات."
        ),
    }
    # Load intent-based advice from JSON
    advice_path = Path(__file__).resolve().parents[1] / "data" / "advice.json"
    if advice_path.exists():
        with advice_path.open("r", encoding="utf-8") as f:
            app.state.advice_intents = json.load(f)
    else:
        app.state.advice_intents = {}

    # Load seed exact answers
    seed_path = Path(__file__).resolve().parents[1] / "data" / "seed_answers.json"
    app.state.seed_answers = {}
    app.state.seed_answers_norm = {}
    if seed_path.exists():
        try:
            app.state.seed_answers = json.loads(seed_path.read_text(encoding="utf-8"))
        except Exception:
            app.state.seed_answers = {}

    # Arabic normalization helpers
    arabic_diacritics = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
    def normalize_ar(s: str) -> str:
        if not isinstance(s, str):
            return ""
        s = s.strip().lower()
        s = arabic_diacritics.sub("", s)
        s = s.replace("\u0640", "")  # tatweel
        s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي").replace("ة", "ه")
        # Remove common quotes and punctuation to improve exact matching
        # This covers ASCII quotes, Arabic quotes, and typical punctuation including Arabic question mark
        s = re.sub(r"[\"'“”‘’«».,!؟?؛:()\[\]{}<>/\\|-]+", " ", s)
        s = re.sub(r"\s+", " ", s)
        return s
    app.state.normalize_ar = normalize_ar
    # Build normalized seed map
    for q, a in app.state.seed_answers.items():
        app.state.seed_answers_norm[normalize_ar(q)] = a

    # Build NN index over training questions for exact/near matches
    try:
        df_train = pd.read_csv(TRAINING_CSV)
        texts = df_train["text"].astype(str).tolist()
        # char n-grams work better for العربية
        nn_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3,5))
        nn_matrix = nn_vectorizer.fit_transform(texts)
        app.state.train_df = df_train
        app.state.nn_vec = nn_vectorizer
        app.state.nn_mx = nn_matrix
    except Exception:
        app.state.train_df = None
        app.state.nn_vec = None
        app.state.nn_mx = None

    # Mount static UI
    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    init_db()


app.add_event_handler("startup", _startup)


def get_db():
    # تزويد جلسة قاعدة البيانات لكل طلب ثم إغلاقها
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(db: Session = Depends(get_db), authorization: Optional[str] = Header(default=None)) -> User:
    # استخراج المستخدم الحالي من ترويسة Authorization بنمط Bearer <token>
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token required")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth header")
    email = decode_token(parts[1])
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@app.post("/auth/signup", response_model=TokenResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    # إنشاء مستخدم جديد وتوليد توكن مباشرة بعد التسجيل
    exists = db.query(User).filter(User.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token)


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    # التحقق من البريد وكلمة المرور ثم إعادة توكن جديد
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token)


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # نقطة النهاية الرئيسية: تتنبأ بالفئة وتعيد نصيحة عربية مناسبة
    question = req.question.strip()

    # Predict category if model exists
    category = "general"
    if app.state.model is not None and question:
        category = app.state.model.predict([question])[0]

    # Try intent-based advice within the predicted category
    advice = None
    # 0) Exact match against seed answers (normalized)
    if hasattr(app.state, "normalize_ar") and getattr(app.state, "seed_answers_norm", None):
        qn = app.state.normalize_ar(question)
        if qn in app.state.seed_answers_norm:
            advice = app.state.seed_answers_norm[qn]
            sources = ["seed_answers"]
            return AskResponse(category=category, advice=advice, sources=sources)
    # 1) Exact/near match to a training question -> use curated answer if available
    if getattr(app.state, "nn_vec", None) is not None and getattr(app.state, "nn_mx", None) is not None:
        try:
            qv2 = app.state.nn_vec.transform([question])
            sims2 = linear_kernel(qv2, app.state.nn_mx).ravel()
            idx2 = sims2.argmax()
            top_sim = float(sims2[idx2])
            if top_sim >= 0.70:
                row = app.state.train_df.iloc[idx2]
                if "answer" in app.state.train_df.columns and isinstance(row.get("answer"), str) and row.get("answer").strip():
                    advice = row.get("answer").strip()
        except Exception:
            pass

    # 2) Otherwise, intent-based within predicted category
    intents = getattr(app.state, "advice_intents", {}).get(category, [])
    if intents:
        corpus = [" ".join(it.get("patterns", [])) for it in intents]
        tfidf = TfidfVectorizer(ngram_range=(1,2))
        try:
            X = tfidf.fit_transform(corpus)
            qv = tfidf.transform([question])
            sims = linear_kernel(qv, X).ravel()
            idx = sims.argmax()
            if sims[idx] > 0:
                advice = intents[idx].get("advice")
        except Exception:
            advice = None
    # Fallback to generic advice
    if not advice:
        if not hasattr(app.state, "advice"):
            app.state.advice = {"general": "اتبع أفضل الممارسات الأساسية: تحديثات، كلمات مرور قوية، MFA، وحذر من الروابط والمرفقات."}
        advice = app.state.advice.get(category, app.state.advice.get("general", ""))
    sources = ["model", "built_in_advice"]

    return AskResponse(category=category, advice=advice, sources=list(dict.fromkeys(sources)))



@app.get("/", response_class=HTMLResponse)
def index():
    # تقديم واجهة المستخدم الأحادية الصفحة من مجلد static
    # Serve the single-page UI
    html_path = Path(__file__).resolve().parent / "static" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"), status_code=200)


@app.get("/debug/predict")
def debug_predict(q: str):
    # مساعدة للتجربة: تعيد الفئة المتوقعة للسؤال بدون مصادقة
    if not q:
        return {"error": "missing q"}
    cat = "general"
    if app.state.model is not None:
        cat = app.state.model.predict([q])[0]
    return {"category": cat}


@app.get("/training/stats")
def training_stats():
    # إحصاءات سريعة عن ملف التدريب (الإجمالي وتوزيع الفئات)
    try:
        df = pd.read_csv(TRAINING_CSV)
        total = int(len(df))
        dist = df["label"].value_counts().to_dict()
        return {"total": total, "distribution": dist}
    except Exception as e:
        return {"error": str(e)}


@app.get("/admin/reload_seed")
def admin_reload_seed():
    # إعادة تحميل الإجابات المطابقة للبذور من الملف دون إعادة تشغيل الخادم
    seed_path = Path(__file__).resolve().parents[1] / "data" / "seed_answers.json"
    app.state.seed_answers = {}
    app.state.seed_answers_norm = {}
    if seed_path.exists():
        try:
            app.state.seed_answers = json.loads(seed_path.read_text(encoding="utf-8"))
        except Exception as e:
            return {"error": str(e)}
    norm = getattr(app.state, "normalize_ar", lambda s: s)
    for q, a in app.state.seed_answers.items():
        app.state.seed_answers_norm[norm(q)] = a
    return {"ok": True, "count": len(app.state.seed_answers_norm)}


@app.get("/admin/reload_advice")
def admin_reload_advice():
    # إعادة تحميل ملف النصائح المقترنة بأنماط الأسئلة
    advice_path = Path(__file__).resolve().parents[1] / "data" / "advice.json"
    if advice_path.exists():
        try:
            app.state.advice_intents = json.loads(advice_path.read_text(encoding="utf-8"))
            return {"ok": True, "categories": list(app.state.advice_intents.keys())}
        except Exception as e:
            return {"error": str(e)}
    return {"ok": False, "reason": "advice.json not found"}


@app.get("/auth", response_class=HTMLResponse)
def auth_page():
    # صفحة بسيطة لتجربة التسجيل/الدخول من الواجهة
    html_path = Path(__file__).resolve().parent / "static" / "auth.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"), status_code=200)
