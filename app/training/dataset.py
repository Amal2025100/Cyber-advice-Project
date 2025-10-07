from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import pandas as pd
from app.config import TRAINING_CSV

@dataclass
class Dataset:
    # يمثل مجموعة بيانات نصية مع التصنيفات المقابلة
    texts: List[str]
    labels: List[str]


def load_dataset() -> Dataset:
    # تحميل بيانات التدريب من ملف CSV مع عمودين: text و label
    df = pd.read_csv(TRAINING_CSV)
    if "text" not in df.columns or "label" not in df.columns:
        raise ValueError("training.csv must have 'text' and 'label' columns")
    texts = df["text"].astype(str).tolist()
    labels = df["label"].astype(str).tolist()
    return Dataset(texts=texts, labels=labels)
