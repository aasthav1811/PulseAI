"""
Trend Analysis & Forecasting Engine
─────────────────────────────────────────────────────────────────────────────
Problem: Teams were reacting to brand crises days after they peaked because
they had no way to detect sentiment inflection points in real time.

Solution: Rolling statistical analysis on sentiment time series — detects
spikes, dips, and emerging trends before they become crises. Simple
exponential smoothing for short-horizon forecasting.
"""

from __future__ import annotations

import math
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

import numpy as np

logger = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────────
SPIKE_THRESHOLD_STD = 2.0    # Standard deviations for anomaly detection
TREND_WINDOW = 7             # Days for rolling trend calculation
FORECAST_HORIZON = 14        # Days to forecast ahead
ALPHA = 0.3                  # ETS smoothing factor


def _exponential_smoothing(series: List[float], alpha: float = ALPHA) -> List[float]:
    """Simple exponential smoothing (SES)."""
    if not series:
        return []
    smoothed = [series[0]]
    for val in series[1:]:
        smoothed.append(alpha * val + (1 - alpha) * smoothed[-1])
    return smoothed


def _linear_trend(y: List[float]) -> Tuple[float, float]:
    """OLS linear regression slope and intercept."""
    n = len(y)
    if n < 2:
        return 0.0, y[0] if y else 0.0
    x = list(range(n))
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    ss_xy = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    ss_xx = sum((xi - x_mean) ** 2 for xi in x)
    slope = ss_xy / ss_xx if ss_xx != 0 else 0.0
    intercept = y_mean - slope * x_mean
    return slope, intercept


def _rolling_stats(series: List[float], window: int) -> Tuple[List[float], List[float]]:
    """Rolling mean and standard deviation."""
    means, stds = [], []
    for i in range(len(series)):
        window_data = series[max(0, i - window + 1) : i + 1]
        means.append(sum(window_data) / len(window_data))
        if len(window_data) > 1:
            variance = sum((x - means[-1]) ** 2 for x in window_data) / (len(window_data) - 1)
            stds.append(math.sqrt(variance))
        else:
            stds.append(0.0)
    return means, stds


class TrendAnalyzer:
    """
    Sentiment trend analysis engine.
    
    Takes a time-indexed list of labeled posts and returns:
    - Daily sentiment time series
    - Rolling trend direction + momentum
    - Anomaly / crisis detection flags
    - Short-term sentiment forecast
    - Volume trend analysis
    - Emerging topic velocity
    """

    def analyze_time_series(self, series_data: List[Dict]) -> Dict:
        """
        Full trend analysis from daily aggregated series data.
        
        Args:
            series_data: list of {date, sentiment, volume, positive, negative}
        
        Returns:
            Comprehensive trend analysis payload for frontend.
        """
        if not series_data:
            return {}

        dates = [d["date"] for d in series_data]
        sentiments = [d["sentiment"] for d in series_data]
        volumes = [d["volume"] for d in series_data]

        # ── Rolling stats ──────────────────────────────────────────────
        roll_means, roll_stds = _rolling_stats(sentiments, TREND_WINDOW)

        # ── Anomaly detection ─────────────────────────────────────────
        anomalies = []
        for i, (s, m, std) in enumerate(zip(sentiments, roll_means, roll_stds)):
            if std > 0:
                z_score = (s - m) / std
                if abs(z_score) >= SPIKE_THRESHOLD_STD:
                    anomalies.append({
                        "date": dates[i],
                        "sentiment": round(s, 3),
                        "z_score": round(z_score, 2),
                        "direction": "spike" if z_score > 0 else "dip",
                        "severity": "high" if abs(z_score) > 3 else "medium",
                    })

        # ── Overall trend direction ────────────────────────────────────
        slope, intercept = _linear_trend(sentiments)
        if slope > 0.002:
            trend_direction = "improving"
        elif slope < -0.002:
            trend_direction = "declining"
        else:
            trend_direction = "stable"

        # ── ETS Forecast ──────────────────────────────────────────────
        smoothed = _exponential_smoothing(sentiments)
        last_smoothed = smoothed[-1] if smoothed else 0.5
        forecast = []
        last_date = datetime.strptime(dates[-1], "%Y-%m-%d")
        for h in range(1, FORECAST_HORIZON + 1):
            forecast_date = last_date + timedelta(days=h)
            projected = last_smoothed + slope * h
            projected = max(0.05, min(0.99, projected))
            forecast.append({
                "date": forecast_date.strftime("%Y-%m-%d"),
                "sentiment": round(projected, 3),
                "lower": round(max(0.05, projected - 0.08 * math.sqrt(h)), 3),
                "upper": round(min(0.99, projected + 0.08 * math.sqrt(h)), 3),
            })

        # ── Volume trend ──────────────────────────────────────────────
        vol_slope, _ = _linear_trend(volumes[-14:])  # Last 2 weeks
        volume_trend = "growing" if vol_slope > 1 else "shrinking" if vol_slope < -1 else "stable"

        # ── 7-day vs 30-day sentiment comparison ──────────────────────
        avg_7 = sum(sentiments[-7:]) / 7 if len(sentiments) >= 7 else sentiments[-1]
        avg_30 = sum(sentiments[-30:]) / 30 if len(sentiments) >= 30 else sum(sentiments) / len(sentiments)
        sentiment_delta = round(avg_7 - avg_30, 3)

        return {
            "time_series": series_data,
            "smoothed": [
                {"date": dates[i], "sentiment": round(smoothed[i], 3)}
                for i in range(len(dates))
            ],
            "forecast": forecast,
            "anomalies": anomalies,
            "trend": {
                "direction": trend_direction,
                "slope": round(slope, 5),
                "current_sentiment": round(sentiments[-1], 3),
                "avg_7d": round(avg_7, 3),
                "avg_30d": round(avg_30, 3),
                "delta_7d_vs_30d": sentiment_delta,
                "volume_trend": volume_trend,
                "total_volume": sum(volumes),
                "avg_daily_volume": round(sum(volumes) / len(volumes), 1),
            },
        }

    def aggregate_posts_to_series(self, posts: List[Dict]) -> List[Dict]:
        """
        Aggregate raw posts into daily sentiment time series.
        
        Args:
            posts: list of {text, timestamp, true_label or sentiment}
        """
        daily: Dict[str, Dict] = defaultdict(lambda: {"pos": 0, "neg": 0, "neu": 0, "total": 0})

        for post in posts:
            try:
                date = post["timestamp"][:10]  # YYYY-MM-DD
                label = post.get("sentiment", post.get("true_label", "neutral"))
                if label in ("positive", "crisis"):  # crisis treated as negative
                    daily[date]["pos" if label == "positive" else "neg"] += 1
                elif label == "negative":
                    daily[date]["neg"] += 1
                else:
                    daily[date]["neu"] += 1
                daily[date]["total"] += 1
            except Exception:
                continue

        series = []
        for date in sorted(daily.keys()):
            d = daily[date]
            total = max(d["total"], 1)
            sentiment = d["pos"] / total  # Proportion positive
            series.append({
                "date": date,
                "sentiment": round(sentiment, 3),
                "volume": d["total"],
                "positive": d["pos"],
                "negative": d["neg"],
                "neutral": d["neu"],
            })

        return series


# ─── Singleton ─────────────────────────────────────────────────────────────
_analyzer: Optional[TrendAnalyzer] = None


def get_trend_analyzer() -> TrendAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = TrendAnalyzer()
    return _analyzer
