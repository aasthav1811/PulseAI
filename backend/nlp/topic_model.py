"""
Topic Modeling Engine
─────────────────────────────────────────────────────────────────────────────
Problem: Product teams were reading thousands of reviews manually to find
recurring themes. They missed emerging issues and couldn't prioritize roadmap
decisions based on customer frequency.

Solution: Automated topic discovery using NMF (Non-negative Matrix 
Factorization) — fast, interpretable, and more coherent than LDA for short
texts like reviews and tweets.

Output: Named topic clusters with example posts, keyword weights, and
sentiment distribution per cluster.
"""

from __future__ import annotations

import re
import logging
from typing import List, Dict, Tuple, Optional
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF, LatentDirichletAllocation
from sklearn.preprocessing import normalize

logger = logging.getLogger(__name__)

# ─── Stop words (reduced to keep domain-specific terms) ──────────────────────
CUSTOM_STOP_WORDS = [
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "this", "that",
    "these", "those", "i", "we", "you", "they", "he", "she", "it",
    "my", "our", "your", "their", "its", "me", "us", "them", "him", "her",
    "very", "really", "just", "also", "even", "still",
    "when", "where", "how", "what", "which", "who", "why",
    "so", "as", "if", "up", "out", "about",
]

# ─── Human-readable topic name mapping ────────────────────────────────────
TOPIC_NAME_MAP = {
    frozenset(["performance", "speed", "slow", "load", "latency", "fast", "crash"]): "Performance & Speed",
    frozenset(["price", "billing", "cost", "expensive", "subscription", "fee", "refund"]): "Pricing & Billing",
    frozenset(["support", "team", "response", "customer", "service", "help", "ticket"]): "Customer Support",
    frozenset(["ui", "interface", "design", "dashboard", "navigation", "layout", "ux"]): "UI & Design",
    frozenset(["feature", "api", "integration", "export", "report", "function", "capability"]): "Features & Integrations",
    frozenset(["setup", "onboard", "doc", "documentation", "guide", "install", "config"]): "Onboarding & Docs",
    frozenset(["data", "accuracy", "model", "analysis", "insight", "quality", "reliable"]): "Data Quality & Accuracy",
    frozenset(["security", "privacy", "breach", "auth", "compliance", "sso", "gdpr"]): "Security & Compliance",
}


def _clean_text(text: str) -> str:
    """Normalize text for vectorization."""
    text = text.lower()
    text = re.sub(r"http\S+|www\S+|@\w+|#\w+", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _infer_topic_name(keywords: List[str]) -> str:
    """Heuristically name a topic from its top keywords."""
    keyword_set = set(keywords[:8])
    best_match = None
    best_overlap = 0

    for key_words, name in TOPIC_NAME_MAP.items():
        overlap = len(keyword_set & key_words)
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = name

    if best_match and best_overlap >= 1:
        return best_match

    # Fallback: capitalize the top keyword
    return keywords[0].replace("_", " ").title() + " Issues" if keywords else "General Feedback"


class TopicModeler:
    """
    NMF-based topic modeling optimized for short product review texts.
    
    Why NMF over LDA?
    - LDA assumes bag-of-words with Dirichlet priors — good for long documents.
    - NMF with TF-IDF produces more coherent, interpretable topics for short texts.
    - Faster training, better topic separation for review-length inputs.
    """

    def __init__(self, n_topics: int = 8, max_features: int = 3000):
        self.n_topics = n_topics
        self.max_features = max_features
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.model: Optional[NMF] = None
        self.feature_names: List[str] = []
        self.topic_names: List[str] = []
        self.is_fitted = False

    def fit(self, texts: List[str]) -> "TopicModeler":
        """Fit the topic model on a corpus of texts."""
        cleaned = [_clean_text(t) for t in texts]
        
        # Filter out empty strings
        cleaned = [t for t in cleaned if t.strip()]
        if len(cleaned) < 10:
            logger.warning(f"Too few valid documents ({len(cleaned)}). Using simple clustering.")
            self._create_fallback_topics(texts)
            return self

        self.vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            stop_words=CUSTOM_STOP_WORDS,
            ngram_range=(1, 2),
            min_df=1,  # Lower threshold - accept terms in at least 1 doc
            max_df=0.95,  # Higher threshold - keep more terms
            sublinear_tf=True,
        )
        
        try:
            tfidf_matrix = self.vectorizer.fit_transform(cleaned)
            self.feature_names = self.vectorizer.get_feature_names_out().tolist()
            
            # Check if matrix is valid
            if tfidf_matrix.nnz == 0 or len(self.feature_names) < self.n_topics:
                logger.warning("TF-IDF matrix is too sparse. Using fallback topics.")
                self._create_fallback_topics(texts)
                return self

            self.model = NMF(
                n_components=self.n_topics,
                init="nndsvd",  # Changed from nndsvda - more robust
                random_state=42,
                max_iter=300,
                alpha_W=0.0,  # Reduced regularization
                alpha_H=0.0,
                l1_ratio=0.0,
            )
            self.model.fit(tfidf_matrix)
            
            self.topic_names = [
                _infer_topic_name(self._get_topic_keywords(i, top_n=10))
                for i in range(self.n_topics)
            ]
            self.is_fitted = True
            logger.info(f"Topic model fitted. Topics: {self.topic_names}")
            
        except Exception as e:
            logger.error(f"Topic model fitting failed: {e}. Using fallback.")
            self._create_fallback_topics(texts)
            
        return self

    def _create_fallback_topics(self, texts: List[str]) -> None:
        """Create a simple fallback topic model when NMF fails."""
        logger.warning("Creating fallback topic model with keyword-based clustering")
        self.n_topics = 5  # Reduced number of topics for fallback
        self.topic_names = [
            "Performance & Speed",
            "Customer Support",  
            "Pricing & Billing",
            "Features & UI",
            "General Feedback"
        ]
        self.is_fitted = True
        self._fallback_mode = True
        # Store texts for fallback classification
        self._fallback_texts = texts[:100]  # Keep sample for reference

    def _get_topic_keywords(self, topic_idx: int, top_n: int = 12) -> List[str]:
        """Return top keywords for a topic."""
        if not hasattr(self, 'model') or self.model is None:
            # Fallback keywords
            fallback_keywords = {
                0: ['slow', 'fast', 'speed', 'performance', 'loading', 'lag', 'crash'],
                1: ['support', 'help', 'response', 'team', 'customer', 'service'],
                2: ['price', 'pricing', 'cost', 'expensive', 'billing', 'subscription'],
                3: ['feature', 'ui', 'interface', 'design', 'dashboard', 'ux'],
                4: ['good', 'better', 'platform', 'recommend', 'experience', 'overall']
            }
            return fallback_keywords.get(topic_idx, ['general', 'feedback'])[:top_n]
        
        topic_vector = self.model.components_[topic_idx]
        top_indices = topic_vector.argsort()[::-1][:top_n]
        return [self.feature_names[i] for i in top_indices]

    def transform(self, texts: List[str]) -> np.ndarray:
        """Assign topic distributions to texts."""
        if hasattr(self, '_fallback_mode') and self._fallback_mode:
            # Simple keyword-based assignment for fallback
            n = len(texts)
            distributions = np.zeros((n, self.n_topics))
            
            keywords = {
                0: ['slow', 'speed', 'performance', 'loading', 'fast', 'lag'],
                1: ['support', 'help', 'response', 'team', 'customer'],
                2: ['price', 'pricing', 'cost', 'expensive', 'billing'],
                3: ['feature', 'ui', 'interface', 'design', 'dashboard'],
                4: []  # default
            }
            
            for i, text in enumerate(texts):
                text_lower = text.lower()
                scores = np.zeros(self.n_topics)
                
                for topic_id, words in keywords.items():
                    scores[topic_id] = sum(1 for w in words if w in text_lower)
                
                # Assign to topic with most keyword matches, or default to last topic
                if scores.sum() > 0:
                    scores = scores / scores.sum()
                else:
                    scores[-1] = 1.0
                    
                distributions[i] = scores
            
            return distributions
        
        # Normal NMF transform
        cleaned = [_clean_text(t) for t in texts]
        tfidf = self.vectorizer.transform(cleaned)
        return self.model.transform(tfidf)

    def get_document_topics(self, texts: List[str]) -> List[int]:
        """Return the dominant topic index for each text."""
        distributions = self.transform(texts)
        return distributions.argmax(axis=1).tolist()

    def get_topics_summary(
        self,
        texts: List[str],
        sentiments: Optional[List[str]] = None,
        top_n_keywords: int = 10,
    ) -> List[Dict]:
        """
        Full topic summary with keywords, example posts, sentiment breakdown,
        and cluster size — ready for frontend visualization.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before calling get_topics_summary.")

        topic_assignments = self.get_document_topics(texts)
        
        # Group texts by topic
        topic_buckets: Dict[int, List[int]] = {i: [] for i in range(self.n_topics)}
        for idx, topic in enumerate(topic_assignments):
            topic_buckets[topic].append(idx)

        summary = []
        for topic_idx in range(self.n_topics):
            indices = topic_buckets[topic_idx]
            if not indices:
                continue

            keywords = self._get_topic_keywords(topic_idx, top_n=top_n_keywords)
            examples = [texts[i] for i in indices[:3]]  # Top 3 representative posts

            # Sentiment breakdown if available
            sentiment_dist = {"positive": 0, "negative": 0, "neutral": 0, "crisis": 0}
            if sentiments:
                for i in indices:
                    lbl = sentiments[i] if i < len(sentiments) else "neutral"
                    sentiment_dist[lbl] = sentiment_dist.get(lbl, 0) + 1

            total = len(indices)
            dominant_sentiment = max(sentiment_dist, key=sentiment_dist.get) if sentiments else "neutral"
            
            # Keyword weights for visualization (bubble size / word cloud)
            kw_weights = {}
            if hasattr(self, 'model') and self.model is not None:
                topic_vector = self.model.components_[topic_idx]
                for kw in keywords:
                    if kw in self.feature_names:
                        feat_idx = self.feature_names.index(kw)
                        kw_weights[kw] = float(round(topic_vector[feat_idx], 4))
            else:
                # Fallback: assign uniform weights
                for i, kw in enumerate(keywords):
                    kw_weights[kw] = float(round(1.0 - (i * 0.1), 2))

            summary.append({
                "id": topic_idx,
                "name": self.topic_names[topic_idx],
                "keywords": keywords,
                "keyword_weights": kw_weights,
                "post_count": total,
                "percentage": round(100 * total / max(len(texts), 1), 1),
                "dominant_sentiment": dominant_sentiment,
                "sentiment_distribution": sentiment_dist,
                "examples": examples,
            })

        return sorted(summary, key=lambda x: x["post_count"], reverse=True)


# ─── Singleton ────────────────────────────────────────────────────────────
_modeler: Optional[TopicModeler] = None


def get_modeler(n_topics: int = 8) -> TopicModeler:
    global _modeler
    if _modeler is None:
        _modeler = TopicModeler(n_topics=n_topics)
    return _modeler
