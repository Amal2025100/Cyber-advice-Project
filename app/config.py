from pathlib import Path

# المسارات الأساسية للتطبيق
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# مسار بيانات التدريب ونموذج التصنيف
TRAINING_CSV = DATA_DIR / "training.csv"
MODEL_PATH = MODELS_DIR / "model.joblib"

# إعدادات الأمان للتوكن JWT
# ملاحظة: استبدل القيمة بمُتغيّر بيئة في الإنتاج
SECRET_KEY = "change-this-secret-in-env"
ALGORITHM = "HS256"
# مدة صلاحية التوكن بالدقائق (8 ساعات)
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours
