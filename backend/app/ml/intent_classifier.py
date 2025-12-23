"""
Intent Classifier using TF-IDF and Logistic Regression.

This module provides a machine learning-based intent classifier that uses
TF-IDF vectorization and Logistic Regression to classify text into intent categories:
- fire
- medical
- crime
- accident
- natural_disaster
- other

Naming Philosophy:
- We use "external_model_api" conceptually instead of "ml_model" to emphasize
  that this classifier is a local model, but the concept applies: we're using
  a model (local or external) for classification as part of signal processing.
- The intent classifier is a local ML model used in our signal processing pipeline,
  not a decision-making component. Decisions are made by the decision engine.

The classifier can be trained on labeled data and saved/loaded for reuse.
"""

import os
import pickle
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)

# Valid intent classes
INTENT_CLASSES = ["fire", "medical", "crime", "accident", "natural_disaster", "other"]

# Default model save path
DEFAULT_MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "intent_classifier.pkl"


class IntentClassifier:
    """
    Intent classifier using TF-IDF vectorization and Logistic Regression.
    
    This classifier can be trained on labeled text data and used to predict
    intent categories with confidence scores.
    """
    
    def __init__(self, model_path: Optional[Path] = None):
        """
        Initialize the intent classifier.
        
        Args:
            model_path: Optional path to save/load the model. Defaults to
                       backend/models/intent_classifier.pkl
        """
        self.model_path = model_path or DEFAULT_MODEL_PATH
        self.pipeline: Optional[Pipeline] = None
        self.label_encoder: Optional[LabelEncoder] = None
        self.is_trained = False
        
    def train(self, texts: List[str], labels: List[str]) -> Dict[str, any]:
        """
        Train the intent classifier on labeled text data.
        
        Args:
            texts: List of text strings to train on
            labels: List of intent labels corresponding to texts.
                    Must be one of: fire, medical, crime, accident, natural_disaster, other
        
        Returns:
            dict: Training results with keys:
                - "status": str - "success" or "error"
                - "n_samples": int - Number of training samples
                - "n_classes": int - Number of unique classes
                - "classes": List[str] - List of classes found in training data
                - "message": str - Status message
        
        Raises:
            ValueError: If texts and labels have different lengths or invalid labels
        """
        if len(texts) != len(labels):
            raise ValueError(f"Texts and labels must have the same length. Got {len(texts)} texts and {len(labels)} labels")
        
        if not texts:
            raise ValueError("Cannot train on empty dataset")
        
        # Validate labels
        invalid_labels = [label for label in labels if label not in INTENT_CLASSES]
        if invalid_labels:
            raise ValueError(f"Invalid labels found: {set(invalid_labels)}. Valid labels are: {INTENT_CLASSES}")
        
        try:
            # Initialize label encoder
            self.label_encoder = LabelEncoder()
            encoded_labels = self.label_encoder.fit_transform(labels)
            
            # Create pipeline with TF-IDF vectorizer and Logistic Regression
            self.pipeline = Pipeline([
                ('tfidf', TfidfVectorizer(
                    max_features=5000,
                    ngram_range=(1, 2),  # Unigrams and bigrams
                    min_df=2,  # Minimum document frequency
                    max_df=0.95,  # Maximum document frequency
                    lowercase=True,
                    stop_words='english'  # Remove English stop words
                )),
                ('classifier', LogisticRegression(
                    max_iter=1000,
                    random_state=42,
                    multi_class='multinomial',  # For multi-class classification
                    solver='lbfgs'  # Good for small datasets
                ))
            ])
            
            # Train the pipeline
            logger.info(f"Training intent classifier on {len(texts)} samples...")
            self.pipeline.fit(texts, encoded_labels)
            self.is_trained = True
            
            # Get unique classes
            unique_classes = sorted(set(labels))
            
            logger.info(f"Training completed. Classes: {unique_classes}")
            
            return {
                "status": "success",
                "n_samples": len(texts),
                "n_classes": len(unique_classes),
                "classes": unique_classes,
                "message": f"Successfully trained on {len(texts)} samples with {len(unique_classes)} classes"
            }
            
        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            self.is_trained = False
            return {
                "status": "error",
                "n_samples": len(texts),
                "n_classes": 0,
                "classes": [],
                "message": f"Training failed: {str(e)}"
            }
    
    def predict(self, text: str) -> Dict[str, any]:
        """
        Predict intent for a given text.
        
        Args:
            text: Input text string to classify
        
        Returns:
            dict: Prediction results with keys:
                - "intent": str - Predicted intent class
                - "confidence": float - Confidence score (0.0 to 1.0)
                - "probabilities": dict - Probability scores for all classes
        
        Raises:
            RuntimeError: If model is not trained
        """
        if not self.is_trained or self.pipeline is None or self.label_encoder is None:
            raise RuntimeError("Model must be trained before making predictions. Call train() first or load_model()")
        
        if not text or not text.strip():
            # Return default prediction for empty text
            return {
                "intent": "other",
                "confidence": 0.0,
                "probabilities": {cls: 0.0 for cls in INTENT_CLASSES}
            }
        
        try:
            # Get prediction probabilities
            encoded_probs = self.pipeline.predict_proba([text])[0]
            
            # Map encoded labels back to original class names
            class_names = self.label_encoder.classes_
            probabilities = {
                class_name: float(prob) 
                for class_name, prob in zip(class_names, encoded_probs)
            }
            
            # Get predicted class (highest probability)
            predicted_encoded = self.pipeline.predict([text])[0]
            predicted_intent = self.label_encoder.inverse_transform([predicted_encoded])[0]
            
            # Get confidence (probability of predicted class)
            confidence = float(encoded_probs[predicted_encoded])
            
            return {
                "intent": predicted_intent,
                "confidence": confidence,
                "probabilities": probabilities
            }
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            # Return safe default on error
            return {
                "intent": "other",
                "confidence": 0.0,
                "probabilities": {cls: 0.0 for cls in INTENT_CLASSES}
            }
    
    def save_model(self, model_path: Optional[Path] = None) -> Dict[str, any]:
        """
        Save the trained model to disk.
        
        Args:
            model_path: Optional path to save the model. If not provided, uses
                       the path specified during initialization.
        
        Returns:
            dict: Save results with keys:
                - "status": str - "success" or "error"
                - "path": str - Path where model was saved
                - "message": str - Status message
        
        Raises:
            RuntimeError: If model is not trained
        """
        if not self.is_trained or self.pipeline is None or self.label_encoder is None:
            raise RuntimeError("Model must be trained before saving. Call train() first")
        
        save_path = model_path or self.model_path
        
        try:
            # Create directory if it doesn't exist
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save both pipeline and label encoder
            model_data = {
                'pipeline': self.pipeline,
                'label_encoder': self.label_encoder,
                'is_trained': self.is_trained
            }
            
            with open(save_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Model saved to {save_path}")
            
            return {
                "status": "success",
                "path": str(save_path),
                "message": f"Model successfully saved to {save_path}"
            }
            
        except Exception as e:
            logger.error(f"Failed to save model: {e}", exc_info=True)
            return {
                "status": "error",
                "path": str(save_path),
                "message": f"Failed to save model: {str(e)}"
            }
    
    def load_model(self, model_path: Optional[Path] = None) -> Dict[str, any]:
        """
        Load a trained model from disk.
        
        Args:
            model_path: Optional path to load the model from. If not provided, uses
                       the path specified during initialization.
        
        Returns:
            dict: Load results with keys:
                - "status": str - "success" or "error"
                - "path": str - Path where model was loaded from
                - "message": str - Status message
        
        Raises:
            FileNotFoundError: If model file doesn't exist
        """
        load_path = model_path or self.model_path
        
        if not load_path.exists():
            raise FileNotFoundError(f"Model file not found: {load_path}")
        
        try:
            with open(load_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.pipeline = model_data['pipeline']
            self.label_encoder = model_data['label_encoder']
            self.is_trained = model_data.get('is_trained', True)
            
            logger.info(f"Model loaded from {load_path}")
            
            return {
                "status": "success",
                "path": str(load_path),
                "message": f"Model successfully loaded from {load_path}"
            }
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}", exc_info=True)
            self.is_trained = False
            raise RuntimeError(f"Failed to load model: {str(e)}")


# Convenience functions for easy usage
def create_classifier(model_path: Optional[Path] = None) -> IntentClassifier:
    """
    Create a new IntentClassifier instance.
    
    Args:
        model_path: Optional path to save/load the model
    
    Returns:
        IntentClassifier: New classifier instance
    """
    return IntentClassifier(model_path=model_path)


def load_classifier(model_path: Optional[Path] = None) -> IntentClassifier:
    """
    Create and load a trained IntentClassifier from disk.
    
    Args:
        model_path: Optional path to load the model from
    
    Returns:
        IntentClassifier: Loaded classifier instance
    
    Raises:
        FileNotFoundError: If model file doesn't exist
        RuntimeError: If model loading fails
    """
    classifier = IntentClassifier(model_path=model_path)
    classifier.load_model()
    return classifier

