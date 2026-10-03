import re
import difflib
from typing import Dict, Any, List, Optional, Set, Tuple

# Canonical brand definitions and normalization mapping
CANONICAL_BRANDS = {
    "neemans": "Neeman's",
    "baccabucci": "Bacca Bucci",
    "elevarsports": "Elevar Sports",
    "plaeto": "Plaeto"
}

BRAND_ALIASES = {
    # Neeman's
    "neemans": "neemans",
    "neeman": "neemans",
    "neeman's": "neemans",
    "neemans shoe": "neemans",
    "neemans shoes": "neemans",
    # Bacca Bucci
    "baccabucci": "baccabucci",
    "bacca bucci": "baccabucci",
    "bacca": "baccabucci",
    "bucci": "baccabucci",
    # Elevar Sports
    "elevarsports": "elevarsports",
    "elevar sports": "elevarsports",
    "elevar": "elevarsports",
    "elevar sport": "elevarsports",
    # Plaeto
    "plaeto": "plaeto",
    "plato": "plaeto",
    "pleato": "plaeto"
}

SELF_REFERENCES = {"my brand", "our brand", "my company", "our company", "me", "us", "we", "my store", "our store"}
COHORT_REFERENCES = {"competitors", "comparison", "cohort", "everyone", "all brands", "others", "the other brands", "peers"}

METRIC_KEYWORDS = {
    "assortment": [
        "product", "products", "style", "styles", "breadth", "catalog", "assortment",
        "sku", "skus", "variant", "variants", "options", "depth", "density", "variant density"
    ],
    "pricing": [
        "price", "prices", "pricing", "cost", "expensive", "cheaper", "cheap", "median price",
        "ppi", "positioning", "price positioning", "iqr", "spread", "distribution", "tier"
    ],
    "discounting": [
        "discount", "discounts", "discounting", "markdown", "markdowns", "promo", "promotions",
        "sale", "on sale", "discount depth", "discount ratio", "cut", "off"
    ],
    "search": [
        "search", "searches", "trends", "google trends", "interest", "attention", "volume",
        "popularity", "demand", "traffic", "query", "queries", "spike", "spikes", "momentum"
    ],
    "category": [
        "category", "categories", "sneaker", "sneakers", "running", "athletic", "boots",
        "flip flop", "slide", "slides", "slip-on", "loafer", "formal", "school", "casual"
    ],
    "domain": [
        "tranco", "rank", "ranking", "website", "domain", "traffic rank", "global rank"
    ]
}

TIME_KEYWORDS = {
    "latest": ["today", "latest", "current", "snapshot", "now", "present"],
    "recent": ["recently", "recent", "lately", "last few weeks", "last month"],
    "12m": ["past year", "last year", "12 months", "last 12 months", "12-month", "12-months", "12m", "53 weeks", "over time", "historically"]
}

class EntityResolver:
    """
    Deterministic Entity Recognition and Normalization Engine.
    Resolves brands, metrics, and time periods using exact token matching,
    regex aliases, and strict Levenshtein normalization without any LLM.
    """

    @staticmethod
    def normalize_brand_name(raw_name: str) -> Optional[str]:
        """Resolves raw input string or alias to canonical brand_id or None."""
        cleaned = raw_name.lower().strip()
        if cleaned in BRAND_ALIASES:
            return BRAND_ALIASES[cleaned]
        if cleaned in CANONICAL_BRANDS:
            return cleaned
        matches = difflib.get_close_matches(cleaned, BRAND_ALIASES.keys(), n=1, cutoff=0.75)
        if matches:
            return BRAND_ALIASES[matches[0]]
        return None

    @staticmethod
    def extract_brands(text: str, default_target_brand: Optional[str] = "baccabucci") -> Tuple[Optional[str], List[str]]:
        """
        Extracts mentioned brands from user input in order of occurrence.
        Returns: (target_brand_id, comparison_brand_ids)
        """
        cleaned = text.lower().strip()
        cleaned_words = re.findall(r"\b[a-z0-9']+\b", cleaned)

        detected_matches: List[Tuple[int, str]] = []

        # 1. Exact alias multi-word matching with start position
        for alias, brand_id in BRAND_ALIASES.items():
            pattern = r"\b" + re.escape(alias) + r"\b"
            for m in re.finditer(pattern, cleaned):
                detected_matches.append((m.start(), brand_id))

        # 2. Fuzzy fallback matching for single words (e.g. typos like "neemns", "plaetoo")
        if not detected_matches:
            for word in cleaned_words:
                matches = difflib.get_close_matches(word, BRAND_ALIASES.keys(), n=1, cutoff=0.85)
                if matches:
                    idx = cleaned.find(word)
                    detected_matches.append((idx, BRAND_ALIASES[matches[0]]))

        # Sort by start position to preserve natural syntax order (Target vs Comparison)
        detected_matches.sort(key=lambda x: x[0])
        unique_detected: List[str] = []
        for _, bid in detected_matches:
            if bid not in unique_detected:
                unique_detected.append(bid)

        # 3. Check for self-reference ("my brand", "we", "us")
        has_self_ref = any(re.search(r"\b" + re.escape(sr) + r"\b", cleaned) for sr in SELF_REFERENCES)

        # Determine target vs comparison
        target_brand: Optional[str] = None
        comparison_brands: List[str] = []

        if has_self_ref:
            target_brand = default_target_brand
            # Any explicitly mentioned brands are comparison brands
            comparison_brands = [b for b in unique_detected if b != target_brand]
        elif len(unique_detected) == 1:
            single_b = unique_detected[0]
            if default_target_brand and single_b != default_target_brand:
                target_brand = default_target_brand
                comparison_brands = [single_b]
            else:
                target_brand = single_b
        elif len(unique_detected) >= 2:
            target_brand = unique_detected[0]
            comparison_brands = unique_detected[1:]
        else:
            # No specific brand mentioned -> fallback to target or cohort
            target_brand = default_target_brand

        # If comparison brands is empty and user explicitly mentioned competitors/cohort/peers, include other brands
        has_cohort_ref = any(re.search(r"\b" + re.escape(cr) + r"\b", cleaned) for cr in COHORT_REFERENCES)
        if not comparison_brands and has_cohort_ref:
            if target_brand:
                comparison_brands = [b for b in CANONICAL_BRANDS if b != target_brand]
            else:
                comparison_brands = list(CANONICAL_BRANDS.keys())

        return target_brand, comparison_brands

    @staticmethod
    def extract_metrics(text: str) -> List[str]:
        """
        Detects relevant metric dimensions referenced in the query.
        Returns a list of metric categories: ['assortment', 'pricing', 'discounting', 'search', 'category', 'domain']
        """
        cleaned = text.lower()
        matched_categories: List[str] = []

        for category, keywords in METRIC_KEYWORDS.items():
            for kw in keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", cleaned):
                    matched_categories.append(category)
                    break

        return matched_categories if matched_categories else ["general"]

    @staticmethod
    def extract_time_period(text: str) -> str:
        """
        Extracts temporal scope: 'latest', 'recent', or 'annual'.
        """
        cleaned = text.lower()
        for scope, keywords in TIME_KEYWORDS.items():
            for kw in keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", cleaned):
                    return scope
        return "latest"

    @staticmethod
    def get_canonical_name(brand_id: str) -> str:
        """Resolves brand_id to official display name."""
        return CANONICAL_BRANDS.get(brand_id, brand_id.replace("_", " ").title())
