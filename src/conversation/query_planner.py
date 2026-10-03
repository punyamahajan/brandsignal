from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from src.conversation.intent_engine import IntentEngine, IntentMatch
from src.conversation.entity_resolver import EntityResolver, CANONICAL_BRANDS
from src.conversation.analytics_service import AnalyticsService

@dataclass
class QueryPlan:
    intent: str
    target_brand: Optional[str]
    comparison_brands: List[str]
    metrics: List[str]
    time_period: str
    snapshot_date: str
    confidence: float

@dataclass
class ExecutionResult:
    plan: QueryPlan
    data: Dict[str, Any]
    success: bool
    error: Optional[str] = None

class QueryPlanner:
    """
    Deterministic Query Planner.
    Converts intent and extracted entities into structured, parameter-safe
    analytical execution plans.
    """

    def __init__(self, analytics_service: Optional[AnalyticsService] = None):
        self.analytics_service = analytics_service or AnalyticsService()

    def plan(
        self,
        query: str,
        active_brand_id: Optional[str] = "baccabucci",
        snapshot_date: str = "2026-09-29"
    ) -> QueryPlan:
        """Constructs an executable query plan without executing any SQL."""
        intent_match = IntentEngine.classify(query)
        target_brand, comparison_brands = EntityResolver.extract_brands(query, default_target_brand=active_brand_id)
        metrics = EntityResolver.extract_metrics(query)
        time_period = EntityResolver.extract_time_period(query)

        # Refine target vs comparison if needed
        if not target_brand and active_brand_id:
            target_brand = active_brand_id

        # If comparison brands is empty and intent implies comparison, fill with other brands
        if not comparison_brands and intent_match.intent in [
            "COMPETITOR_COMPARISON", "ASSORTMENT_COMPARISON", "PRICE_COMPARISON",
            "DISCOUNT_COMPARISON", "SEARCH_COMPARISON", "BRAND_DIFFERENCE", "BRAND_MISSING"
        ]:
            if target_brand:
                comparison_brands = [b for b in CANONICAL_BRANDS if b != target_brand]
            else:
                comparison_brands = list(CANONICAL_BRANDS.keys())

        return QueryPlan(
            intent=intent_match.intent,
            target_brand=target_brand,
            comparison_brands=comparison_brands,
            metrics=metrics,
            time_period=time_period,
            snapshot_date=snapshot_date,
            confidence=intent_match.confidence
        )

    def execute(
        self,
        query: str,
        active_brand_id: Optional[str] = "baccabucci",
        snapshot_date: str = "2026-09-29"
    ) -> ExecutionResult:
        """Generates the plan and executes the designated read-only analytical function."""
        plan = self.plan(query, active_brand_id=active_brand_id, snapshot_date=snapshot_date)
        t_brand = plan.target_brand or "baccabucci"
        comp_brands = plan.comparison_brands

        try:
            if plan.intent == "MARKET_OVERVIEW":
                data = self.analytics_service.get_market_overview(plan.snapshot_date)
            elif plan.intent == "COMPETITOR_COMPARISON":
                if comp_brands:
                    # Compare target against first comparison brand, or cohort if multiple
                    if len(comp_brands) == 1:
                        data = self.analytics_service.compare_brands(t_brand, comp_brands[0], plan.snapshot_date)
                    else:
                        data = self.analytics_service.get_brand_differences(t_brand, comp_brands, plan.snapshot_date)
                else:
                    data = self.analytics_service.get_market_overview(plan.snapshot_date)
            elif plan.intent == "ASSORTMENT_COMPARISON" or plan.intent == "CATALOG_SCALE":
                data = self.analytics_service.compare_assortment(t_brand, comp_brands, plan.snapshot_date)
            elif plan.intent == "PRICE_COMPARISON" or plan.intent == "PRICE_POSITIONING":
                data = self.analytics_service.compare_pricing(t_brand, comp_brands, plan.snapshot_date)
            elif plan.intent == "DISCOUNT_COMPARISON" or plan.intent == "PROMOTIONAL_INTENSITY":
                data = self.analytics_service.compare_discounting(t_brand, comp_brands, plan.snapshot_date)
            elif plan.intent == "SEARCH_TREND":
                data = self.analytics_service.get_search_trend(t_brand)
            elif plan.intent == "SEARCH_COMPARISON":
                data = self.analytics_service.compare_search_attention(t_brand, comp_brands)
            elif plan.intent == "RECENT_CHANGE":
                data = {"spikes": self.analytics_service.get_recent_changes(min_abs_delta=5)}
            elif plan.intent == "BRAND_DIFFERENCE":
                data = self.analytics_service.get_brand_differences(t_brand, comp_brands, plan.snapshot_date)
            elif plan.intent == "BRAND_MISSING":
                data = self.analytics_service.get_brand_gaps(t_brand, comp_brands, plan.snapshot_date)
            elif plan.intent == "CATEGORY_MIX":
                data = self.analytics_service.get_category_mix(t_brand, plan.snapshot_date)
            elif plan.intent == "EXPLAIN_METRIC":
                metric_key = plan.metrics[0] if plan.metrics else query
                meta = self.analytics_service.get_metric_definition(metric_key)
                data = {"definition": meta, "query_term": metric_key}
            elif plan.intent == "DATA_AVAILABILITY":
                data = self.analytics_service.get_data_availability()
            elif plan.intent == "HELP":
                data = {"help": True}
            else: # UNKNOWN
                data = {"unknown": True}

            return ExecutionResult(plan=plan, data=data, success=True)
        except Exception as e:
            return ExecutionResult(plan=plan, data={}, success=False, error=str(e))
