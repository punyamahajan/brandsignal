# BrandSignal

### D2C Market & Competitive Intelligence

> **Understand what's changing in your market. Understand where you stand.**

BrandSignal is an analytics-first competitive intelligence platform designed to help D2C businesses understand their position within a changing market.

Instead of telling a business what it should do, BrandSignal focuses on three questions:

1. **What's happening around my business?**
2. **How does my business compare with similar brands?**
3. **Where are the meaningful gaps or changes?**

The goal is to bring fragmented market and business signals together and turn them into a clear, evidence-based view of the competitive landscape.

---

## Why BrandSignal?

D2C businesses interact with large amounts of information across different platforms:

- Search demand
- Product pricing
- Customer reviews
- Content activity
- Competitor activity
- Website performance
- Internal business metrics

These signals are often fragmented across different sources.

A change in market demand may appear in search behaviour, while competitor pricing changes on their website and customer sentiment appears in reviews.

BrandSignal brings these signals together to help businesses understand **what is changing, where they stand, and how their position is evolving over time.**

---

## Core Questions

### 🌎 Market

**What's happening around me?**

Track changes in search demand, pricing, customer sentiment, content activity and other observable market signals.

### 🏢 Competition

**How do comparable brands differ?**

Benchmark a brand against a carefully selected competitive set and category-level statistics.

### 📍 Position

**Where do I stand?**

Identify areas where a brand is above, below, or moving differently from its competitive benchmark.

### 📡 Signals

**What's changing?**

Detect meaningful changes in market and competitive behaviour over time.

---

## Analytical Approach

BrandSignal follows an analytics-first workflow:

```text
Real-world data
      ↓
Data collection
      ↓
Cleaning & validation
      ↓
Exploratory analysis
      ↓
Benchmarking
      ↓
Statistical analysis
      ↓
Business intelligence
      ↓
Human decision
```

---

## Running BrandSignal

### 1. Start the FastAPI Intelligence Backend
```bash
uvicorn backend.main:app --port 8000 --reload
```
Interactive API documentation is available at `http://localhost:8000/docs`.

### 2. Start the React / Vite Frontend
```bash
cd frontend
npm run dev
```
Open `http://localhost:5173` in your browser.

### 3. Run the Automated Test Suite
```bash
pytest -v
```
All 113 tests validate DuckDB data integrity, analytics feature calculations, and FastAPI endpoints.