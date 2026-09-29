import os
import json
import time
import urllib.request
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional

class TrancoIngestor:
    """Ingestor for the official Tranco Top-1M List research API."""

    def __init__(
        self,
        api_template: str = "https://tranco-list.eu/api/ranks/domain/{domain}",
        user_agent: str = "BrandSignalValidator/1.0 (academic/research; contact@brandsignal.dev)",
        timeout: int = 15,
        politeness_delay: float = 1.0,
        raw_base_dir: str = "data/raw/tranco",
        base_dir: str = "."
    ):
        self.api_template = api_template
        self.user_agent = user_agent
        self.timeout = timeout
        self.politeness_delay = politeness_delay
        self.raw_base_dir = os.path.join(base_dir, raw_base_dir)
        self.base_dir = base_dir

    def fetch_domain_rank(
        self,
        brand_id: str,
        domain: str,
        observation_date: Optional[str] = None
    ) -> Tuple[int, Optional[Dict[str, Any]], Optional[str], Optional[str]]:
        """
        Queries Tranco research API for a domain, saves raw JSON payload,
        and returns the latest rank observation record.
        """
        if observation_date is None:
            observation_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        collection_ts = datetime.now(timezone.utc).isoformat()
        tranco_raw_dir = os.path.join(self.raw_base_dir, observation_date)
        os.makedirs(tranco_raw_dir, exist_ok=True)

        url = self.api_template.format(domain=domain)
        headers = {"User-Agent": self.user_agent}
        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                raw_bytes = resp.read()
                data = json.loads(raw_bytes.decode("utf-8"))

                # 1. Preserve raw response
                raw_filename = f"{brand_id}_{domain}.json"
                raw_filepath = os.path.join(tranco_raw_dir, raw_filename)
                with open(raw_filepath, "wb") as f:
                    f.write(raw_bytes)
                rel_raw_ref = os.path.relpath(raw_filepath, self.base_dir).replace("\\", "/")

                # 2. Extract latest rank
                ranks = data.get("ranks", [])
                if not ranks:
                    return status, None, rel_raw_ref, f"Domain {domain} not in Tranco top 1M list"

                latest_rank_info = ranks[0]
                rank_val = latest_rank_info.get("rank")
                rank_date = latest_rank_info.get("date", observation_date)

                record = {
                    "observation_date": rank_date,
                    "brand_id": brand_id,
                    "domain": domain,
                    "tranco_global_rank": rank_val,
                    "collection_timestamp": collection_ts
                }
                return status, record, rel_raw_ref, None

        except Exception as e:
            http_status = getattr(e, "code", 500)
            return http_status, None, None, str(e)
