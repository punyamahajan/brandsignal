import os
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional

class StorefrontIngestor:
    """Polite HTTP client and pagination handler for Shopify public storefronts."""

    def __init__(
        self,
        user_agent: str = "BrandSignalValidator/1.0 (academic/competitive analysis research; contact@brandsignal.dev)",
        timeout: int = 15,
        politeness_delay: float = 2.0,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        raw_base_dir: str = "data/raw/storefront",
        base_dir: str = "."
    ):
        self.user_agent = user_agent
        self.timeout = timeout
        self.politeness_delay = politeness_delay
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.raw_base_dir = os.path.join(base_dir, raw_base_dir)
        self.base_dir = base_dir

    def fetch_page(self, url: str) -> Tuple[int, bytes, Dict[str, Any]]:
        """Fetches a single page with retry logic and exponential backoff."""
        headers = {"User-Agent": self.user_agent}
        req = urllib.request.Request(url, headers=headers)
        
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    status = resp.status
                    content = resp.read()
                    data = json.loads(content.decode("utf-8"))
                    return status, content, data
            except urllib.error.HTTPError as e:
                status = e.code
                if status in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    sleep_time = self.politeness_delay * (self.backoff_factor ** attempt)
                    time.sleep(sleep_time)
                    continue
                raise
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    sleep_time = self.politeness_delay * (self.backoff_factor ** attempt)
                    time.sleep(sleep_time)
                    continue
                raise last_exception

    def ingest_brand_catalog(
        self,
        brand_id: str,
        base_endpoint: str,
        batch_size: int = 250,
        snapshot_date: Optional[str] = None
    ) -> Tuple[int, List[Dict[str, Any]], List[str], Optional[str]]:
        """
        Paginates through a brand's /products.json endpoint, stores raw responses,
        and returns raw extracted variant records.
        """
        if snapshot_date is None:
            snapshot_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        collection_ts = datetime.now(timezone.utc).isoformat()
        brand_raw_dir = os.path.join(self.raw_base_dir, brand_id, snapshot_date)
        os.makedirs(brand_raw_dir, exist_ok=True)

        extracted_records: List[Dict[str, Any]] = []
        raw_saved_files: List[str] = []
        page = 1
        last_http_status = 200
        error_msg = None

        while True:
            url = f"{base_endpoint}?limit={batch_size}&page={page}"
            try:
                status, raw_bytes, data = self.fetch_page(url)
                last_http_status = status
            except Exception as e:
                error_msg = str(e)
                # If error happens on page 1, the whole run failed
                if page == 1:
                    last_http_status = getattr(e, "code", 500)
                    return last_http_status, extracted_records, raw_saved_files, error_msg
                else:
                    # Partial failure on subsequent page
                    break

            # 1. Preserve unmutated raw response
            raw_filename = f"page_{page}.json"
            raw_filepath = os.path.join(brand_raw_dir, raw_filename)
            with open(raw_filepath, "wb") as f:
                f.write(raw_bytes)
            
            rel_raw_ref = os.path.relpath(raw_filepath, self.base_dir).replace("\\", "/")
            raw_saved_files.append(rel_raw_ref)

            products = data.get("products", [])
            if not products:
                break

            # 2. Extract raw snapshot records
            for p in products:
                p_id = p.get("id")
                p_title = p.get("title")
                p_type = p.get("product_type")
                p_handle = p.get("handle")
                p_created = p.get("created_at")
                p_updated = p.get("updated_at")
                source_url = f"{base_endpoint.replace('/products.json', '')}/products/{p_handle}"

                variants = p.get("variants", [])
                for v in variants:
                    extracted_records.append({
                        "collection_timestamp": collection_ts,
                        "snapshot_date": snapshot_date,
                        "brand": brand_id,
                        "product_id": p_id,
                        "product_title": p_title,
                        "product_type": p_type,
                        "handle": p_handle,
                        "created_at": p_created,
                        "updated_at": p_updated,
                        "sku": v.get("sku"),
                        "variant_id": v.get("id"),
                        "variant_title": v.get("title"),
                        "price": v.get("price"),
                        "compare_at_price": v.get("compare_at_price"),
                        "available": v.get("available"),
                        "source_url": source_url,
                        "raw_payload_ref": rel_raw_ref
                    })

            if len(products) < batch_size:
                # End of paginated catalog
                break

            page += 1
            time.sleep(self.politeness_delay)

        return last_http_status, extracted_records, raw_saved_files, error_msg
