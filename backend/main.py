"""
Social Intelligence Platform — FastAPI Backend
─────────────────────────────────────────────────────────────────────────────
Main application entrypoint. Wires together the NLP pipelines and exposes
a clean REST API for the frontend dashboard.

Architecture:
  POST /api/analyze          → Single text sentiment + crisis + aspects
  POST /api/batch-analyze    → Bulk post analysis
  GET  /api/dashboard        → Full dashboard data payload
  GET  /api/topics           → Topic clusters
  GET  /api/trends           → Time series + forecast
  GET  /api/competitors      → Competitor intelligence
  GET  /api/crisis           → Crisis scan results
  POST /api/ingest           → Add posts to the demo corpus
  GET  /api/health           → Health check
"""

from __future__ import annotations

import logging
import sys
import time
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ─── Internal modules ─────────────────────────────────────────────────────
sys.path.append(".")

from data.sample_data import generate_posts, generate_competitor_data, generate_time_series
from nlp.sentiment import get_analyzer
from nlp.topic_model import get_modeler
from nlp.trend_analysis import get_trend_analyzer
from nlp.crisis_detector import get_crisis_detector
from nlp.competitor_intel import get_competitor_intel

logging.basicConfig(level=logging.INFO, format="%(asctime)s │ %(levelname)s │ %(message)s")
logger = logging.getLogger(__name__)

# ─── In-memory state (replace with DB for production) ─────────────────────
_corpus: List[dict] = []
_analysis_cache: dict = {}
_initialized = False


def _bootstrap() -> None:
    """Generate sample data, run NLP pipeline, cache results."""
    global _corpus, _analysis_cache, _initialized

    logger.info("Bootstrapping platform with sample data...")
    t0 = time.time()

    # Generate posts
    _corpus = generate_posts(n=200)
    texts = [p["text"] for p in _corpus]

    # ── Sentiment analysis ────────────────────────────────────────────
    analyzer = get_analyzer()
    logger.info(f"Running sentiment on {len(texts)} posts (mode: {analyzer.mode})...")
    sentiments = analyzer.batch_analyze(texts)
    for i, post in enumerate(_corpus):
        post["sentiment"] = sentiments[i]["label"]
        post["sentiment_score"] = sentiments[i]["score"]

    # ── Topic modeling ────────────────────────────────────────────────
    logger.info("Fitting topic model...")
    modeler = get_modeler(n_topics=8)
    modeler.fit(texts)
    topic_labels = modeler.get_document_topics(texts)
    for i, post in enumerate(_corpus):
        post["topic_id"] = topic_labels[i]
        post["topic_name"] = modeler.topic_names[topic_labels[i]]

    sentiment_labels = [p["sentiment"] for p in _corpus]
    topics_summary = modeler.get_topics_summary(texts, sentiments=sentiment_labels)

    # ── Trend analysis ────────────────────────────────────────────────
    logger.info("Running trend analysis...")
    trend_analyzer = get_trend_analyzer()
    raw_series = trend_analyzer.aggregate_posts_to_series(_corpus)
    # Merge with richer pre-generated series for longer history
    extended_series = generate_time_series(days=90)
    trend_data = trend_analyzer.analyze_time_series(extended_series)

    # ── Crisis detection ──────────────────────────────────────────────
    logger.info("Running crisis scan...")
    detector = get_crisis_detector()
    crisis_report = detector.scan_corpus(_corpus)
    volume_spike = detector.detect_volume_spike(raw_series)

    # ── Competitor intelligence ───────────────────────────────────────
    logger.info("Building competitor intelligence...")
    intel = get_competitor_intel()
    comp_report = intel.build_competitive_report(
        _corpus,
        brand_name="TechFlow",
        brand_overall_sentiment=float(trend_data["trend"]["avg_30d"]),
    )

    # ── Assemble dashboard payload ────────────────────────────────────
    pos_count = sum(1 for p in _corpus if p["sentiment"] == "positive")
    neg_count = sum(1 for p in _corpus if p["sentiment"] == "negative")
    total = len(_corpus)

    _analysis_cache = {
        "meta": {
            "total_posts": total,
            "model_mode": analyzer.mode,
            "bootstrapped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "elapsed_seconds": round(time.time() - t0, 1),
        },
        "summary": {
            "overall_sentiment": trend_data["trend"]["current_sentiment"],
            "avg_7d_sentiment": trend_data["trend"]["avg_7d"],
            "avg_30d_sentiment": trend_data["trend"]["avg_30d"],
            "delta": trend_data["trend"]["delta_7d_vs_30d"],
            "trend_direction": trend_data["trend"]["direction"],
            "total_volume": trend_data["trend"]["total_volume"],
            "avg_daily_volume": trend_data["trend"]["avg_daily_volume"],
            "positive_count": pos_count,
            "negative_count": neg_count,
            "neutral_count": total - pos_count - neg_count,
            "positive_pct": round(100 * pos_count / total, 1),
            "negative_pct": round(100 * neg_count / total, 1),
            "nps_estimate": round((pos_count - neg_count) / total * 100, 1),
            "crisis_alert": crisis_report["overall_alert_level"],
        },
        "topics": topics_summary,
        "trends": trend_data,
        "crisis": crisis_report,
        "volume_spike": volume_spike,
        "competitors": comp_report,
        "recent_posts": _corpus[:50],
    }

    _initialized = True
    logger.info(f"Bootstrap complete in {time.time() - t0:.1f}s")


# ─── App startup ───────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    _bootstrap()
    yield


app = FastAPI(
    title="Social Intelligence Platform API",
    description="AI-powered brand monitoring, sentiment analysis, and competitor intelligence.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Schemas ───────────────────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    include_aspects: bool = True
    include_crisis: bool = True


class BatchAnalyzeRequest(BaseModel):
    texts: List[str] = Field(..., min_items=1, max_items=200)


class IngestRequest(BaseModel):
    posts: List[dict]


# ─── Routes ────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "initialized": _initialized,
        "corpus_size": len(_corpus),
        "model_mode": get_analyzer().mode,
    }


@app.get("/api/dashboard")
async def dashboard():
    if not _initialized:
        raise HTTPException(503, "Platform is initializing. Please try again in a moment.")
    return _analysis_cache


@app.get("/api/summary")
async def summary():
    if not _initialized:
        raise HTTPException(503, "Initializing...")
    return _analysis_cache["summary"]


@app.get("/api/topics")
async def topics():
    if not _initialized:
        raise HTTPException(503, "Initializing...")
    return {"topics": _analysis_cache["topics"]}


@app.get("/api/trends")
async def trends():
    if not _initialized:
        raise HTTPException(503, "Initializing...")
    return _analysis_cache["trends"]


@app.get("/api/crisis")
async def crisis():
    if not _initialized:
        raise HTTPException(503, "Initializing...")
    return {
        "crisis": _analysis_cache["crisis"],
        "volume_spike": _analysis_cache.get("volume_spike"),
    }


@app.get("/api/competitors")
async def competitors():
    if not _initialized:
        raise HTTPException(503, "Initializing...")
    return _analysis_cache["competitors"]


@app.get("/api/posts")
async def posts(limit: int = 50, sentiment: Optional[str] = None, source: Optional[str] = None):
    filtered = _corpus
    if sentiment:
        filtered = [p for p in filtered if p.get("sentiment") == sentiment]
    if source:
        filtered = [p for p in filtered if p.get("source", "").lower() == source.lower()]
    return {"posts": filtered[:limit], "total": len(filtered)}


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    """Real-time analysis of a single text."""
    analyzer = get_analyzer()
    sentiment = analyzer.analyze(req.text)

    result = {"text": req.text, "sentiment": sentiment}

    if req.include_aspects:
        aspects = analyzer.analyze_aspects(req.text)
        result["aspects"] = aspects

    if req.include_crisis:
        detector = get_crisis_detector()
        crisis = detector.score_post(req.text)
        result["crisis"] = crisis

    return result


@app.post("/api/batch-analyze")
async def batch_analyze(req: BatchAnalyzeRequest):
    """Batch analysis of multiple texts."""
    analyzer = get_analyzer()
    results = analyzer.batch_analyze(req.texts)
    return {"results": results, "count": len(results)}


@app.post("/api/ingest")
async def ingest(req: IngestRequest, background_tasks: BackgroundTasks):
    """Add new posts to the corpus and trigger re-analysis."""
    global _corpus
    _corpus = req.posts + _corpus
    background_tasks.add_task(_bootstrap)
    return {"status": "accepted", "posts_added": len(req.posts), "total": len(_corpus)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
