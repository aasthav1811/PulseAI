"""
Sample data generator for Social Intelligence Platform demo.
Simulates real-world product reviews, social posts, and competitor mentions.
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict

# ─── Seed for reproducibility ──────────────────────────────────────────────
random.seed(42)

BRANDS = ["TechFlow", "Nexus AI", "CloudPulse", "DataSpark"]
COMPETITORS = ["RivalOne", "CompeteX", "AltStream"]

POSITIVE_REVIEWS = [
    "Absolutely love the new dashboard update — real-time insights have completely changed how our team operates.",
    "Setup was surprisingly smooth. Was up and running in under an hour. The onboarding flow is excellent.",
    "The sentiment analysis is scarily accurate. Caught a product issue before it became a PR crisis.",
    "Customer support responded within minutes. Rare to see this level of care from a SaaS company.",
    "The topic clustering feature alone is worth the subscription price.",
    "We replaced three separate tools with this one platform. ROI has been incredible.",
    "Mobile app works flawlessly. Can monitor brand health on the go.",
    "The competitor tracking module is a game-changer for our strategy team.",
    "Onboarding documentation is detailed and well-written. Love the product.",
    "Finally, an analytics tool that non-technical stakeholders can actually understand.",
    "The trend forecasting caught an emerging issue 3 days before it hit social media.",
    "Integrations are seamless. Plugged into our Slack and got alerts immediately.",
    "The BERT-powered sentiment analysis is significantly more accurate than alternatives we tried.",
    "Dashboard is gorgeous. My team actually looks forward to the weekly review sessions.",
    "Excellent value for the pricing tier. No hidden fees, transparent usage reporting.",
    "The crisis detection saved us during a product recall situation — literally priceless.",
    "API is well-documented and developer-friendly. Extensible and modern.",
    "The aspect-based sentiment breakdown helps us pinpoint exactly what customers love or hate.",
    "Reports are export-ready and look professional. Clients are impressed.",
    "Great for tracking post-launch sentiment across multiple channels simultaneously.",
]

NEGATIVE_REVIEWS = [
    "The export feature crashes when handling datasets over 10,000 rows. Very frustrating.",
    "Pricing jumped 40% at renewal with no notice. This kind of thing destroys trust.",
    "Loading times are unacceptable. The dashboard takes 8 seconds to render.",
    "Customer support ghosted us for 3 days during a critical monitoring window.",
    "The mobile app loses session state constantly. Had to re-login 5 times today.",
    "Documentation is outdated. Several API endpoints described don't match actual behavior.",
    "Too many false positives in the crisis detection. Our team has alert fatigue now.",
    "Onboarding was confusing. Took us a week to get basic pipelines running.",
    "The competitor tracking misses mentions from smaller niche forums.",
    "Data ingestion pipeline drops roughly 3-5% of posts silently. No error reporting.",
    "The billing portal is a UX disaster. Can't even download invoices easily.",
    "Trend forecasting was way off during our last product launch. Not reliable enough.",
    "No SSO support. This is a dealbreaker for enterprise customers.",
    "The sentiment model clearly wasn't fine-tuned for B2B contexts. Accuracy suffers.",
    "Integrations are shallow. Can pull data in but almost no bi-directional actions.",
]

NEUTRAL_REVIEWS = [
    "Switched from a competitor. The migration process was manageable but took longer than expected.",
    "Feature parity with alternatives is roughly equal. Pricing is the deciding factor.",
    "The API rate limits are fine for our current scale but might be an issue as we grow.",
    "Decent product. Nothing revolutionary but it does what it says on the tin.",
    "The free tier is quite limited. You'll need a paid plan for any real usage.",
    "Had some initial setup issues that were eventually resolved by support.",
    "The UI is clean. Some features require too many clicks to access.",
    "Data refresh rates are acceptable for daily monitoring but not real-time enough for live events.",
    "Works as advertised. Would like to see more customization options in future releases.",
    "The reporting features cover the basics. Power users will want more advanced options.",
]

CRISIS_REVIEWS = [
    "This is a SCAM. They charged me twice and won't issue a refund. Disputing with my bank.",
    "WARNING: Data breach. My private information appeared in another user's dashboard.",
    "ZERO stars. Complete system outage for 6 hours with no status page updates. Unacceptable.",
    "Their AI flagged a completely innocent post as hate speech and got our account banned.",
    "Absolutely catastrophic data loss. Two months of insights just disappeared after an update.",
    "They deleted our entire account without warning. No backup. No explanation. Lawyers involved.",
]

TOPICS = {
    "Performance": ["slow", "loading", "latency", "speed", "fast", "response time", "lag", "crash", "freeze"],
    "Pricing": ["expensive", "cost", "pricing", "value", "subscription", "billing", "refund", "fee", "cheap"],
    "Support": ["support", "response", "help", "team", "customer service", "resolved", "ignored", "ghosted"],
    "UI/UX": ["interface", "design", "dashboard", "ui", "ux", "navigation", "clicks", "intuitive", "confusing"],
    "Features": ["feature", "functionality", "api", "integration", "export", "report", "analysis", "detection"],
    "Onboarding": ["setup", "onboarding", "documentation", "guide", "tutorial", "getting started", "config"],
    "Data Quality": ["accuracy", "false positive", "data", "insights", "model", "analysis quality", "reliable"],
    "Security": ["breach", "security", "privacy", "sso", "authentication", "data leak", "compliance"],
}

COMPETITORS_MENTIONS = [
    "Switched from {c} because of pricing",
    "{c} has better documentation honestly",
    "Compared to {c}, the UI is much cleaner here",
    "{c}'s customer support is faster but their features lag behind",
    "Evaluating {c} as an alternative due to recent pricing changes",
    "We use {c} for X but this platform for Y — wish they'd merge",
    "{c} doesn't offer aspect-based sentiment at this price point",
    "Tried {c} first but their API was too complex for our team",
]


def generate_posts(n: int = 500) -> List[Dict]:
    """Generate synthetic social posts/reviews with timestamps."""
    posts = []
    now = datetime.utcnow()

    # Weight pool: more positive than negative (realistic distribution)
    pool = (
        [(r, "positive") for r in POSITIVE_REVIEWS] * 4
        + [(r, "negative") for r in NEGATIVE_REVIEWS] * 2
        + [(r, "neutral") for r in NEUTRAL_REVIEWS] * 2
        + [(r, "crisis") for r in CRISIS_REVIEWS] * 1
    )

    sources = ["Twitter", "Reddit", "G2", "Trustpilot", "ProductHunt", "AppStore", "LinkedIn"]
    products = ["Core Platform", "Mobile App", "API", "Dashboard", "Integrations", "Support"]

    for i in range(n):
        text, true_label = random.choice(pool)
        
        # Add competitor mentions occasionally
        if random.random() < 0.15:
            comp = random.choice(COMPETITORS)
            mention = random.choice(COMPETITORS_MENTIONS).format(c=comp)
            text = text + " " + mention

        # Spread posts over the last 90 days with recency bias
        days_ago = int(random.betavariate(1.5, 5) * 90)
        timestamp = now - timedelta(
            days=days_ago,
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )

        posts.append({
            "id": f"post_{i:04d}",
            "text": text,
            "true_label": true_label,
            "source": random.choice(sources),
            "product": random.choice(products),
            "timestamp": timestamp.isoformat(),
            "likes": random.randint(0, 500) if true_label in ["positive", "crisis"] else random.randint(0, 50),
            "author": f"user_{random.randint(1000, 9999)}",
        })

    # Inject a crisis cluster 7 days ago
    for i, crisis_text in enumerate(CRISIS_REVIEWS):
        crisis_time = now - timedelta(days=7, hours=random.randint(0, 6))
        posts.append({
            "id": f"crisis_{i:03d}",
            "text": crisis_text,
            "true_label": "crisis",
            "source": random.choice(["Twitter", "Reddit"]),
            "product": "Core Platform",
            "timestamp": crisis_time.isoformat(),
            "likes": random.randint(100, 1000),
            "author": f"user_{random.randint(1000, 9999)}",
        })

    return sorted(posts, key=lambda x: x["timestamp"], reverse=True)


def generate_competitor_data() -> Dict:
    """Generate competitor comparison data."""
    return {
        "TechFlow": {"sentiment_score": 0.72, "mention_volume": 4820, "nps": 67, "trend": "up"},
        "RivalOne": {"sentiment_score": 0.61, "mention_volume": 3200, "nps": 52, "trend": "down"},
        "CompeteX": {"sentiment_score": 0.68, "mention_volume": 2800, "nps": 59, "trend": "stable"},
        "AltStream": {"sentiment_score": 0.55, "mention_volume": 1900, "nps": 41, "trend": "down"},
    }


def generate_time_series(days: int = 90) -> List[Dict]:
    """Generate daily sentiment time series data."""
    now = datetime.utcnow()
    series = []
    
    base_sentiment = 0.65
    trend = 0.001
    
    for day in range(days, -1, -1):
        date = now - timedelta(days=day)
        noise = random.gauss(0, 0.04)
        
        # Crisis dip 7 days ago
        crisis_dip = -0.25 if 5 <= day <= 8 else 0
        
        sentiment = max(0.1, min(0.99, base_sentiment + trend * (90 - day) + noise + crisis_dip))
        volume = int(random.gauss(120, 30) * (1 + 0.5 * (1 if day < 30 else 0)))
        
        series.append({
            "date": date.strftime("%Y-%m-%d"),
            "sentiment": round(sentiment, 3),
            "volume": max(10, volume),
            "positive": round(sentiment * 0.9, 3),
            "negative": round((1 - sentiment) * 0.8, 3),
        })
    
    return series
