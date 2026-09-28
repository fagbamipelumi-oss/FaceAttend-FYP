"""Face-verification evaluation metrics.

Distances are dlib/face_recognition Euclidean distances between 128-d
embeddings. A pair is classified as a predicted match when distance <
threshold. "Genuine" pairs are two photos of the same enrolled person;
"impostor" pairs are two photos of different people (or an enrolled person
vs. someone never enrolled).

Formulas:
    Accuracy  = (TP + TN) / (TP + TN + FP + FN)
    Precision = TP / (TP + FP)
    Recall    = TP / (TP + FN)
    F1        = 2 * (Precision * Recall) / (Precision + Recall)
    FAR (False Acceptance Rate) = FP / (FP + TN)   -- impostors wrongly accepted
    FRR (False Rejection Rate)  = FN / (TP + FN)   -- genuine users wrongly rejected
    EER (Equal Error Rate) = the error rate at the threshold where FAR == FRR
    ROC-AUC = area under the ROC curve (True Positive Rate vs. False Positive Rate)
      across all thresholds, via sklearn.
"""

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import auc, roc_curve


@dataclass
class ConfusionCounts:
    tp: int
    fn: int
    fp: int
    tn: int


def confusion_counts(genuine: list[float], impostor: list[float], threshold: float) -> ConfusionCounts:
    tp = sum(1 for d in genuine if d < threshold)
    fn = len(genuine) - tp
    fp = sum(1 for d in impostor if d < threshold)
    tn = len(impostor) - fp
    return ConfusionCounts(tp=tp, fn=fn, fp=fp, tn=tn)


def accuracy_precision_recall_f1(genuine: list[float], impostor: list[float], threshold: float) -> dict:
    c = confusion_counts(genuine, impostor, threshold)
    total = c.tp + c.tn + c.fp + c.fn
    accuracy = (c.tp + c.tn) / total if total else 0.0
    precision = c.tp / (c.tp + c.fp) if (c.tp + c.fp) else 0.0
    recall = c.tp / (c.tp + c.fn) if (c.tp + c.fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": c.tp,
        "fn": c.fn,
        "fp": c.fp,
        "tn": c.tn,
    }


def far_frr(genuine: list[float], impostor: list[float], threshold: float) -> tuple[float, float]:
    c = confusion_counts(genuine, impostor, threshold)
    far = c.fp / (c.fp + c.tn) if (c.fp + c.tn) else 0.0
    frr = c.fn / (c.tp + c.fn) if (c.tp + c.fn) else 0.0
    return far, frr


def equal_error_rate(genuine: list[float], impostor: list[float]) -> dict:
    """Scan every candidate threshold (every observed distance) and return
    the one where FAR and FRR are closest, along with their average as the
    reported EER.
    """
    candidates = sorted(set(genuine) | set(impostor))
    best_threshold = None
    best_gap = None
    best_rate = None
    for t in candidates:
        far, frr = far_frr(genuine, impostor, t)
        gap = abs(far - frr)
        if best_gap is None or gap < best_gap:
            best_gap = gap
            best_threshold = t
            best_rate = (far + frr) / 2
    return {"threshold": best_threshold, "eer": best_rate}


def roc_auc(genuine: list[float], impostor: list[float]) -> dict:
    y_true = [1] * len(genuine) + [0] * len(impostor)
    # Lower distance = more similar, so negate distance to use as a score
    # where higher = more likely genuine, as roc_curve expects.
    scores = [-d for d in genuine] + [-d for d in impostor]
    fpr, tpr, thresholds = roc_curve(y_true, scores)
    return {
        "fpr": fpr.tolist(),
        "tpr": tpr.tolist(),
        "thresholds": (-thresholds).tolist(),
        "auc": float(auc(fpr, tpr)),
    }
