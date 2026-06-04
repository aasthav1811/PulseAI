"""
Crisis Detection Engine
─────────────────────────────────────────────────────────────────────────────
Problem: By the time a brand crisis appeared in weekly reports, it had already
gone viral. Teams needed sub-hour detection of emerging PR disasters.

Solution: Multi-signal crisis scoring that combines:
  1. Lexical crisis indicators (severity-weighted keyword matching)
  2. Sentiment volume spikes (statistical anomaly vs. rolling baseline)
  3. Viral signal detection (engagement velocity)
  4. Escalation pattern recognition

Output: Crisis severity score, alert level, affected topics, recommended actions.
"""

from __future__ import annotations

import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import Counter

logger = logging.getLogger(__name__)

# ─── Crisis signal dictionary ─────────────────────────────────────────────
CRISIS_SIGNALS = {
    # Tier 1: Immediate escalation (Critical)
    "legal": {
        "weight": 10,
        "keywords": ["lawsuit", "legal action", "lawyer", "attorney", "sue", "suing", "court", "fraud"],
    },
    "data_breach": {
        "weight": 10,
        "keywords": ["data breach", "hack", "hacked", "data leak", "personal information", "privacy breach", "exposed data"],
    },
    "safety": {
        "weight": 9,
        "keywords": ["unsafe", "dangerous", "injury", "accident", "recall", "hazard", "toxic", "contaminate"],
    },
    # Tier 2: High concern (High alert)
    "outrage": {
        "weight": 6,
        "keywords": ["outrageous", "unacceptable", "disgusting", "furious", "enraged", "appalled", "scandalous"],
    },
    "viral_threat": {
        "weight": 5,
        "keywords": ["going viral", "twitter storm", "trending", "boycott", "cancel", "report them", "share this"],
    },
    "financial_dispute": {
        "weight": 5,
        "keywords": ["chargeback", "dispute with bank", "credit card fraud", "unauthorized charge", "stolen money", "scam"],
    },
    # Tier 3: Monitor (Medium alert)
    "service_failure": {
        "weight": 3,
        "keywords": ["down", "outage", "not working", "completely unusable", "offline", "broken system"],
    },
    "mass_complaint": {
        "weight": 3,
        "keywords": ["everyone is", "all users", "mass", "widespread", "not just me", "many customers", "multiple reports"],
    },
    # Tier 4: Low concern (informational)
    "churn_signal": {
        "weight": 2,
        "keywords": ["considering switching", "looking at competitors", "thinking about leaving", "evaluating alternatives"],
    },
    "mild_frustration": {
        "weight": 1,
        "keywords": ["switching", "competitor", "canceling", "unsubscribe", "leaving", "refund"],
    },
}

ALERT_LEVELS = {
    (0, 3): ("low", "🟢", "No action required. Continue standard monitoring."),
    (3, 6): ("medium", "🟡", "Elevated concern. Assign monitoring owner and prepare response draft."),
    (6, 12): ("high", "🟠", "High alert. Escalate to communications team within 2 hours."),
    (12, 99): ("critical", "🔴", "CRITICAL. Activate crisis response playbook immediately."),
}


def _get_alert_level(score: float) -> Dict:
    for (low, high), (level, emoji, action) in ALERT_LEVELS.items():
        if low <= score < high:
            return {"level": level, "emoji": emoji, "recommended_action": action}
    return {"level": "critical", "emoji": "🔴", "recommended_action": "CRITICAL. Activate crisis response."}


class CrisisDetector:
    """
    Multi-signal crisis detection system.
    
    Designed to catch problems early — before they trend, before they go viral.
    """

    def score_post(self, text: str, likes: int = 0) -> Dict:
        """
        Score a single post for crisis signals.
        
        Returns crisis score, triggered signals, and alert level.
        """
        text_lower = text.lower()
        total_score = 0.0
        triggered_signals = []
        max_signal_tier = 0  # Track highest severity signal

        for signal_name, signal_data in CRISIS_SIGNALS.items():
            matched_keywords = [kw for kw in signal_data["keywords"] if kw in text_lower]
            if matched_keywords:
                signal_score = signal_data["weight"] * len(matched_keywords)
                total_score += signal_score
                
                # Track the highest tier signal for multiplier logic
                tier = signal_data["weight"]
                if tier > max_signal_tier:
                    max_signal_tier = tier
                
                triggered_signals.append({
                    "signal": signal_name,
                    "keywords": matched_keywords,
                    "score": signal_score,
                    "weight": signal_data["weight"],
                })

        # Conservative engagement amplification
        # Only amplify if there are genuinely high-severity signals
        engagement_multiplier = 1.0
        if max_signal_tier >= 9:  # Legal, breach, safety - CRITICAL tier
            if likes > 100:
                engagement_multiplier = 1.5
            if likes > 500:
                engagement_multiplier = 2.0
        elif max_signal_tier >= 6:  # Medium-high tier (outrage, viral)
            if likes > 500:
                engagement_multiplier = 1.25  # Very conservative
        # Low-tier signals (performance, churn) get NO amplification

        final_score = round(total_score * engagement_multiplier, 2)
        alert = _get_alert_level(final_score)

        return {
            "score": final_score,
            "raw_score": total_score,
            "engagement_multiplier": engagement_multiplier,
            "triggered_signals": sorted(triggered_signals, key=lambda x: x["score"], reverse=True),
            "alert_level": alert["level"],
            "alert_emoji": alert["emoji"],
            "recommended_action": alert["recommended_action"],
            "is_crisis": final_score >= 6,  # Changed threshold from 8 to 6
        }

    def detect_volume_spike(self, series: List[Dict], window: int = 7) -> Optional[Dict]:
        """
        Detect statistically significant spikes in negative sentiment volume.
        Returns spike info if detected, None otherwise.
        """
        if len(series) < window + 1:
            return None

        recent = series[-window:]
        baseline = series[-(window * 3):-window]

        recent_neg_rate = sum(d.get("negative", 0) / max(d.get("volume", 1), 1) for d in recent) / len(recent)
        baseline_neg_rate = sum(d.get("negative", 0) / max(d.get("volume", 1), 1) for d in baseline) / max(len(baseline), 1)

        if baseline_neg_rate == 0:
            return None

        spike_ratio = recent_neg_rate / baseline_neg_rate

        if spike_ratio > 2.0:
            return {
                "detected": True,
                "spike_ratio": round(spike_ratio, 2),
                "recent_neg_rate": round(recent_neg_rate, 3),
                "baseline_neg_rate": round(baseline_neg_rate, 3),
                "severity": "critical" if spike_ratio > 4 else "high" if spike_ratio > 2.5 else "medium",
                "description": f"Negative sentiment volume is {spike_ratio:.1f}× baseline over the last {window} days.",
            }
        return None

    def scan_corpus(self, posts: List[Dict]) -> Dict:
        """
        Scan a corpus of posts for crisis signals.
        
        Returns aggregated crisis report with top crisis posts,
        active signals, and timeline of crisis events.
        """
        crisis_posts = []
        signal_counter: Counter = Counter()
        level_counter: Counter = Counter()

        for post in posts:
            result = self.score_post(
                post.get("text", ""),
                likes=post.get("likes", 0),
            )
            if result["score"] > 2:  # Include any post with signal
                crisis_posts.append({
                    **post,
                    "crisis_score": result["score"],
                    "alert_level": result["alert_level"],
                    "triggered_signals": result["triggered_signals"],
                })
                level_counter[result["alert_level"]] += 1
                for sig in result["triggered_signals"]:
                    signal_counter[sig["signal"]] += 1

        crisis_posts.sort(key=lambda x: x["crisis_score"], reverse=True)

        # Overall assessment - only count HIGH + CRITICAL as "active crises"
        active_crises = [p for p in crisis_posts if p["alert_level"] in ("high", "critical")]
        overall_level = "critical" if level_counter["critical"] > 0 else \
                        "high" if level_counter["high"] > 2 else \
                        "medium" if level_counter["medium"] > 5 else "low"

        return {
            "overall_alert_level": overall_level,
            "total_crisis_posts": len(crisis_posts),
            "active_crises": len(active_crises),
            "top_crisis_posts": crisis_posts[:10],
            "signal_frequency": dict(signal_counter.most_common(8)),
            "level_distribution": dict(level_counter),
            "needs_immediate_action": overall_level in ("high", "critical"),
            "summary": self._generate_summary(overall_level, signal_counter, len(active_crises)),
        }

    def _generate_summary(self, level: str, signals: Counter, active: int) -> str:
        top_signal = signals.most_common(1)[0][0].replace("_", " ") if signals else "general negativity"
        if level == "critical":
            return f"🔴 CRITICAL: {active} high-severity posts detected. Primary signal: {top_signal}. Activate crisis playbook."
        if level == "high":
            return f"🟠 HIGH ALERT: Elevated negative signals around {top_signal}. Assign response team immediately."
        if level == "medium":
            return f"🟡 MONITOR: Recurring complaints about {top_signal}. Prepare response templates."
        return f"🟢 LOW: Normal signal levels. Minor mentions of {top_signal} — no immediate action needed."


# ─── Singleton ─────────────────────────────────────────────────────────────
_detector: Optional[CrisisDetector] = None


def get_crisis_detector() -> CrisisDetector:
    global _detector
    if _detector is None:
        _detector = CrisisDetector()
    return _detector
