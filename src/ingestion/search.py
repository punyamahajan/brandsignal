import os
import glob
import json
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional

class GoogleTrendsIngestor:
    """
    Ingestor for official Google Trends comparison exports.
    Adheres strictly to zero synthetic data: if no official export is provided,
    marks status as PENDING_MANUAL_REFRESH without generating fake observations.
    """

    def __init__(self, raw_search_dir: str = "data/raw/search", base_dir: str = "."):
        self.raw_search_dir = os.path.join(base_dir, raw_search_dir)
        self.base_dir = base_dir

    def scan_and_ingest(
        self,
        cohort_terms: List[str],
        brand_term_mapping: Dict[str, str],
        geography: str = "IN"
    ) -> Tuple[str, List[Dict[str, Any]], Optional[str], Optional[str]]:
        """
        Scans data/raw/search for official CSV export and metadata manifest.
        Returns:
            (status, records, raw_file_ref, message)
        """
        if not os.path.exists(self.raw_search_dir):
            os.makedirs(self.raw_search_dir, exist_ok=True)

        # Look for multiTimeline*.csv or trends*.csv
        csv_candidates = glob.glob(os.path.join(self.raw_search_dir, "**", "*.csv"), recursive=True)
        if not csv_candidates:
            msg = (
                "Automated Google Trends retrieval is restricted by rate limits (HTTP 429). "
                "Official manual CSV export required. No official export found in data/raw/search/. "
                "Preserving empty schema without synthetic data generation."
            )
            return "PENDING_MANUAL_REFRESH", [], None, msg

        # Sort to find latest
        latest_csv = max(csv_candidates, key=os.path.getmtime)
        rel_csv_path = os.path.relpath(latest_csv, self.base_dir).replace("\\", "/")

        try:
            # Google Trends exports have preamble rows; skip until line starts with "Week" or contains date format
            with open(latest_csv, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            header_idx = None
            for idx, line in enumerate(lines):
                if line.strip().startswith("Week") or line.strip().startswith("Day"):
                    header_idx = idx
                    break

            if header_idx is None:
                return "FAILED", [], rel_csv_path, f"Could not find 'Week' header row in {latest_csv}"

            df = pd.read_csv(latest_csv, skiprows=header_idx)
            # Standardize date column
            date_col = df.columns[0]
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df = df.dropna(subset=[date_col])

            # Process term columns
            collection_ts = datetime.now(timezone.utc).isoformat()
            records: List[Dict[str, Any]] = []

            # Map columns to brand IDs
            col_brand_map = {}
            for col in df.columns[1:]:
                clean_col = col.split(":")[0].strip()
                for brand_id, term in brand_term_mapping.items():
                    if term.lower() in clean_col.lower():
                        col_brand_map[col] = (brand_id, term)
                        break

            for _, row in df.iterrows():
                week_date = row[date_col].strftime("%Y-%m-%d")
                
                # First pass: collect raw relative search interest values
                week_values = {}
                for col, (b_id, term) in col_brand_map.items():
                    val_raw = str(row[col]).strip()
                    val = 0 if val_raw in ("<1", "") else int(float(val_raw))
                    week_values[b_id] = (term, val)

                # Compute cohort sum for derived cohort_relative_search_share
                total_cohort_interest = sum(v[1] for v in week_values.values())

                for b_id, (term, val) in week_values.items():
                    share = (val / total_cohort_interest * 100.0) if total_cohort_interest > 0 else 0.0
                    records.append({
                        "week_start_date": week_date,
                        "brand_id": b_id,
                        "geography": geography,
                        "search_term": term,
                        "relative_search_interest": val,
                        "cohort_relative_search_share": round(share, 2),
                        "collection_timestamp": collection_ts,
                        "raw_file_ref": rel_csv_path
                    })

            return "SUCCESS", records, rel_csv_path, f"Successfully parsed {len(records)} weekly search records."

        except Exception as e:
            return "FAILED", [], rel_csv_path, f"Error parsing Google Trends CSV: {str(e)}"
