from dataclasses import dataclass, field, fields
from typing import Dict, Any, List, Optional, Tuple
import re

# Known demo dataset mapping for the Indian D2C footwear cohort
DEMO_FOOTWEAR_BRANDS = {
    "neemans": "Neeman's",
    "baccabucci": "Bacca Bucci",
    "elevarsports": "Elevar Sports",
    "plaeto": "Plaeto"
}

DEMO_BRAND_ALIASES = {
    "neemans": "neemans",
    "neeman": "neemans",
    "neeman's": "neemans",
    "baccabucci": "baccabucci",
    "bacca bucci": "baccabucci",
    "bacca": "baccabucci",
    "elevarsports": "elevarsports",
    "elevar sports": "elevarsports",
    "elevar": "elevarsports",
    "plaeto": "plaeto",
    "plato": "plaeto"
}

@dataclass
class BrandContext:
    """
    Maintains the structured identity, category, and competitive landscape
    of the user's business across conversational turns.
    No automatic default assumptions (e.g. no hardcoded Footwear, D2C, or India).
    """
    brand_name: Optional[str] = None
    industry: Optional[str] = None
    category: Optional[str] = None
    geography: Optional[str] = None
    business_model: Optional[str] = None  # "D2C", "B2B", "Retail", etc.
    target_customer: Optional[str] = None
    price_positioning: Optional[str] = None
    customer_segment: Optional[str] = None
    is_demo_vertical: bool = False
    demo_brand_id: Optional[str] = None
    competitors: List[str] = field(default_factory=list)
    status: str = "INITIAL"  # "INITIAL" | "ONBOARDING" | "ESTABLISHED"
    conversation_id: Optional[str] = "default"

    def is_established(self) -> bool:
        """Context is considered established once we know the brand and/or its specific category."""
        return bool(self.brand_name or (self.industry and self.category) or self.is_demo_vertical)

    def summary(self) -> str:
        parts = []
        if self.brand_name:
            parts.append(f"Brand: {self.brand_name}")
        if self.industry:
            parts.append(f"Industry: {self.industry}")
        if self.category:
            parts.append(f"Category: {self.category}")
        if self.business_model:
            parts.append(f"Model: {self.business_model}")
        if self.geography:
            parts.append(f"Market: {self.geography}")
        if self.price_positioning:
            parts.append(f"Tier: {self.price_positioning}")
        if self.competitors:
            parts.append(f"Peers: {', '.join(self.competitors)}")
        return " | ".join(parts) if parts else "No brand context established."

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand_name": self.brand_name,
            "industry": self.industry,
            "category": self.category,
            "geography": self.geography,
            "business_model": self.business_model,
            "target_customer": self.target_customer,
            "price_positioning": self.price_positioning,
            "customer_segment": self.customer_segment,
            "is_demo_vertical": self.is_demo_vertical,
            "demo_brand_id": self.demo_brand_id,
            "competitors": self.competitors,
            "status": self.status,
            "conversation_id": self.conversation_id
        }

    def update_from_dict(self, data: Dict[str, Any]) -> "BrandContext":
        """Safely updates only defined dataclass fields from a dictionary."""
        valid_fields = {f.name for f in fields(self)}
        for k, v in data.items():
            if k in valid_fields and v is not None:
                setattr(self, k, v)
        return self


class BrandContextManager:
    """
    Extracts, updates, and manages BrandContext from conversational exchanges.
    Performs deterministic entity extraction with fallback heuristics.
    Never assumes footwear, D2C, or India unless explicitly detected.
    """

    @staticmethod
    def extract_from_text(text: str, current_context: Optional[BrandContext] = None) -> BrandContext:
        ctx = current_context or BrandContext()
        cleaned = text.strip()
        cleaned_lower = cleaned.lower()

        # Check for demo footwear brands explicitly
        matched_demo_id = None
        for alias, bid in DEMO_BRAND_ALIASES.items():
            pattern = r"\b" + re.escape(alias) + r"\b"
            if re.search(pattern, cleaned_lower):
                matched_demo_id = bid
                break

        if matched_demo_id:
            ctx.brand_name = DEMO_FOOTWEAR_BRANDS[matched_demo_id]
            ctx.industry = "Footwear"
            ctx.category = "D2C Footwear"
            ctx.geography = "IN"
            ctx.business_model = "D2C"
            ctx.is_demo_vertical = True
            ctx.demo_brand_id = matched_demo_id
            ctx.competitors = [b_name for b_id, b_name in DEMO_FOOTWEAR_BRANDS.items() if b_id != matched_demo_id]
            ctx.status = "ESTABLISHED"
            return ctx

        # Heuristic 1: Explicit brand name mentions: "called [Name]" or "named [Name]" or "brand is [Name]"
        brand_match = re.search(
            r"(?:called|named|brand is|company is)\s+([A-Z][a-zA-Z0-9'\s]{1,25})(?:\b|\.|\,)",
            cleaned
        )
        if brand_match:
            candidate = brand_match.group(1).strip()
            if candidate.lower() not in {"a", "an", "the", "d2c", "footwear", "stationery", "beverage"}:
                ctx.brand_name = candidate

        # Heuristic 2: Business model extraction (D2C, B2B, Retail)
        if re.search(r"\b(d2c|direct[- ]to[- ]consumer)\b", cleaned_lower):
            ctx.business_model = "D2C"
        elif re.search(r"\b(b2b|wholesale)\b", cleaned_lower):
            ctx.business_model = "B2B"
        elif re.search(r"\b(retail|brick[- ]and[- ]mortar|offline)\b", cleaned_lower):
            ctx.business_model = "Retail"

        # Heuristic 3: Industry extraction
        industry_keywords = {
            "Stationery": ["stationery", "notebooks", "notebook", "pens", "pen", "pencils", "office supplies", "journals", "planners"],
            "Footwear": ["footwear", "shoes", "sneakers", "boots", "sandals", "slippers", "loafers", "running shoes"],
            "Beverages": ["beverage", "beverages", "soda", "soft drink", "soft drinks", "cola", "energy drink", "juice"],
            "Coffee": ["coffee", "roastery", "specialty coffee", "cold brew", "espresso"],
            "Apparel": ["apparel", "clothing", "fashion", "streetwear", "activewear", "jeans", "t-shirts"],
            "Beauty": ["beauty", "cosmetics", "skincare", "personal care", "serum", "sunscreen"],
            "Food": ["food", "snacks", "healthy snacks", "protein bar", "chocolates", "cereal"],
            "Consumer Electronics": ["electronics", "audio", "headphones", "smartwatch", "wearables"]
        }

        for ind, kws in industry_keywords.items():
            if any(re.search(r"\b" + re.escape(kw) + r"\b", cleaned_lower) for kw in kws):
                ctx.industry = ind
                # Extract specific sub-category if mentioned
                for kw in kws:
                    if kw in cleaned_lower and kw.lower() != ind.lower():
                        ctx.category = kw.title()
                        break
                break

        # Heuristic 4: Geography extraction (only set if explicitly stated)
        if re.search(r"\b(india|indian|in)\b", cleaned_lower):
            ctx.geography = "IN"
        elif re.search(r"\b(usa|us|united states|america)\b", cleaned_lower):
            ctx.geography = "US"
        elif re.search(r"\b(uk|united kingdom|britain)\b", cleaned_lower):
            ctx.geography = "UK"

        # Price positioning extraction
        if re.search(r"\b(affordable|budget|mass|value|entry|accessible)\b", cleaned_lower):
            ctx.price_positioning = "Affordable / Value"
        elif re.search(r"\b(premium|luxury|high[- ]end|designer)\b", cleaned_lower):
            ctx.price_positioning = "Premium / High-End"
        elif re.search(r"\b(mid[- ]tier|mid[- ]range|balanced)\b", cleaned_lower):
            ctx.price_positioning = "Mid-Tier"

        # Customer segment / target customer
        if re.search(r"\b(daily|everyday|casual|commuters?)\b", cleaned_lower):
            ctx.customer_segment = "Everyday / Casual"
            ctx.target_customer = "Everyday Consumers"
        elif re.search(r"\b(athletes?|running|sports?|fitness)\b", cleaned_lower):
            ctx.customer_segment = "Athletic / Performance"
            ctx.target_customer = "Athletes & Fitness Enthusiasts"
        elif re.search(r"\b(kids?|youth|children)\b", cleaned_lower):
            ctx.customer_segment = "Youth / Kids"
            ctx.target_customer = "Children & Parents"
        elif re.search(r"\b(students?|academic|school|college)\b", cleaned_lower):
            ctx.customer_segment = "Students"
            ctx.target_customer = "Students & Educators"

        # Update status
        is_est = ctx.is_established() if callable(getattr(ctx, "is_established", None)) else bool(getattr(ctx, "is_established", False))
        if is_est:
            ctx.status = "ESTABLISHED"
        elif ctx.brand_name or ctx.industry:
            ctx.status = "ONBOARDING"
        else:
            ctx.status = "INITIAL"

        return ctx

    @staticmethod
    def get_clarification_question(ctx: BrandContext) -> Optional[str]:
        """Generates a targeted, helpful follow-up question if critical context is missing."""
        if not ctx.brand_name and not ctx.industry:
            return "Tell me about your brand and what you sell, and I'll help you understand your market."
        elif ctx.industry and not ctx.brand_name and not ctx.category:
            return f"What is your brand name, and what specific products in {ctx.industry.lower()} do you focus on?"
        elif ctx.industry and not ctx.geography:
            return f"Which market or geography (e.g., India, US, global) does your {ctx.industry.lower()} brand operate in?"
        elif ctx.brand_name and not ctx.industry:
            return f"What product category or market does **{ctx.brand_name}** operate in?"
        return None
