import pandas as pd
from typing import Dict, Any

class AssortmentFeatureExtractor:
    """Extracts descriptive assortment, catalog depth, and category mix features."""

    @staticmethod
    def compute_assortment_summary(df_brand: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates core assortment statistics for a single brand catalog snapshot.
        
        Metrics:
        1. active_product_count: Unique active parent product styles (product_id).
        2. active_sku_count: Distinct purchasable product variants/SKUs (variant_id).
        3. variant_density: active_sku_count / active_product_count (guarded against div by zero).
        """
        if df_brand.empty:
            return {
                "active_product_count": 0,
                "active_sku_count": 0,
                "variant_density": 0.0,
                "in_stock_ratio": 0.0,
                "category_share_pct": {}
            }

        total_skus = len(df_brand)
        unique_products = int(df_brand["product_id"].nunique()) if "product_id" in df_brand.columns else 0
        variant_density = round(total_skus / unique_products, 2) if unique_products > 0 else 0.0

        # Category share breakdown across standardized categories
        category_share = {}
        if "category_std" in df_brand.columns and not df_brand["category_std"].empty:
            cat_counts = df_brand["category_std"].value_counts(normalize=True) * 100.0
            category_share = {str(cat): round(float(pct), 2) for cat, pct in cat_counts.items()}

        in_stock_count = int(df_brand["is_available"].sum()) if "is_available" in df_brand.columns else 0
        in_stock_ratio = round(in_stock_count / total_skus, 4) if total_skus > 0 else 0.0

        return {
            "active_product_count": unique_products,
            "active_sku_count": total_skus,
            "variant_density": variant_density,
            "in_stock_ratio": in_stock_ratio,
            "category_share_pct": category_share
        }
