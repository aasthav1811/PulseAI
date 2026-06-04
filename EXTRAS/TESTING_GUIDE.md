# Crisis Detection Testing Guide

## Quick Test Commands

Once backend is running, test the fixes with these curl commands:

### Test 1: Normal Complaint (Should be MEDIUM)

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The dashboard is beautiful but the loading times are painfully slow. Support responded quickly which I appreciate, but the performance issues make this hard to recommend. Considering switching to a competitor.",
    "include_crisis": true
  }'
```

**Expected Response:**
```json
{
  "sentiment": {
    "label": "negative",
    "confidence": 0.85
  },
  "crisis": {
    "score": 7,
    "alert_level": "medium",
    "alert_emoji": "🟡",
    "recommended_action": "Elevated concern. Assign monitoring owner and prepare response draft."
  }
}
```

✅ **PASS if:** score 6-9, alert_level = "medium", emoji = "🟡"  
❌ **FAIL if:** score 12+, alert_level = "critical", emoji = "🔴"

---

### Test 2: Actual Crisis (Should be CRITICAL)

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "ZERO stars. Data breach - my personal information appeared in another user'\''s account. Already contacted my lawyer and disputing charges with my bank. This is a scam.",
    "include_crisis": true
  }'
```

**Expected Response:**
```json
{
  "crisis": {
    "score": 20,
    "alert_level": "critical",
    "alert_emoji": "🔴",
    "triggered_signals": [
      {"signal": "data_breach", "keywords": ["data breach"], "score": 10},
      {"signal": "legal", "keywords": ["lawyer"], "score": 10}
    ]
  }
}
```

✅ **PASS if:** score 12+, alert_level = "critical", emoji = "🔴"

---

### Test 3: Praise with Minor Issue (Should be LOW)

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I absolutely love this platform! The dashboard is gorgeous and the sentiment analysis is incredibly accurate. Just one small performance issue during peak hours.",
    "include_crisis": true
  }'
```

**Expected Response:**
```json
{
  "sentiment": {
    "label": "positive",
    "confidence": 0.92
  },
  "crisis": {
    "score": 3,
    "alert_level": "low",
    "alert_emoji": "🟢"
  }
}
```

✅ **PASS if:** score 0-3, alert_level = "low", emoji = "🟢"

---

### Test 4: Outrage (Should be HIGH)

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This is completely unacceptable! System outage for 6 hours with zero status updates. The support team is completely useless. Disputing with my bank and leaving negative reviews everywhere.",
    "include_crisis": true
  }'
```

**Expected Response:**
```json
{
  "crisis": {
    "score": 12,
    "alert_level": "high",
    "alert_emoji": "🟠",
    "triggered_signals": [
      {"signal": "outrage", "score": 6},
      {"signal": "service_failure", "score": 3},
      {"signal": "financial_dispute", "score": 3}
    ]
  }
}
```

✅ **PASS if:** score 6-12, alert_level = "high", emoji = "🟠"

---

### Test 5: Viral Threat (Should be HIGH/CRITICAL based on score)

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "OMG this product is a disaster! Everyone on Twitter is talking about how bad this is. This is going VIRAL and the company is not responding. Boycott now!",
    "include_crisis": true
  }'
```

**Expected Response:**
```json
{
  "crisis": {
    "score": 11,
    "alert_level": "high",
    "alert_emoji": "🟠",
    "triggered_signals": [
      {"signal": "viral_threat", "score": 5},
      {"signal": "outrage", "score": 6}
    ]
  }
}
```

✅ **PASS if:** score 6+, alert_level = "high" or higher

---

## Browser Testing

### Via Dashboard

1. Open `http://localhost:3000`
2. Go to **Live Analyzer** section (left sidebar)
3. Paste test texts and click "⚡ Analyze"
4. Check the Crisis Score badge:
   - 🟢 = LOW (0-3)
   - 🟡 = MEDIUM (3-6)
   - 🟠 = HIGH (6-12)
   - 🔴 = CRITICAL (12+)

### Expected Color Pattern

| Text Content | Expected | Color |
|---|---|---|
| Beautiful UI, slow performance, considering switching | 🟡 MEDIUM | Yellow |
| Data breach, personal info exposed, contacting lawyer | 🔴 CRITICAL | Red |
| Love the features, works great | 🟢 LOW | Green |
| System down, unacceptable, disputing charges | 🟠 HIGH | Orange |

---

## Signal Weight Reference

Use this to understand why posts score as they do:

### CRITICAL Signals (Weight 9-10)
- `legal` (weight: 10) — lawyer, lawsuit, court, legal action, sue
- `data_breach` (weight: 10) — data breach, hack, personal information exposed
- `safety` (weight: 9) — unsafe, dangerous, injury, recall, hazard

### HIGH Signals (Weight 5-6)
- `outrage` (weight: 6) — unacceptable, disgusting, furious, appalled
- `viral_threat` (weight: 5) — going viral, trending, boycott, cancel
- `financial_dispute` (weight: 5) — chargeback, credit card fraud, stolen money

### MEDIUM Signals (Weight 3)
- `service_failure` (weight: 3) — down, outage, completely unusable, offline
- `mass_complaint` (weight: 3) — everyone is, all users, widespread, many customers

### LOW Signals (Weight 1-2)
- `churn_signal` (weight: 2) — considering switching, evaluating alternatives
- `mild_frustration` (weight: 1) — switching, competitor, leaving, unsubscribe

---

## Troubleshooting

### Issue: Still seeing CRITICAL alerts for normal complaints

**Solution:** Restart backend after fix is installed

```bash
# Kill old process
Ctrl+C

# Make sure you have latest code
cd backend
git pull origin main  # or re-download zip

# Start fresh
python main.py
```

### Issue: Crisis scores don't match expected values

**Check 1:** Make sure backend is on the NEW code
```bash
# Check crisis_detector.py has new ALERT_LEVELS
grep -A 3 "ALERT_LEVELS = {" backend/nlp/crisis_detector.py

# Should show: (0, 3): ... (3, 6): ... (6, 12): ... (12, 99): ...
```

**Check 2:** Verify weights in CRISIS_SIGNALS
```bash
grep "weight\":" backend/nlp/crisis_detector.py | head -10

# Should show mix of 1, 2, 3, 5, 6, 9, 10
```

### Issue: Not seeing "triggered_signals" in response

**Check 1:** Make sure `include_crisis: true` in request
```bash
curl ... -d '{"text": "...", "include_crisis": true}'
```

**Check 2:** Response should include triggered_signals field
```json
{
  "crisis": {
    "triggered_signals": [
      {"signal": "name", "keywords": ["..."], "score": X}
    ]
  }
}
```

---

## Batch Testing Script

Save as `test_crisis.sh`:

```bash
#!/bin/bash

echo "Testing Crisis Detection Fixes..."
echo ""

# Test 1
echo "Test 1: Normal Complaint (Expected: MEDIUM 🟡)"
curl -s -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text":"Dashboard beautiful but slow. Switching to competitor.","include_crisis":true}' \
  | grep -o '"alert_level":"[^"]*"'
echo ""

# Test 2
echo "Test 2: Data Breach (Expected: CRITICAL 🔴)"
curl -s -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text":"Data breach! Personal info exposed. Contacting lawyer.","include_crisis":true}' \
  | grep -o '"alert_level":"[^"]*"'
echo ""

# Test 3
echo "Test 3: Praise (Expected: LOW 🟢)"
curl -s -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text":"I love this platform! Absolutely gorgeous and accurate.","include_crisis":true}' \
  | grep -o '"alert_level":"[^"]*"'
echo ""

echo "Done!"
```

Run with:
```bash
chmod +x test_crisis.sh
./test_crisis.sh
```

---

## Summary

All tests passing? ✅ Crisis detection is now properly calibrated!

- ✅ Normal complaints = LOW/MEDIUM, not CRITICAL
- ✅ True crises = CRITICAL with high scores
- ✅ False positives minimized
- ✅ Alert fatigue reduced
