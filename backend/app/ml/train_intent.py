"""
Training script for Intent Classifier.

This script loads the intent dataset, trains the classifier, evaluates performance,
and saves the trained model.

Usage:
    python -m app.ml.train_intent
"""

import csv
import logging
import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
from sklearn.model_selection import train_test_split

# Add backend directory to path for imports
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.ml.intent_classifier import IntentClassifier, INTENT_CLASSES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
DATASET_PATH = Path(__file__).parent / "data" / "intent_dataset.csv"
MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "intent_classifier.pkl"


def load_dataset(dataset_path: Path) -> Tuple[List[str], List[str]]:
    """
    Load the intent dataset from CSV file.
    
    Args:
        dataset_path: Path to the CSV dataset file
    
    Returns:
        tuple: (texts, labels) - Lists of text strings and corresponding labels
    
    Raises:
        FileNotFoundError: If dataset file doesn't exist
        ValueError: If dataset is empty or malformed
    """
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")
    
    texts = []
    labels = []
    
    logger.info(f"Loading dataset from {dataset_path}")
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (row 1 is header)
            text = row.get('text', '').strip()
            label = row.get('label', '').strip()
            
            if not text:
                logger.warning(f"Row {row_num}: Empty text, skipping")
                continue
            
            if not label:
                logger.warning(f"Row {row_num}: Empty label, skipping")
                continue
            
            if label not in INTENT_CLASSES:
                logger.warning(f"Row {row_num}: Invalid label '{label}', skipping")
                continue
            
            texts.append(text)
            labels.append(label)
    
    if not texts:
        raise ValueError("Dataset is empty or contains no valid rows")
    
    logger.info(f"Loaded {len(texts)} examples from dataset")
    
    # Log class distribution
    from collections import Counter
    label_counts = Counter(labels)
    logger.info("Class distribution:")
    for label in INTENT_CLASSES:
        count = label_counts.get(label, 0)
        logger.info(f"  {label}: {count}")
    
    return texts, labels


def split_train_test(texts: List[str], labels: List[str], test_size: float = 0.2, random_seed: int = 42) -> Tuple[List[str], List[str], List[str], List[str]]:
    """
    Split dataset into training and testing sets.
    
    Args:
        texts: List of text strings
        labels: List of labels
        test_size: Proportion of data to use for testing (default: 0.2)
        random_seed: Random seed for reproducibility
    
    Returns:
        tuple: (train_texts, train_labels, test_texts, test_labels)
    """
    train_texts, test_texts, train_labels, test_labels = train_test_split(
        texts, labels,
        test_size=test_size,
        random_state=random_seed,
        stratify=labels  # Maintain class distribution
    )
    
    logger.info(f"Split dataset: {len(train_texts)} train, {len(test_texts)} test")
    
    return train_texts, train_labels, test_texts, test_labels


def print_confusion_matrix(y_true: List[str], y_pred: List[str], classes: List[str]):
    """
    Print a formatted confusion matrix.
    
    Args:
        y_true: True labels
        y_pred: Predicted labels
        classes: List of class names
    """
    cm = confusion_matrix(y_true, y_pred, labels=classes)
    
    print("\n" + "=" * 80)
    print("CONFUSION MATRIX")
    print("=" * 80)
    
    # Print header
    header = f"{'Actual \\ Predicted':<20}"
    for cls in classes:
        header += f"{cls[:10]:>12}"
    print(header)
    print("-" * 80)
    
    # Print rows
    for i, cls in enumerate(classes):
        row = f"{cls[:18]:<20}"
        for j in range(len(classes)):
            row += f"{cm[i, j]:>12}"
        print(row)
    
    print("=" * 80)
    print()


def evaluate_classifier(classifier: IntentClassifier, test_texts: List[str], test_labels: List[str]) -> dict:
    """
    Evaluate the classifier on test data.
    
    Args:
        classifier: Trained IntentClassifier instance
        test_texts: Test text strings
        test_labels: True labels for test texts
    
    Returns:
        dict: Evaluation metrics
    """
    logger.info("Evaluating classifier on test set...")
    
    predictions = []
    confidences = []
    
    for text in test_texts:
        result = classifier.predict(text)
        predictions.append(result['intent'])
        confidences.append(result['confidence'])
    
    # Calculate accuracy
    accuracy = accuracy_score(test_labels, predictions)
    
    # Calculate per-class metrics
    report = classification_report(test_labels, predictions, labels=INTENT_CLASSES, output_dict=True)
    
    # Print results
    print("\n" + "=" * 80)
    print("EVALUATION RESULTS")
    print("=" * 80)
    print(f"\nAccuracy: {accuracy:.4f} ({accuracy * 100:.2f}%)")
    print(f"\nAverage Confidence: {np.mean(confidences):.4f}")
    print(f"Min Confidence: {np.min(confidences):.4f}")
    print(f"Max Confidence: {np.max(confidences):.4f}")
    
    print("\n" + "-" * 80)
    print("PER-CLASS METRICS")
    print("-" * 80)
    print(f"{'Class':<20} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<12}")
    print("-" * 80)
    
    for cls in INTENT_CLASSES:
        if cls in report:
            metrics = report[cls]
            print(f"{cls:<20} {metrics['precision']:<12.4f} {metrics['recall']:<12.4f} "
                  f"{metrics['f1-score']:<12.4f} {int(metrics['support']):<12}")
    
    # Print macro and weighted averages
    print("-" * 80)
    print(f"{'macro avg':<20} {report['macro avg']['precision']:<12.4f} "
          f"{report['macro avg']['recall']:<12.4f} {report['macro avg']['f1-score']:<12.4f} "
          f"{int(report['macro avg']['support']):<12}")
    print(f"{'weighted avg':<20} {report['weighted avg']['precision']:<12.4f} "
          f"{report['weighted avg']['recall']:<12.4f} {report['weighted avg']['f1-score']:<12.4f} "
          f"{int(report['weighted avg']['support']):<12}")
    
    # Print confusion matrix
    print_confusion_matrix(test_labels, predictions, INTENT_CLASSES)
    
    return {
        'accuracy': accuracy,
        'average_confidence': float(np.mean(confidences)),
        'classification_report': report,
        'predictions': predictions,
        'confidences': confidences
    }


def train():
    """
    Main training function.
    
    Loads dataset, trains classifier, evaluates performance, and saves model.
    """
    try:
        # Load dataset
        texts, labels = load_dataset(DATASET_PATH)
        
        # Split into train/test
        train_texts, train_labels, test_texts, test_labels = split_train_test(texts, labels)
        
        # Initialize classifier
        logger.info("Initializing intent classifier...")
        classifier = IntentClassifier(model_path=MODEL_PATH)
        
        # Train classifier
        logger.info("Training classifier...")
        train_result = classifier.train(train_texts, train_labels)
        
        if train_result['status'] != 'success':
            logger.error(f"Training failed: {train_result['message']}")
            return False
        
        logger.info(f"Training completed: {train_result['message']}")
        
        # Evaluate on test set
        evaluation = evaluate_classifier(classifier, test_texts, test_labels)
        
        # Save model
        logger.info(f"Saving model to {MODEL_PATH}")
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        save_result = classifier.save_model()
        
        if save_result['status'] != 'success':
            logger.error(f"Failed to save model: {save_result['message']}")
            return False
        
        logger.info(f"Model saved successfully to {save_result['path']}")
        
        print("\n" + "=" * 80)
        print("TRAINING COMPLETE")
        print("=" * 80)
        print(f"Model saved to: {save_result['path']}")
        print(f"Test Accuracy: {evaluation['accuracy']:.4f} ({evaluation['accuracy'] * 100:.2f}%)")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"Training failed with error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    """
    Training is explicit - only runs when script is executed directly.
    """
    success = train()
    sys.exit(0 if success else 1)

