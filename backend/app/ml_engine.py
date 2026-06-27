"""
ML Layer for anomaly detection using Isolation Forest.
"""
import logging
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
import os
import hashlib
from datetime import datetime, timezone
from typing import List, Optional

from app.models import FeatureVector
from app.config import settings

logger = logging.getLogger(__name__)

class MLEngine:
    """Anomaly detection using Isolation Forest."""
    
    def __init__(self):
        self.model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
        self.is_trained = False
        self.training_data = []
        self.min_training_samples = 100
        self.model_path = os.path.join(os.path.dirname(settings.DATABASE_PATH), "anomaly_model.pkl")
        self._load_model()

    def _extract_features(self, fv: FeatureVector) -> np.ndarray:
        """Flatten feature vector into a numeric array for ML."""
        v = fv.vibration
        e = fv.electrical
        return np.array([
            v.rms_overall,
            v.rms_x, v.rms_y, v.rms_z,
            v.peak_x, v.peak_y, v.peak_z,
            v.kurtosis_x, v.kurtosis_y, v.kurtosis_z,
            v.crest_factor,
            e.current,
            e.power_factor,
            e.efficiency,
            fv.temperature
        ]).reshape(1, -1)

    def predict(self, fv: FeatureVector) -> float:
        """
        Return an anomaly score 0-1.
        1.0 means highly anomalous, 0.0 means normal.
        """
        if not self.is_trained:
            # Collect data for training if not enough samples
            feat = self._extract_features(fv)
            self.training_data.append(feat.flatten())
            
            if len(self.training_data) >= self.min_training_samples:
                self.train()
                
            return 0.0 # Default to normal during training phase
            
        try:
            feat = self._extract_features(fv)
            # decision_function returns negative values for anomalies, positive for normal
            # We transform it to a 0-1 scale where 1 is anomaly
            score = self.model.decision_function(feat)[0]
            
            # Map score (roughly -0.5 to 0.5) to 0-1
            # Higher score = more normal. Lower score = more anomalous.
            normalized_anomaly = 1.0 - (score + 0.5) 
            return float(max(0, min(1.0, normalized_anomaly)))
        except Exception as e:
            logger.error(f"Error during ML prediction: {e}")
            return 0.0

    def train(self):
        """Train the model on collected data."""
        if len(self.training_data) < 20: # Sanity check
            return
            
        logger.info(f"Training anomaly detection model with {len(self.training_data)} samples...")
        X = np.array(self.training_data)
        self.model.fit(X)
        self.is_trained = True
        self._save_model()
        # Keep some data for future incremental training or clear it
        self.training_data = self.training_data[-500:] # Keep last 500
        logger.info("Model training complete.")

    def _save_model(self):
        try:
            joblib.dump(self.model, self.model_path)
            # Compute and log hash of saved model
            with open(self.model_path, 'rb') as f:
                model_hash = hashlib.sha256(f.read()).hexdigest()
            logger.info(f"Model saved. SHA256: {model_hash}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")

    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                # Log hash before loading
                with open(self.model_path, 'rb') as f:
                    model_hash = hashlib.sha256(f.read()).hexdigest()
                logger.info(f"Loading model with SHA256: {model_hash}")
                
                self.model = joblib.load(self.model_path)
                self.is_trained = True
                logger.info("Loaded anomaly detection model from disk.")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")

# Singleton
ml_engine = MLEngine()
