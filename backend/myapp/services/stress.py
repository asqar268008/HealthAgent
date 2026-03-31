"""
Stress Prediction Service - Improved version
"""

import os
import joblib
import pandas as pd
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(settings.BASE_DIR, "myapp", "services", "stress.pkl")

# Try to load model, handle gracefully if missing
try:
    model = joblib.load(MODEL_PATH)
    MODEL_LOADED = True
except Exception as e:
    logger.warning(f"Could not load stress model: {str(e)}")
    MODEL_LOADED = False
    model = None

FEATURE_COLUMNS = ["snr", "rr", "bt", "lm", "bo", "rem", "sh", "hr"]

LABELS = {
    0: "Very Low",
    1: "Low",
    2: "Moderate",
    3: "High",
    4: "Severe"
}

SCORE_MAP = {
    0: 15,
    1: 35,
    2: 55,
    3: 75,
    4: 95
}

# Feature descriptions for frontend
FEATURE_DESCRIPTIONS = {
    "snr": "Snoring Rate",
    "rr": "Respiratory Rate",
    "bt": "Body Temperature",
    "lm": "Limb Movement",
    "bo": "Blood Oxygen",
    "rem": "REM Sleep",
    "sh": "Sleep Hours",
    "hr": "Heart Rate"
}


def predict_stress(features_dict):
    """
    Predict stress level based on features
    
    Args:
        features_dict: Dictionary with feature values
        
    Returns:
        int: Prediction class (0-4)
        
    Raises:
        RuntimeError: If model is not loaded
    """
    if not MODEL_LOADED or model is None:
        raise RuntimeError("Stress prediction model not available")

    try:
        # Create DataFrame with correct column order
        df = pd.DataFrame(
            [[features_dict[col] for col in FEATURE_COLUMNS]],
            columns=FEATURE_COLUMNS
        )

        prediction = model.predict(df)[0]
        return int(prediction)

    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise


def stressService(user, additional_data):
    """
    Main service function for stress prediction
    
    Args:
        user: User object
        additional_data: Dictionary containing stress metrics
        
    Returns:
        dict: {stress_level, stress_score}
        
    Raises:
        ValueError: If required features are missing or invalid
        RuntimeError: If model is not available
    """
    if not MODEL_LOADED:
        raise RuntimeError("Stress prediction model is not available")

    features = {}

    # Validate and extract features
    for col in FEATURE_COLUMNS:
        value = additional_data.get(col)

        if value is None:
            raise ValueError(f"Missing required feature: {col}")

        try:
            features[col] = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid value for {col}: must be a number")

    # Validate ranges (optional but recommended)
    if features.get("sh", 0) > 24:
        raise ValueError("Sleep hours cannot exceed 24")
    
    if features.get("rr", 0) > 100:
        raise ValueError("Respiratory rate seems invalid")
    
    if features.get("hr", 0) > 220:
        raise ValueError("Heart rate seems invalid")

    try:
        prediction = predict_stress(features)

        stress_level = LABELS.get(prediction, "Unknown")
        stress_score = SCORE_MAP.get(prediction, 50)

        logger.info(f"Stress prediction for user {user.id}: {stress_level} ({stress_score})")

        return {
            "stress_level": stress_level,
            "stress_score": stress_score,
            "prediction": prediction
        }

    except Exception as e:
        logger.error(f"Stress service error: {str(e)}")
        raise


def get_stress_features_schema():
    """Return schema for stress prediction features"""
    return {
        "features": [
            {
                "key": key,
                "label": FEATURE_DESCRIPTIONS.get(key, key),
                "type": "number"
            }
            for key in FEATURE_COLUMNS
        ]
    }