import re
import pandas as pd
from typing import List, Dict, Any, Tuple

class StorefrontCleaner:
    """Cleans and standardizes raw storefront variant records into normalized catalog facts."""

    @staticmethod
    def standardize_category(product_type: str, title: str) -> str:
        """Harmonizes idiosyncratic merchant tags and product types into standard footwear categories."""
        combined = f"{str(product_type).lower()} {str(title).lower()}"

        if any(k in combined for k in ["flip flop", "slipper", "slide", "slides", "clogs", "sandal", "sandals"]):
            return "Flip Flop/Slide"
        if any(k in combined for k in ["sneaker", "sneakers", "high top", "low top", "streetwear"]):
            return "Sneakers"
        if any(k in combined for k in ["slip-on", "slip on", "loafer", "loafers", "moccasin"]):
            return "Slip-on/Loafer"
        if any(k in combined for k in ["running", "sports", "athletic", "training", "gym"]):
            return "Running/Athletic"
        if any(k in combined for k in ["oxford", "formal", "derby", "school"]):
            return "Formal/School"
        if any(k in combined for k in ["boot", "boots", "chelsea"]):
            return "Boots"
        
        return "Casual/Other"

    def clean_records(self, raw_records: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, List[Dict[str, Any]], Dict[str, int]]:
        """
        Cleans and transforms raw variant dictionaries into a normalized DataFrame.
        Returns:
            (df_cleaned, rejected_records, stats_summary)
        """
        cleaned_rows: List[Dict[str, Any]] = []
        rejected_rows: List[Dict[str, Any]] = []
        stats = {
            "total_raw": len(raw_records),
            "passed": 0,
            "rejected_missing_ids": 0,
            "rejected_invalid_price": 0,
            "inverted_discount_corrected": 0,
            "duplicates_removed": 0
        }

        seen_keys = set()

        for rec in raw_records:
            # 1. Product & Variant ID completeness
            p_id = rec.get("product_id")
            v_id = rec.get("variant_id")
            if not p_id or not v_id:
                stats["rejected_missing_ids"] += 1
                rejected_rows.append({"record": rec, "reason": "Missing product_id or variant_id"})
                continue

            # 2. Duplicate variant check in single batch
            snap_date = rec.get("snapshot_date")
            key = (snap_date, v_id)
            if key in seen_keys:
                stats["duplicates_removed"] += 1
                rejected_rows.append({"record": rec, "reason": "Duplicate variant_id in snapshot"})
                continue
            seen_keys.add(key)

            # 3. Price validation
            raw_price = rec.get("price")
            try:
                price_val = float(str(raw_price).replace(",", "").strip())
                if price_val <= 0:
                    raise ValueError("Price must be strictly positive")
            except (ValueError, TypeError):
                stats["rejected_invalid_price"] += 1
                rejected_rows.append({"record": rec, "reason": f"Invalid price: {raw_price}"})
                continue

            # 4. Compare-at price validation & inverted discount correction
            raw_compare = rec.get("compare_at_price")
            compare_val = None
            if raw_compare is not None and str(raw_compare).strip() not in ("", "None", "null"):
                try:
                    c_val = float(str(raw_compare).replace(",", "").strip())
                    if c_val >= price_val:
                        compare_val = round(c_val, 2)
                    else:
                        # Inverted discount: compare_at < price (merchant error)
                        # Fix per methodology: treat as non-discounted, set compare_val = None
                        stats["inverted_discount_corrected"] += 1
                        compare_val = None
                except (ValueError, TypeError):
                    compare_val = None

            # 5. Discount metrics
            is_discounted = compare_val is not None and compare_val > price_val
            discount_amount = round(compare_val - price_val, 2) if is_discounted else None
            discount_pct = round((discount_amount / compare_val) * 100.0, 2) if (is_discounted and compare_val) else None

            # 6. Standardize category
            category_std = self.standardize_category(rec.get("product_type", ""), rec.get("product_title", ""))

            # 7. Availability boolean
            avail_raw = rec.get("available")
            is_available = bool(avail_raw) if avail_raw is not None else False

            cleaned_rows.append({
                "snapshot_date": snap_date,
                "variant_id": int(v_id),
                "brand_id": rec.get("brand"),
                "product_id": int(p_id),
                "product_title": str(rec.get("product_title", "")).strip(),
                "product_type_raw": str(rec.get("product_type", "")).strip() if rec.get("product_type") else None,
                "category_std": category_std,
                "sku": str(rec.get("sku", "")).strip() if rec.get("sku") else None,
                "variant_title": str(rec.get("variant_title", "")).strip() if rec.get("variant_title") else None,
                "selling_price_inr": round(price_val, 2),
                "compare_at_price_inr": compare_val,
                "is_discounted": is_discounted,
                "discount_amount_inr": discount_amount,
                "discount_pct": discount_pct,
                "is_available": is_available,
                "sku_created_at": rec.get("created_at"),
                "collection_timestamp": rec.get("collection_timestamp"),
                "raw_payload_ref": rec.get("raw_payload_ref")
            })

        stats["passed"] = len(cleaned_rows)
        df_cleaned = pd.DataFrame(cleaned_rows)
        return df_cleaned, rejected_rows, stats
