"""
Competitor Intelligence Engine
─────────────────────────────────────────────────────────────────────────────
Problem: Strategy teams were making product decisions without knowing how their
brand sentiment compared to competitors — or what competitor weaknesses they
could exploit.

Solution: Extract and analyze competitor mentions from the same corpus,
building a comparative intelligence layer that surfaces switch signals,
competitive advantage gaps, and opportunity areas.
"""

from __future__ import annotations

import re
import logging
from typing import List, Dict, Optional
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

# ─── Tracked entities ─────────────────────────────────────────────────────
DEFAULT_COMPETITORS = {
    "RivalOne": ["rivalone", "rival one", "rival-one"],
    "CompeteX": ["competex", "compete x", "compete-x", "cx platform"],
    "AltStream": ["altstream", "alt stream", "alt-stream"],
}

SWITCH_SIGNALS = [
    "switching from", "switched from", "migrating from", "moved from",
    "replaced", "replacing", "considering switching", "evaluating alternatives",
    "compared to", "better than", "worse than", "instead of",
    "vs ", "versus",
]

ADVANTAGE_KEYWORDS = {
    "pricing": ["cheaper", "expensive", "pricing", "cost", "value", "affordable"],
    "features": ["feature", "capability", "function", "support", "integration"],
    "support": ["support", "customer service", "response", "help"],
    "ease_of_use": ["easier", "simpler", "intuitive", "complex", "confusing", "user-friendly"],
    "performance": ["faster", "slower", "reliable", "uptime", "performance", "stable"],
    "documentation": ["docs", "documentation", "guide", "tutorial", "onboarding"],
}


class CompetitorIntel:
    """
    Competitor mention extraction and comparative intelligence.
    
    Scans a corpus for competitor mentions, extracts context,
    classifies switch direction, and identifies competitive gaps.
    """

    def __init__(self, competitors: Optional[Dict[str, List[str]]] = None):
        self.competitors = competitors or DEFAULT_COMPETITORS
        # Pre-compile patterns for speed
        self._patterns = {
            name: re.compile(
                r"\b(" + "|".join(re.escape(alias) for alias in aliases) + r")\b",
                re.IGNORECASE,
            )
            for name, aliases in self.competitors.items()
        }

    def extract_mentions(self, posts: List[Dict]) -> Dict[str, List[Dict]]:
        """Extract all competitor mentions from the corpus."""
        mentions: Dict[str, List[Dict]] = defaultdict(list)

        for post in posts:
            text = post.get("text", "")
            for name, pattern in self._patterns.items():
                if pattern.search(text):
                    mentions[name].append({
                        "post_id": post.get("id", ""),
                        "text": text,
                        "timestamp": post.get("timestamp", ""),
                        "source": post.get("source", ""),
                        "sentiment": post.get("sentiment", post.get("true_label", "neutral")),
                        "likes": post.get("likes", 0),
                    })

        return dict(mentions)

    def _detect_switch_direction(self, text: str, competitor: str) -> Optional[str]:
        """Detect if the post signals switching to or from the competitor."""
        text_lower = text.lower()
        comp_lower = competitor.lower()

        for signal in SWITCH_SIGNALS:
            if signal in text_lower:
                signal_pos = text_lower.find(signal)
                comp_pos = text_lower.find(comp_lower)
                if comp_pos == -1:
                    continue
                # If competitor comes after "switched FROM" → user left competitor
                if comp_pos > signal_pos and "from" in signal:
                    return "switched_away_from_competitor"
                # If competitor mentioned in comparison context
                if "compared to" in signal or "vs" in signal:
                    return "comparison"
                return "considering_switch"

        return None

    def _detect_advantage_gaps(self, text: str) -> List[str]:
        """Identify which dimensions are being compared."""
        text_lower = text.lower()
        gaps = []
        for dimension, keywords in ADVANTAGE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                gaps.append(dimension)
        return gaps

    def build_competitive_report(
        self,
        posts: List[Dict],
        brand_name: str = "TechFlow",
        brand_overall_sentiment: float = 0.72,
    ) -> Dict:
        """
        Full competitive intelligence report.
        
        Returns per-competitor analysis plus brand positioning summary.
        """
        mentions = self.extract_mentions(posts)

        competitor_profiles = {}
        for comp_name in self.competitors:
            comp_mentions = mentions.get(comp_name, [])
            
            # Sentiment breakdown of competitor mentions
            sent_dist = Counter(m["sentiment"] for m in comp_mentions)
            total_mentions = len(comp_mentions)

            # Switch signals
            switch_signals = []
            advantage_gaps = Counter()
            for m in comp_mentions:
                direction = self._detect_switch_direction(m["text"], comp_name)
                if direction:
                    switch_signals.append({"direction": direction, "text": m["text"][:150]})
                gaps = self._detect_advantage_gaps(m["text"])
                for gap in gaps:
                    advantage_gaps[gap] += 1

            switched_away = sum(1 for s in switch_signals if s["direction"] == "switched_away_from_competitor")
            
            # Rough sentiment score from mention context
            pos = sent_dist.get("positive", 0)
            neg = sent_dist.get("negative", 0) + sent_dist.get("crisis", 0)
            comp_sentiment = pos / max(total_mentions, 1) if total_mentions > 0 else 0.5

            competitor_profiles[comp_name] = {
                "name": comp_name,
                "mention_count": total_mentions,
                "sentiment_score": round(comp_sentiment, 3),
                "sentiment_distribution": dict(sent_dist),
                "switch_signals": switch_signals[:5],
                "users_switched_away": switched_away,
                "top_comparison_dimensions": dict(advantage_gaps.most_common(4)),
                "top_mentions": sorted(comp_mentions, key=lambda x: x["likes"], reverse=True)[:3],
            }

        # Opportunity matrix: where competitors are weak, we can win
        opportunities = self._find_opportunities(competitor_profiles)

        return {
            "brand": brand_name,
            "brand_sentiment": brand_overall_sentiment,
            "competitors": competitor_profiles,
            "opportunities": opportunities,
            "total_competitive_mentions": sum(len(v) for v in mentions.values()),
            "market_share_of_voice": self._share_of_voice(mentions, len(posts)),
        }

    def _find_opportunities(self, profiles: Dict) -> List[Dict]:
        """Surface dimensions where competitors are underperforming."""
        opportunities = []
        for comp_name, profile in profiles.items():
            if profile["sentiment_score"] < 0.55:
                opportunities.append({
                    "competitor": comp_name,
                    "opportunity": f"{comp_name} shows weak sentiment ({profile['sentiment_score']:.0%}). "
                                   f"Users are looking for alternatives.",
                    "action": "Create targeted comparison content highlighting your strengths.",
                    "priority": "high" if profile["sentiment_score"] < 0.45 else "medium",
                })

            for dim, count in profile.get("top_comparison_dimensions", {}).items():
                if count >= 2:
                    opportunities.append({
                        "competitor": comp_name,
                        "opportunity": f"Users frequently compare {comp_name} on '{dim}' ({count} mentions).",
                        "action": f"Strengthen your {dim} positioning in marketing and product.",
                        "priority": "medium",
                    })

        return sorted(opportunities, key=lambda x: x["priority"] == "high", reverse=True)[:6]

    def _share_of_voice(self, mentions: Dict, total_posts: int) -> Dict:
        """Calculate share of voice for each competitor."""
        if total_posts == 0:
            return {}
        return {
            name: round(100 * len(posts) / total_posts, 1)
            for name, posts in mentions.items()
        }


# ─── Singleton ─────────────────────────────────────────────────────────────
_intel: Optional[CompetitorIntel] = None


def get_competitor_intel() -> CompetitorIntel:
    global _intel
    if _intel is None:
        _intel = CompetitorIntel()
    return _intel
