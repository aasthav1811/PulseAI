"""
Sentiment Analysis Pipeline
─────────────────────────────────────────────────────────────────────────────
Uses cardiffnlp/twitter-roberta-base-sentiment-latest — a RoBERTa model
fine-tuned on ~124M tweets. Falls back to VADER for lightweight/offline use.

Problem solved: Product teams couldn't distinguish real customer pain points
from noise at scale. Rule-based tools missed sarcasm and context.

Capabilities:
  - Document-level sentiment (positive / negative / neutral)
  - Confidence scoring
  - Aspect-based sentiment extraction
  - Batch processing
"""

from __future__ import annotations

import re
import logging
from typing import List, Dict, Optional, Tuple
from functools import lru_cache
import numpy as np

logger = logging.getLogger(__name__)

# ─── Model config ─────────────────────────────────────────────────────────
MODEL_ID = "cardiffnlp/twitter-roberta-base-sentiment-latest"
FALLBACK_MODE = False  # Set True to skip transformer download

# ─── Aspect keywords for aspect-based sentiment ───────────────────────────
ASPECT_KEYWORDS = {
    "Performance": ["slow", "fast", "speed", "latency", "lag", "crash", "freeze", "load", "response"],
    "Pricing": ["price", "expensive", "cheap", "cost", "billing", "subscription", "fee", "value", "refund"],
    "Support": ["support", "help", "response", "customer service", "team", "resolve", "ticket", "agent"],
    "UI/UX": ["interface", "design", "ui", "ux", "dashboard", "navigation", "button", "layout", "click"],
    "Features": ["feature", "function", "api", "integration", "export", "report", "capability", "tool"],
    "Reliability": ["reliable", "stable", "uptime", "outage", "downtime", "broken", "bug", "error", "glitch"],
    "Onboarding": ["setup", "onboard", "doc", "tutorial", "guide", "install", "config", "start"],
    "Security": ["security", "breach", "privacy", "sso", "login", "auth", "compliance", "gdpr"],
}


class SentimentAnalyzer:
    """
    Production sentiment analysis pipeline.
    
    Tries to load the RoBERTa transformer. If torch/transformers are not
    installed or the model isn't cached, falls back to a lexicon-based scorer
    so the API still works during demo/development.
    """

    def __init__(self, use_gpu: bool = False):
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self._mode = "fallback"
        self._load_model(use_gpu)

    def _load_model(self, use_gpu: bool) -> None:
        try:
            from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
            import torch

            logger.info(f"Loading sentiment model: {MODEL_ID}")
            device = 0 if (use_gpu and torch.cuda.is_available()) else -1

            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
            self.model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID)
            self.pipeline = pipeline(
                "sentiment-analysis",
                model=self.model,
                tokenizer=self.tokenizer,
                device=device,
                truncation=True,
                max_length=512,
            )
            self._mode = "transformer"
            logger.info("Transformer model loaded successfully.")

        except Exception as e:
            logger.warning(f"Transformer load failed ({e}). Using lexicon fallback.")
            self._init_fallback()
            self._mode = "fallback"

    def _init_fallback(self) -> None:
        """VADER-based fallback sentiment scorer."""
        try:
            from nltk.sentiment.vader import SentimentIntensityAnalyzer
            import nltk
            nltk.download("vader_lexicon", quiet=True)
            self._vader = SentimentIntensityAnalyzer()
        except Exception as e:
            logger.warning(f"VADER also unavailable: {e}. Using keyword fallback.")
            self._vader = None

    def _preprocess(self, text: str) -> str:
        """Clean text for model input."""
        text = re.sub(r"http\S+|www\S+", "[URL]", text)
        text = re.sub(r"@\w+", "@user", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:512]

    def _label_map(self, raw_label: str) -> str:
        """Normalize model output labels to positive/negative/neutral."""
        label = raw_label.lower()
        if any(x in label for x in ["positive", "pos", "label_2", "2"]):
            return "positive"
        if any(x in label for x in ["negative", "neg", "label_0", "0"]):
            return "negative"
        return "neutral"

    def analyze(self, text: str) -> Dict:
        """Analyze a single text. Returns label, score, and confidence."""
        cleaned = self._preprocess(text)

        if self._mode == "transformer":
            try:
                result = self.pipeline(cleaned)[0]
                label = self._label_map(result["label"])
                score = result["score"]
                return {
                    "label": label,
                    "score": round(score, 4),
                    "confidence": round(score, 4),
                    "mode": "transformer",
                }
            except Exception as e:
                logger.error(f"Transformer inference failed: {e}")

        return self._fallback_analyze(cleaned)

    def _fallback_analyze(self, text: str) -> Dict:
        """VADER or keyword fallback."""
        if hasattr(self, "_vader") and self._vader:
            scores = self._vader.polarity_scores(text)
            compound = scores["compound"]
            if compound >= 0.05:
                label, score = "positive", 0.5 + compound / 2
            elif compound <= -0.05:
                label, score = "negative", 0.5 - compound / 2
            else:
                label, score = "neutral", 0.5 + abs(compound)
            return {"label": label, "score": round(score, 4), "confidence": round(score, 4), "mode": "vader"}

        # Pure keyword fallback
        text_lower = text.lower()
        pos_words = ["love", "great", "excellent", "amazing", "fantastic", "good", "helpful", "best", "fast"]
        neg_words = ["hate", "terrible", "awful", "slow", "broken", "crash", "bug", "scam", "worst", "bad"]
        pos = sum(w in text_lower for w in pos_words)
        neg = sum(w in text_lower for w in neg_words)
        if pos > neg:
            return {"label": "positive", "score": 0.70, "confidence": 0.70, "mode": "keyword"}
        if neg > pos:
            return {"label": "negative", "score": 0.70, "confidence": 0.70, "mode": "keyword"}
        return {"label": "neutral", "score": 0.55, "confidence": 0.55, "mode": "keyword"}

    def batch_analyze(self, texts: List[str]) -> List[Dict]:
        """Batch sentiment analysis. Uses transformer batching when available."""
        if self._mode == "transformer":
            try:
                cleaned = [self._preprocess(t) for t in texts]
                results = self.pipeline(cleaned, batch_size=16)
                return [
                    {
                        "label": self._label_map(r["label"]),
                        "score": round(r["score"], 4),
                        "confidence": round(r["score"], 4),
                        "mode": "transformer",
                    }
                    for r in results
                ]
            except Exception as e:
                logger.error(f"Batch inference failed: {e}")

        return [self._fallback_analyze(self._preprocess(t)) for t in texts]

    def analyze_aspects(self, text: str) -> Dict[str, Dict]:
        """
        Aspect-based sentiment analysis.
        
        Splits text into sentences, identifies which aspects are mentioned,
        runs sentiment on those sentences, and aggregates per aspect.
        """
        text_lower = text.lower()
        results = {}

        for aspect, keywords in ASPECT_KEYWORDS.items():
            mentioned = [kw for kw in keywords if kw in text_lower]
            if mentioned:
                # Run sentiment on the full text (for simplicity; 
                # production would use sentence-level granularity)
                sentiment = self.analyze(text)
                results[aspect] = {
                    "mentioned": True,
                    "keywords": mentioned,
                    "sentiment": sentiment["label"],
                    "score": sentiment["score"],
                }

        return results

    @property
    def mode(self) -> str:
        return self._mode


# ─── Singleton instance ────────────────────────────────────────────────────
_analyzer: Optional[SentimentAnalyzer] = None


def get_analyzer() -> SentimentAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer
