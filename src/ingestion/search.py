import os
import glob
import json
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional, Set

from src.features.search_features import SearchFeatureExtractor

class GoogleTrendsIngestor:
    """
    Ingestor for official Google Trends comparison exports.
    Strictly enforces zero synthetic/fabricated data:
    - Ingests only verified official Google Trends CSV exports.
    - Preserves relative search interest exactly as exported.
    - Handles Google Trends '<1' (low-volume / sub-unit interest) and missing values
      according to Google Trends semantics without inventing arbitrary numbers (e.g. 0 or 0.5).
    - Derives cohort_relative_search_share strictly after validating that all four cohort
      brands are represented for each comparable period with definite numeric values.
    - Does NOT interpret Google Trends relative search interest as absolute search volume,
      revenue, market share, or number of queries.
    """

    def __init__(self, raw_search_dir: str = "data/raw/search", base_dir: str = "."):
        self.raw_search_dir = os.path.join(base_dir, raw_search_dir)
        self.base_dir = base_dir

    def load_metadata_manifest(self, manifest_name: str = "search_metadata.json") -> Optional[Dict[str, Any]]:
        """Loads the metadata manifest documenting collection parameters if available."""
        manifest_path = os.path.join(self.raw_search_dir, manifest_name)
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def scan_and_ingest(
        self,
        cohort_terms: List[str],
        brand_term_mapping: Dict[str, str],
        geography: str = "IN"
    ) -> Tuple[str, List[Dict[str, Any]], Optional[str], str]:
        """
        Scans data/raw/search for official Google Trends CSV export and metadata manifest.
        Returns:
            (status, records, raw_file_ref, message)
        """
        if not os.path.exists(self.raw_search_dir):
            os.makedirs(self.raw_search_dir, exist_ok=True)

        # Look for multiTimeline*.csv, google_trends*.csv, or any .csv in raw search dir
        csv_candidates = glob.glob(os.path.join(self.raw_search_dir, "**", "*.csv"), recursive=True)
        if not csv_candidates:
            msg = (
                "Official manual Google Trends CSV export required (automated collection blocked by HTTP 429). "
                "No CSV export found in data/raw/search/. Preserving empty schema without synthetic data."
            )
            return "PENDING_MANUAL_REFRESH", [], None, msg

        # Select latest CSV file
        latest_csv = max(csv_candidates, key=os.path.getmtime)
        return self.parse_csv_file(
            csv_path=latest_csv,
            cohort_terms=cohort_terms,
            brand_term_mapping=brand_term_mapping,
            geography=geography
        )

    def parse_csv_file(
        self,
        csv_path: str,
        cohort_terms: List[str],
        brand_term_mapping: Dict[str, str],
        geography: str = "IN"
    ) -> Tuple[str, List[Dict[str, Any]], Optional[str], str]:
        """
        Parses and validates an official Google Trends CSV export file.
        """
        try:
            rel_csv_path = os.path.relpath(csv_path, self.base_dir).replace("\\", "/")
        except ValueError:
            rel_csv_path = os.path.abspath(csv_path).replace("\\", "/")

        try:
            # 1. Skip Google Trends preamble lines (e.g. "Category: All categories", blank lines)
            with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            header_idx = None
            for idx, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("Week") or stripped.startswith("Day"):
                    header_idx = idx
                    break

            if header_idx is None:
                return "FAILED", [], rel_csv_path, f"Header row starting with 'Week' or 'Day' not found in {rel_csv_path}"

            df = pd.read_csv(csv_path, skiprows=header_idx)
            if df.empty or len(df.columns) < 2:
                return "FAILED", [], rel_csv_path, f"CSV contains no data columns or rows in {rel_csv_path}"

            # 2. Date column normalization (YYYY-MM-DD standard format)
            date_col = df.columns[0]
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df = df.dropna(subset=[date_col])

            # 3. Validate expected brand terms
            # Google Trends column format: "<Term>: (<Region>)" e.g. "Neeman's: (India)"
            col_brand_map: Dict[str, Tuple[str, str]] = {}
            unmatched_cols = []

            for col in df.columns[1:]:
                clean_col = col.split(":")[0].strip()
                matched = False
                for brand_id, term in brand_term_mapping.items():
                    # Match normalized terms (resilient to apostrophes and casing)
                    norm_col = clean_col.replace("'", "").replace("’", "").lower()
                    norm_term = term.replace("'", "").replace("’", "").lower()
                    if norm_col == norm_term or norm_term in norm_col:
                        col_brand_map[col] = (brand_id, term)
                        matched = True
                        break
                if not matched:
                    unmatched_cols.append(col)

            # Assert that all expected brands are present
            mapped_brand_ids = {b_id for b_id, _ in col_brand_map.values()}
            expected_brand_ids = set(brand_term_mapping.keys())
            missing_brand_ids = expected_brand_ids - mapped_brand_ids

            if missing_brand_ids:
                missing_terms = [brand_term_mapping[b] for b in missing_brand_ids]
                return (
                    "FAILED",
                    [],
                    rel_csv_path,
                    f"Google Trends validation failed: missing expected brand terms {missing_terms} in {rel_csv_path}"
                )

            # 4. Extract and normalize weekly observations
            collection_ts = datetime.now(timezone.utc).isoformat()
            raw_records: List[Dict[str, Any]] = []
            seen_observations: Set[Tuple[str, str]] = set()
            duplicates_count = 0

            for _, row in df.iterrows():
                week_date = row[date_col].strftime("%Y-%m-%d")

                for col, (b_id, term) in col_brand_map.items():
                    obs_key = (week_date, b_id)
                    if obs_key in seen_observations:
                        duplicates_count += 1
                        continue
                    seen_observations.add(obs_key)

                    val_raw = str(row[col]).strip() if pd.notna(row[col]) else ""

                    # Google Trends Semantics handling for <1 and missing
                    # '<1' means detectable non-zero search interest below 1% of peak.
                    # Do NOT replace with 0 or 0.5; preserve as NULL numeric, '<1' raw, is_low_volume=True
                    if val_raw == "<1":
                        num_val = None
                        is_low_vol = True
                        raw_str = "<1"
                    elif val_raw in ("", "nan", "null", "none"):
                        num_val = None
                        is_low_vol = False
                        raw_str = ""
                    else:
                        try:
                            num_val = int(round(float(val_raw)))
                            is_low_vol = False
                            raw_str = str(num_val)
                        except ValueError:
                            num_val = None
                            is_low_vol = False
                            raw_str = val_raw

                    raw_records.append({
                        "week_start_date": week_date,
                        "brand_id": b_id,
                        "geography": geography,
                        "search_term": term,
                        "relative_search_interest_raw": raw_str,
                        "relative_search_interest": num_val,
                        "is_low_volume": is_low_vol,
                        "cohort_relative_search_share": None,  # Derived in step 5
                        "collection_timestamp": collection_ts,
                        "raw_file_ref": rel_csv_path
                    })

            # 5. Derive cohort_relative_search_share
            # cohort_relative_search_share = brand relative_search_interest / sum(cohort relative_search_interest) * 100
            # ONLY derived when all 4 cohort brands are present for that week with definite numeric values.
            # If any brand has a low-volume ('<1') or missing value, cohort share is preserved as None (NULL).
            records_by_week: Dict[str, List[Dict[str, Any]]] = {}
            for rec in raw_records:
                records_by_week.setdefault(rec["week_start_date"], []).append(rec)

            final_records: List[Dict[str, Any]] = []
            successful_share_weeks = 0
            low_volume_weeks = 0

            for week_date, week_recs in records_by_week.items():
                week_brands = {r["brand_id"] for r in week_recs}
                all_brands_present = expected_brand_ids.issubset(week_brands)
                has_low_volume = any(r["is_low_volume"] for r in week_recs)
                has_missing_numeric = any(r["relative_search_interest"] is None for r in week_recs)

                if has_low_volume:
                    low_volume_weeks += 1

                if all_brands_present and not has_low_volume and not has_missing_numeric:
                    cohort_total = sum(r["relative_search_interest"] for r in week_recs if r["relative_search_interest"] is not None)
                    successful_share_weeks += 1
                    for r in week_recs:
                        if cohort_total > 0 and r["relative_search_interest"] is not None:
                            r["cohort_relative_search_share"] = round(
                                (r["relative_search_interest"] / cohort_total) * 100.0, 2
                            )
                        else:
                            r["cohort_relative_search_share"] = 0.0
                else:
                    # Incomplete cohort or sub-unit interval (<1) present; preserve as None
                    for r in week_recs:
                        r["cohort_relative_search_share"] = None

                final_records.extend(week_recs)

            msg = (
                f"Successfully parsed {len(final_records)} observations across {len(records_by_week)} weeks from {rel_csv_path}. "
                f"Cohort relative search share calculated for {successful_share_weeks} weeks. "
                f"Low-volume (<1) sub-unit observations preserved in {low_volume_weeks} weeks without invented values."
            )
            if duplicates_count > 0:
                msg += f" Removed {duplicates_count} duplicate observations."

            return "SUCCESS", final_records, rel_csv_path, msg

        except Exception as e:
            return "FAILED", [], rel_csv_path, f"Error parsing Google Trends CSV {rel_csv_path}: {str(e)}"
