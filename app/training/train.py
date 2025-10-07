from __future__ import annotations
import joblib
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from app.training.dataset import load_dataset
from app.config import MODEL_PATH


def build_pipeline() -> Pipeline:
    # إنشاء بايبلاين يتكون من:
    # - TF-IDF لاستخراج السمات النصية
    # - مصنف خطي SVM للتصنيف السريع والفعال
    return Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=20000)),
        ("clf", LinearSVC()),
    ])


def main():
    # تحميل البيانات وتقسيمها إلى تدريب/اختبار بشكل متوازن بين التصنيفات
    data = load_dataset()
    X_train, X_test, y_train, y_test = train_test_split(
        data.texts, data.labels, test_size=0.2, random_state=42, stratify=data.labels
    )
    pipe = build_pipeline()
    # تدريب النموذج
    pipe.fit(X_train, y_train)

    # التقييم وطباعة تقرير التصنيف
    y_pred = pipe.predict(X_test)
    print(classification_report(y_test, y_pred))

    # حفظ النموذج المدرب للاستخدام في واجهة البرمجة
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, MODEL_PATH)
    print(f"Saved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()
