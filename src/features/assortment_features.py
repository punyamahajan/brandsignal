import pandas as pd
from typing import Dict, Any

class AssortmentFeatureExtractor:
    """Extracts descriptive assortment, catalog depth, and category mix features."""

    @staticmethod
    def compute_assortment_summary(df_brand: pd.DataFrame) -> Dict[str, Any]:
        """Calculates core assortment statistics for a single brand catalog snapshot."""
        if df_brand.empty:
            return {}

        total_skus = len(df_brand)
        unique_products = int(df_brand["product_id"].nunique())
        variant_density = round(total_skus / unique_products, 2) if unique_products > 0 else 0.0

        # Category share breakdown
        cat_counts = df_brand["category_std"].value_counts(normalize=True) * 100.0
        category_share = {cat: round(float(pct), 2) for cat, pct in cat_counts.items()}

        # In-stock ratio
        in_stock_count = int(df_brand["is_available"].sum())
        in_stock_ratio = round(in_stock_count / total_skus, 4) if total_skus > 0 else 0.0

        return {
            "active_product_count": unique_products,
            "active_sku_count": total_skus,
            "variant_density": variant_density,
            "in_stock_ratio": in_stock_ratio,
            "category_share_pct": category_share
        }
