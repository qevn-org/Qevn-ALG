"""Machine Learning Lead Scoring and Hybrid Engine."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import numpy as np
import structlog

from linkedin_intelligence.models.lead import (
    CompanySignalProfile,
    Lead,
    LeadTemperature,
)

logger = structlog.get_logger(__name__)

FEATURE_NAMES = [
    "hiring_intent",
    "buying_intent",
    "technology_intent",
    "decision_maker_probability",
    "post_freshness",
    "urgency",
    "company_fit",
    "company_size_score",
    "industry_fit",
    "geographic_fit",
    "role_relevance",
    "explicit_vendor_search",
    "recommendation_request",
    "technology_problem_detected",
    "related_posts_count",
    "hiring_velocity",
    "contact_availability",
    "evidence_confidence",
]

MIN_LABELED_SAMPLES = 20
MODEL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "models"


@dataclass
class ModelMetrics:
    mode: Literal["Cold Start", "Trained"]
    status_message: str
    algorithm: str = "Hybrid Weighted Heuristic"
    training_samples: int = 0
    positive_samples: int = 0
    negative_samples: int = 0
    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    roc_auc: float | None = None
    last_trained: str | None = None
    feature_importances: dict[str, float] | None = None


def classify_lead_temperature(
    score: float,
    hot_threshold: float = 90.0,
    warm_threshold: float = 75.0,
    cool_threshold: float = 55.0,
    cold_threshold: float = 30.0,
) -> LeadTemperature:
    """Classify 0-100 score into a 6-tier lead classification."""
    s = float(score)
    if s >= hot_threshold:
        return "HOT"
    elif s >= warm_threshold:
        return "WARM"
    elif s >= cool_threshold:
        return "COOL"
    elif s >= cold_threshold:
        return "COLD"
    elif s >= 0.0:
        return "UNQUALIFIED"
    return "OTHER"


def extract_lead_features(
    lead_or_data: dict[str, Any] | Lead,
    company_profile: CompanySignalProfile | None = None,
) -> dict[str, float]:
    """Extract 18-dimensional feature vector for ML and hybrid scoring."""
    if isinstance(lead_or_data, Lead):
        data = {
            "score": lead_or_data.score,
            "hiring_intent": getattr(lead_or_data.intent, "urgency", 50.0),
            "buying_intent": 85.0 if "buy" in str(lead_or_data.intent.detected_requirement).lower() else 60.0,
            "technology_intent": 75.0,
            "decision_maker_probability": 85.0 if lead_or_data.person.is_decision_maker else 40.0,
            "post_freshness": 80.0,
            "urgency": lead_or_data.intent.urgency,
            "company_fit": 70.0,
            "company_size": lead_or_data.company.company_size,
            "industry": lead_or_data.company.industry,
            "location": lead_or_data.company.location,
            "role_relevance": 75.0,
            "signals": lead_or_data.signals,
            "contacts": lead_or_data.contacts,
            "evidence": lead_or_data.evidence,
        }
    else:
        data = dict(lead_or_data)

    # 1. Intent features
    hiring_intent = float(data.get("hiring_intent", 60.0))
    buying_intent = float(data.get("buying_intent", 50.0))
    tech_intent = float(data.get("technology_intent", 65.0))
    dm_prob = float(data.get("decision_maker_probability", 50.0))
    freshness = float(data.get("post_freshness", 75.0))
    urgency = float(data.get("urgency", 50.0))
    company_fit = float(data.get("company_fit", 60.0))

    # 2. Company size score (Mid-market & Series A/B fit best for agencies)
    comp_size = str(data.get("company_size", "")).lower()
    if "series" in comp_size or "growth" in comp_size or "50-200" in comp_size:
        company_size_score = 85.0
    elif "startup" in comp_size or "11-50" in comp_size:
        company_size_score = 75.0
    elif "enterprise" in comp_size or "1000+" in comp_size:
        company_size_score = 65.0
    else:
        company_size_score = 50.0

    # 3. Industry & Geographic fit
    industry = str(data.get("industry", "")).lower()
    if any(k in industry for k in ["tech", "software", "saas", "fintech", "ai", "health"]):
        industry_fit = 85.0
    else:
        industry_fit = 55.0

    location = str(data.get("location", "")).lower()
    if any(k in location for k in ["india", "bangalore", "mumbai", "delhi", "gurgaon", "hyderabad", "pune"]):
        geo_fit = 90.0
    elif "remote" in location or "us" in location or "uk" in location:
        geo_fit = 80.0
    else:
        geo_fit = 60.0

    role_rel = float(data.get("role_relevance", 70.0))

    # 4. Text & signal indicators
    signals_text = " ".join(str(s) for s in data.get("signals", [])).lower()
    explicit_vendor = 100.0 if any(k in signals_text for k in ["agency", "vendor", "partner", "rfp", "outsource"]) else 0.0
    rec_request = 100.0 if any(k in signals_text for k in ["recommend", "looking for", "suggestions"]) else 0.0
    tech_problem = 100.0 if any(k in signals_text for k in ["migration", "scaling", "overhaul", "replace", "legacy"]) else 0.0

    # 5. Multi-post velocity boost
    rel_posts = len(data.get("evidence", []))
    if company_profile:
        rel_posts = max(rel_posts, company_profile.post_count)
        if company_profile.hiring_velocity in ["High", "Aggressive"]:
            hiring_vel = 90.0
        elif company_profile.hiring_velocity == "Moderate":
            hiring_vel = 65.0
        else:
            hiring_vel = 40.0
    else:
        hiring_vel = min(100.0, rel_posts * 35.0)

    related_posts_score = min(100.0, rel_posts * 30.0)

    # 6. Contact & evidence confidence
    contacts = data.get("contacts", [])
    has_contact = len(contacts) > 0 or bool(data.get("primary_email"))
    contact_avail = 100.0 if has_contact else 0.0
    evidence_conf = min(100.0, 50.0 + (rel_posts * 25.0))

    return {
        "hiring_intent": round(hiring_intent, 1),
        "buying_intent": round(buying_intent, 1),
        "technology_intent": round(tech_intent, 1),
        "decision_maker_probability": round(dm_prob, 1),
        "post_freshness": round(freshness, 1),
        "urgency": round(urgency, 1),
        "company_fit": round(company_fit, 1),
        "company_size_score": round(company_size_score, 1),
        "industry_fit": round(industry_fit, 1),
        "geographic_fit": round(geo_fit, 1),
        "role_relevance": round(role_rel, 1),
        "explicit_vendor_search": round(explicit_vendor, 1),
        "recommendation_request": round(rec_request, 1),
        "technology_problem_detected": round(tech_problem, 1),
        "related_posts_count": round(related_posts_score, 1),
        "hiring_velocity": round(hiring_vel, 1),
        "contact_availability": round(contact_avail, 1),
        "evidence_confidence": round(evidence_conf, 1),
    }


def calculate_hybrid_lead_score(
    features: dict[str, float],
    custom_weights: dict[str, float] | None = None,
) -> tuple[float, LeadTemperature]:
    """Transparent mathematical hybrid score combining 18 features (0-100)."""
    weights = {
        "hiring_intent": 0.15,
        "buying_intent": 0.15,
        "technology_intent": 0.10,
        "decision_maker_probability": 0.12,
        "urgency": 0.08,
        "post_freshness": 0.07,
        "company_fit": 0.08,
        "company_size_score": 0.05,
        "industry_fit": 0.05,
        "geographic_fit": 0.03,
        "role_relevance": 0.04,
        "explicit_vendor_search": 0.03,
        "recommendation_request": 0.01,
        "technology_problem_detected": 0.01,
        "hiring_velocity": 0.03,
        "contact_availability": 0.02,
        "evidence_confidence": 0.03,
    }
    if custom_weights:
        weights.update(custom_weights)

    total_weight = sum(weights.values())
    weighted_sum = sum(features.get(k, 50.0) * w for k, w in weights.items())
    final_score = round(max(0.0, min(100.0, weighted_sum / total_weight)), 1)
    temp = classify_lead_temperature(final_score)
    return final_score, temp


class MLScoringService:
    """Manages ML model training, evaluation, persistence, and inference."""

    def __init__(self, model_dir: Path | str | None = None):
        self.model_dir = Path(model_dir) if model_dir else MODEL_DIR
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = self.model_dir / "lead_classifier.joblib"
        self.meta_path = self.model_dir / "model_meta.json"
        self._classifier: Any = None
        self._meta: ModelMetrics = self._load_meta()

    def _load_meta(self) -> ModelMetrics:
        if self.meta_path.exists():
            try:
                data = json.loads(self.meta_path.read_text(encoding="utf-8"))
                return ModelMetrics(**data)
            except Exception as err:
                logger.warning("failed_to_load_model_meta", error=str(err))

        return ModelMetrics(
            mode="Cold Start",
            status_message="Cold-start mode — insufficient historical labels",
            algorithm="Hybrid Weighted Engine",
            training_samples=0,
            positive_samples=0,
            negative_samples=0,
        )

    def get_metrics(self) -> ModelMetrics:
        return self._meta

    def train_from_dataset(self, dataset: list[dict[str, Any]]) -> ModelMetrics:
        """Train a supervised ML model if sufficient labeled outcome samples exist."""
        if len(dataset) < MIN_LABELED_SAMPLES:
            pos = sum(1 for d in dataset if d.get("label") == 1)
            neg = sum(1 for d in dataset if d.get("label") == 0)
            self._meta = ModelMetrics(
                mode="Cold Start",
                status_message=f"Cold-start mode — insufficient historical labels ({len(dataset)}/{MIN_LABELED_SAMPLES} collected)",
                algorithm="Hybrid Weighted Engine",
                training_samples=len(dataset),
                positive_samples=pos,
                negative_samples=neg,
            )
            self._save_meta()
            return self._meta

        try:
            import joblib
            from sklearn.linear_model import LogisticRegression
            from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
            from sklearn.model_selection import train_test_split
        except ImportError:
            logger.warning("scikit_learn_not_available_fallback_hybrid")
            return self._meta

        X_rows = []
        y_rows = []
        for row in dataset:
            feat = row.get("features") or {}
            vector = [float(feat.get(name, 50.0)) for name in FEATURE_NAMES]
            X_rows.append(vector)
            y_rows.append(int(row.get("label", 0)))

        X = np.array(X_rows)
        y = np.array(y_rows)

        pos_count = int(np.sum(y == 1))
        neg_count = int(np.sum(y == 0))

        if pos_count < 3 or neg_count < 3:
            self._meta = ModelMetrics(
                mode="Cold Start",
                status_message="Cold-start mode — need both positive (Won/Meeting) and negative (Lost/Disqualified) examples",
                algorithm="Hybrid Weighted Engine",
                training_samples=len(dataset),
                positive_samples=pos_count,
                negative_samples=neg_count,
            )
            self._save_meta()
            return self._meta

        # Split and train
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
        clf = LogisticRegression(max_iter=500, class_weight="balanced")
        clf.fit(X_train, y_train)

        y_pred = clf.predict(X_test)
        y_prob = clf.predict_proba(X_test)[:, 1] if len(clf.classes_) > 1 else y_pred

        acc = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred, zero_division=0))
        rec = float(recall_score(y_test, y_pred, zero_division=0))
        try:
            auc = float(roc_auc_score(y_test, y_prob))
        except Exception:
            auc = 0.5

        # Feature coefficients as importances
        coefs = clf.coef_[0]
        feat_importances = {name: round(float(c), 3) for name, c in zip(FEATURE_NAMES, coefs)}

        # Persist model
        joblib.dump(clf, self.model_path)
        self._classifier = clf

        now_str = datetime.now(timezone.utc).isoformat()
        self._meta = ModelMetrics(
            mode="Trained",
            status_message=f"Trained supervised model on {len(dataset)} historical outcomes",
            algorithm="Logistic Regression",
            training_samples=len(dataset),
            positive_samples=pos_count,
            negative_samples=neg_count,
            accuracy=round(acc, 3),
            precision=round(prec, 3),
            recall=round(rec, 3),
            roc_auc=round(auc, 3),
            last_trained=now_str,
            feature_importances=feat_importances,
        )
        self._save_meta()
        logger.info("ml_model_trained_successfully", accuracy=acc, samples=len(dataset))
        return self._meta

    def _save_meta(self) -> None:
        try:
            data = {
                "mode": self._meta.mode,
                "status_message": self._meta.status_message,
                "algorithm": self._meta.algorithm,
                "training_samples": self._meta.training_samples,
                "positive_samples": self._meta.positive_samples,
                "negative_samples": self._meta.negative_samples,
                "accuracy": self._meta.accuracy,
                "precision": self._meta.precision,
                "recall": self._meta.recall,
                "roc_auc": self._meta.roc_auc,
                "last_trained": self._meta.last_trained,
                "feature_importances": self._meta.feature_importances,
            }
            self.meta_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as err:
            logger.warning("failed_to_save_model_meta", error=str(err))

    def predict_lead(self, features: dict[str, float]) -> tuple[float, LeadTemperature, str]:
        """Predict lead score using trained ML model if available, else transparent hybrid scoring."""
        if self._meta.mode == "Trained" and self.model_path.exists():
            try:
                if self._classifier is None:
                    import joblib
                    self._classifier = joblib.load(self.model_path)

                vector = np.array([[float(features.get(name, 50.0)) for name in FEATURE_NAMES]])
                prob = float(self._classifier.predict_proba(vector)[0][1])
                score = round(prob * 100.0, 1)
                temp = classify_lead_temperature(score)
                return score, temp, "Supervised ML (Logistic Regression)"
            except Exception as err:
                logger.error("ml_inference_failed_falling_back_to_hybrid", error=str(err))

        score, temp = calculate_hybrid_lead_score(features)
        return score, temp, "Hybrid Heuristic (Cold-start mode)"


_scoring_service: MLScoringService | None = None


def get_ml_scoring_service() -> MLScoringService:
    global _scoring_service
    if _scoring_service is None:
        _scoring_service = MLScoringService()
    return _scoring_service
