import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class IntentMatch:
    intent: str
    confidence: float
    matched_phrases: List[str]

# Deterministic Intent Matching Rules
INTENT_PATTERNS = {
    "MARKET_OVERVIEW": {
        "phrases": [
            r"what('?s| is) happening( in my market| in the market)?",
            r"market overview",
            r"category overview",
            r"market summary",
            r"how is the market( doing)?",
            r"state of the market",
            r"landscape overview",
            r"what is trending( right now)?",
            r"what('?s| is) trending",
            r"macro view",
            r"tell me about the footwear market"
        ],
        "keywords": ["market", "overview", "landscape", "trending", "trends", "happening", "summary"],
        "weight": 1.0
    },
    "COMPETITOR_COMPARISON": {
        "phrases": [
            r"how (does|do|is) (my brand|we|us|\w+)( performing)? (compare|compared) (with|to|against) \w+",
            r"compare (me|my brand|\w+) (with|to|against) \w+",
            r"\w+ vs \w+",
            r"competitor comparison",
            r"head to head",
            r"benchmark (me|my brand|\w+) against"
        ],
        "keywords": ["compare", "compared", "comparing", "comparison", "vs", "versus", "against", "competitor", "benchmark"],
        "weight": 1.2
    },
    "ASSORTMENT_COMPARISON": {
        "phrases": [
            r"who has (more|the most|fewer|the fewest) (products|styles|skus|variants)",
            r"catalog (breadth|depth|scale) comparison",
            r"who has (a )?(bigger|smaller|larger) catalog",
            r"assortment comparison",
            r"compare (catalog|assortment|styles|skus)",
            r"variant density comparison",
            r"who has the widest (catalog|assortment)"
        ],
        "keywords": ["products", "styles", "skus", "variants", "breadth", "depth", "assortment", "catalog", "density"],
        "weight": 1.1
    },
    "PRICE_COMPARISON": {
        "phrases": [
            r"who is (cheaper|cheapest|more expensive|most expensive)",
            r"compare (prices|pricing|median price|selling price)",
            r"price comparison",
            r"who has (higher|lower) prices",
            r"are my prices (higher|lower)",
            r"pricing landscape",
            r"how do our prices compare",
            r"is \w+ cheaper than \w+"
        ],
        "keywords": ["price", "prices", "pricing", "cheaper", "expensive", "cost", "selling price", "median price"],
        "weight": 1.15
    },
    "DISCOUNT_COMPARISON": {
        "phrases": [
            r"who discounts (the most|more|the least)",
            r"who has (the highest|deepest|the lowest) discounts?",
            r"compare discounts?",
            r"discount comparison",
            r"promotional (comparison|intensity)",
            r"markdown depth comparison",
            r"who offers the (biggest|deepest) (markdown|sale|discount)",
            r"who runs more sales"
        ],
        "keywords": ["discount", "discounts", "discounting", "markdown", "markdowns", "promo", "promotions", "sale"],
        "weight": 1.15
    },
    "SEARCH_TREND": {
        "phrases": [
            r"what happened to search (interest|demand|attention|traffic)",
            r"search (trend|trends|trajectory|history)",
            r"how has search (changed|evolved|grown|dropped)",
            r"google trends (over time|trajectory|history)",
            r"12 month search (trend|history)",
            r"search momentum"
        ],
        "keywords": ["search", "trends", "google trends", "trajectory", "interest over time", "search demand"],
        "weight": 1.1
    },
    "SEARCH_COMPARISON": {
        "phrases": [
            r"who gets (more|the most) search (volume|traffic|interest|attention)",
            r"search (share|attention) comparison",
            r"who is (more|most) popular (on google|in search)",
            r"compare search (attention|share|interest)",
            r"who leads (in )?search"
        ],
        "keywords": ["search share", "search attention", "cohort search", "relative search", "popular in search"],
        "weight": 1.15
    },
    "RECENT_CHANGE": {
        "phrases": [
            r"what changed (recently|last week|last month|in search)",
            r"(any )?search spikes",
            r"recent (changes|movements|spikes|drops)",
            r"what moved recently",
            r"any big (changes|jumps|drops) recently"
        ],
        "keywords": ["recent", "recently", "spike", "spikes", "drop", "drops", "jump", "changed recently", "movement"],
        "weight": 1.1
    },
    "BRAND_DIFFERENCE": {
        "phrases": [
            r"(where|what) is (my brand|our brand|\w+) (different|unique|distinct)",
            r"what is different about (my brand|our brand|\w+)",
            r"what (are competitors doing|is the market doing) differently",
            r"what makes (my brand|\w+) different",
            r"how (am i|are we|is my brand|\w+) different",
            r"where do (we|i|\w+) stand out",
            r"brand differentiation"
        ],
        "keywords": ["different", "differently", "difference", "differences", "distinct", "unique", "stand out"],
        "weight": 1.2
    },
    "BRAND_MISSING": {
        "phrases": [
            r"what is (my brand|our brand|\w+) missing",
            r"what (do competitors have|does \w+ have) that i don'?t",
            r"where are my gaps",
            r"where do i fall behind",
            r"what am i lacking"
        ],
        "keywords": ["missing", "gaps", "gap", "lacking", "fall behind", "what do they have"],
        "weight": 1.25
    },
    "CATEGORY_MIX": {
        "phrases": [
            r"what categories (do they sell|are there|does \w+ offer)",
            r"category (mix|breakdown|share|distribution)",
            r"sneaker(s)? share",
            r"formal or casual",
            r"do they sell slides"
        ],
        "keywords": ["category", "categories", "category mix", "product types", "sneakers", "boots", "slides"],
        "weight": 1.1
    },
    "CATALOG_SCALE": {
        "phrases": [
            r"how big is (\w+'?s? )?catalog",
            r"how many (styles|skus|products) (do we have|does \w+ have)",
            r"catalog size",
            r"total (skus|styles|products)"
        ],
        "keywords": ["catalog size", "how many skus", "how many styles", "how many products", "total skus"],
        "weight": 1.1
    },
    "PRICE_POSITIONING": {
        "phrases": [
            r"what is (my|our|\w+'?s) (price positioning|ppi)",
            r"is (my brand|\w+) premium or value",
            r"(our|my) price positioning index"
        ],
        "keywords": ["price positioning", "premium or value", "positioning index", "price index"],
        "weight": 1.15
    },
    "PROMOTIONAL_INTENSITY": {
        "phrases": [
            r"how aggressive are (discounts|promotions)",
            r"how much (is discounted|is on sale)",
            r"percentage of catalog discounted",
            r"promotional intensity"
        ],
        "keywords": ["promotional intensity", "aggressive discounts", "how much is discounted", "discount coverage"],
        "weight": 1.1
    },
    "EXPLAIN_METRIC": {
        "phrases": [
            r"what (is|does) (the )?(ppi|variant density|price iqr|relative search interest|<1|tranco)( mean)?",
            r"explain (ppi|variant density|price iqr|relative search interest|discount depth|<1)",
            r"define (ppi|variant density|iqr|relative search share)",
            r"how is \w+ calculated"
        ],
        "keywords": ["what is ppi", "what is variant density", "explain", "definition", "define", "how is it calculated", "formula"],
        "weight": 1.2
    },
    "DATA_AVAILABILITY": {
        "phrases": [
            r"what data (do you have|is available)",
            r"which brands (are included|can you analyze)",
            r"data (sources|availability|coverage|freshness)",
            r"what is your data source",
            r"where does the data come from"
        ],
        "keywords": ["data sources", "what data", "available data", "which brands", "sources", "coverage"],
        "weight": 1.1
    },
    "HELP": {
        "phrases": [
            r"^(hi|hello|hey|help|what can you do|how to use|guide|options)$",
            r"what (can|should) i ask( you)?",
            r"how does this work"
        ],
        "keywords": ["help", "hello", "hi", "what can you do", "guide", "commands", "options"],
        "weight": 1.0
    }
}

class IntentEngine:
    """
    Deterministic rule-based Intent Classification Engine.
    Uses regex phrases, keyword scoring, and priority weighting.
    Guaranteed zero hallucination, zero LLM reliance.
    """

    @staticmethod
    def classify(query: str) -> IntentMatch:
        """
        Classifies user query into one of the supported intents.
        Returns IntentMatch with intent name, confidence score, and matched tokens.
        """
        cleaned = query.strip().lower()
        if not cleaned:
            return IntentMatch(intent="HELP", confidence=1.0, matched_phrases=["empty_query"])

        best_intent = "UNKNOWN"
        best_score = 0.0
        best_matches: List[str] = []

        for intent_name, config in INTENT_PATTERNS.items():
            score = 0.0
            matches: List[str] = []

            # 1. Regex phrase matching (high value)
            for phrase_pat in config["phrases"]:
                if re.search(phrase_pat, cleaned):
                    score += 5.0
                    matches.append(phrase_pat)

            # 2. Keyword token matching
            for kw in config["keywords"]:
                if re.search(r"\b" + re.escape(kw) + r"\b", cleaned):
                    score += 1.0
                    matches.append(kw)

            # Apply intent weight
            score *= config.get("weight", 1.0)

            if score > best_score:
                best_score = score
                best_intent = intent_name
                best_matches = matches

        # Confidence normalization
        if best_score >= 5.0:
            confidence = min(0.95, 0.70 + (best_score / 20.0))
        elif best_score >= 1.0:
            confidence = min(0.70, 0.40 + (best_score / 10.0))
        else:
            best_intent = "UNKNOWN"
            confidence = 0.0

        return IntentMatch(intent=best_intent, confidence=round(confidence, 2), matched_phrases=best_matches)
