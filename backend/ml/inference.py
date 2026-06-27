# ml/inference.py — зарежда LSTM и BiLSTM моделите и предоставя predict().
# Не зависи от Flask или базата — само от TensorFlow и preprocessing.py.

import os
import pickle
from typing import List, Dict

import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences

from .preprocessing import preprocess_text


# ─── Пътища ────────────────────────────────────────────────────────────
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_MODELS_DIR = os.path.join(_THIS_DIR, 'models')

LSTM_PATH          = os.path.join(_MODELS_DIR, 'best_lstm_model.keras')
BILSTM_PATH        = os.path.join(_MODELS_DIR, 'best_bilstm_model.keras')
TOKENIZER_PATH     = os.path.join(_MODELS_DIR, 'tokenizer.pkl')
LABEL_MAPPING_PATH = os.path.join(_MODELS_DIR, 'label_mapping.pkl')


# ─── Константи (синхронизирани с preprocessing_config.json) ────────────
MAX_SEQUENCE_LENGTH = 20

# Центрове на sentiment интервалите → за weighted average rating
# neg ≤ 2.0   → център 1.0
# neu 2.5–3.5 → център 3.0
# pos ≥ 4.0   → център 5.0
# ВАЖНО: редът трябва да съответства на label_mapping (neg=0, neu=1, pos=2)
CLASS_RATINGS = np.array([1.0, 3.0, 5.0], dtype=np.float32)


# ─── Singleton за заредените артефакти ─────────────────────────────────
_lstm_model    = None
_bilstm_model  = None
_tokenizer     = None
_label_mapping = None


def _load_artifacts():
    """Зарежда модели и tokenizer веднъж (lazy). Извиква се при първи predict()."""
    global _lstm_model, _bilstm_model, _tokenizer, _label_mapping

    if _lstm_model is not None:
        return

    print('[ml.inference] Зареждане на LSTM модел...')
    _lstm_model = load_model(LSTM_PATH)

    print('[ml.inference] Зареждане на BiLSTM модел...')
    _bilstm_model = load_model(BILSTM_PATH)

    print('[ml.inference] Зареждане на tokenizer...')
    with open(TOKENIZER_PATH, 'rb') as f:
        _tokenizer = pickle.load(f)

    print('[ml.inference] Зареждане на label mapping...')
    with open(LABEL_MAPPING_PATH, 'rb') as f:
        _label_mapping = pickle.load(f)

    print(f'[ml.inference] Готово. Label mapping: {_label_mapping}')


def warmup():
    """Принудително зарежда моделите — извикай при Flask startup."""
    _load_artifacts()


def predict(texts: List[str]) -> List[Dict[str, float]]:
    """Batch предсказание — връща lstm_rating и bilstm_rating (1.0–5.0) за всеки текст."""
    if not texts:
        return []

    _load_artifacts()

    # 1. Препроцесинг (точно същия като в тренировката)
    cleaned = [preprocess_text(t) for t in texts]

    # 2. Tokenization (същия tokenizer от тренировката)
    sequences = _tokenizer.texts_to_sequences(cleaned)

    # 3. Padding до фиксирана дължина (както при тренировката)
    padded = pad_sequences(
        sequences,
        maxlen=MAX_SEQUENCE_LENGTH,
        padding='post',
        truncating='post',
    )

    # 4. Batch predict с двата модела (verbose=0 за да не спами конзолата)
    lstm_probs   = _lstm_model.predict(padded, verbose=0)    # shape: (N, 3)
    bilstm_probs = _bilstm_model.predict(padded, verbose=0)  # shape: (N, 3)

    # 5. Weighted average rating — np.dot работи vectorized
    lstm_ratings   = np.dot(lstm_probs, CLASS_RATINGS)    # shape: (N,)
    bilstm_ratings = np.dot(bilstm_probs, CLASS_RATINGS)  # shape: (N,)

    # 6. Опаковане в списък от речници
    results = []
    for lstm_r, bilstm_r in zip(lstm_ratings, bilstm_ratings):
        results.append({
            'lstm_rating':   round(float(lstm_r), 2),
            'bilstm_rating': round(float(bilstm_r), 2),
        })

    return results


def predict_one(text: str) -> Dict[str, float]:
    """Удобна обвивка за единичен текст. Връща един речник, не списък."""
    return predict([text])[0]