import time
import os
import duckdb
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.research.base import ResearchProvider, ResearchResult
from src.evidence.models import EvidenceItem

class SearchTrendsProvider(ResearchProvider):
    """
    Search demand trends provider.
    Interfaces with verified Google Trends historical series in DuckDB.
    """

    def __init__(self, db_path: str = "data/processed/brandsignal.duckdb"):
        super().__init__(politeness_delay_sec=0.5)
        self.db_path = db_path

    @property
    def name(self) -> str:
        return "trends"

    @property
    def is_available(self) -> bool:
        return os.path.exists(self.db_path)

    @property
    def status_description(self) -> str:
        if self.is_available:
            return "Active (Verified 53-Week Google Trends Dataset in DuckDB)"
        return "Unavailable (DuckDB database not found)"

    def search(self, brand_id_or_term: str, **kwargs) -> ResearchResult:
        t0 = time.time()
        if not self.is_available:
            return ResearchResult(
                provider_name=self.name,
                query=brand_id_or_term,
                success=False,
                error_message="DuckDB database file not found"
            )

        evidence_items = []
        try:
            conn = duckdb.connect(self.db_path, read_only=True)
            query = f"""
                SELECT 
                    brand_id,
                    AVG(relative_search_interest) as mean_rsi,
                    MAX(relative_search_interest) as max_rsi,
                    COUNT(*) as observed_weeks
                FROM fact_search_demand
                WHERE brand_id = '{brand_id_or_term}'
                GROUP BY brand_id
            """
            df = conn.execute(query).df()
            conn.close()

            if not df.empty:
                row = df.iloc[0]
                item = EvidenceItem(
                    evidence_id=f"EVID-TREND-{brand_id_or_term.upper()}",
                    source_name="Official Google Trends Export (India, Web Search)",
                    source_type="google_trends",
                    source_url="https://trends.google.com/trends/",
                    collected_at="2026-09-29T00:00:00Z",
                    brand_id=brand_id_or_term,
                    brand_name=brand_id_or_term.title(),
                    metric="mean_relative_search_interest",
                    observation=f"Mean RSI of {row['mean_rsi']:.1f} (Peak: {row['max_rsi']:.0f}) across {int(row['observed_weeks'])} observed weeks",
                    value=float(row['mean_rsi']),
                    confidence=1.0,
                    dataset_name="google_trends_india_12m.csv",
                    raw_reference="fact_search_demand",
                    limitation_note="Google Trends index [0-100] measures relative search interest, not search query volume or sales."
                )
                evidence_items.append(item)

            return ResearchResult(
                provider_name=self.name,
                query=brand_id_or_term,
                success=True,
                evidence_items=evidence_items,
                execution_time_ms=(time.time() - t0) * 1000.0
            )
        except Exception as e:
            return ResearchResult(
                provider_name=self.name,
                query=brand_id_or_term,
                success=False,
                error_message=str(e),
                execution_time_ms=(time.time() - t0) * 1000.0
            )
