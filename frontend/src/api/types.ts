export interface BrandContext {
  brand_name?: string | null;
  industry?: string | null;
  category?: string | null;
  geography: string;
  price_positioning?: string | null;
  customer_segment?: string | null;
  is_demo_vertical: boolean;
  demo_brand_id?: string | null;
  competitors: string[];
  status: string;
  summary: string;
  is_established: boolean;
}

export interface EvidenceItem {
  evidence_id: string;
  source_name: string;
  source_type: string;
  source_url?: string | null;
  collected_at: string;
  brand_id?: string | null;
  brand_name?: string | null;
  metric: string;
  observation: string;
  value?: any;
  raw_reference?: string | null;
  dataset_name?: string | null;
  limitation_note?: string | null;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  cited_evidence?: EvidenceItem[];
  suggested_followups?: string[];
  visual_navigation_target?: string | null;
  visual_navigation_label?: string | null;
  why_are_you_saying_this_md?: string;
  is_clarification?: boolean;
}

export interface MarketBrandSummary {
  brand_id: string;
  brand_name: string;
  active_styles: number;
  active_skus: number;
  median_price: number;
  ppi: number;
  discount_ratio: number;
  tranco_rank?: number | null;
}

export interface CohortBenchmarks {
  total_active_products: number;
  total_active_skus: number;
  median_products: number;
  median_skus: number;
  median_variant_density: number;
  median_price_inr: number;
  median_price_iqr_inr: number;
  median_discount_ratio: number;
  median_discount_depth: number;
}

export interface MarketSnapshotData {
  category: string;
  snapshot_date: string;
  benchmarks: CohortBenchmarks;
  brands: MarketBrandSummary[];
}

export interface BrandComparisonData {
  brand_a: {
    id: string;
    name: string;
    styles: number;
    skus: number;
    variant_density: number;
    median_price: number;
    ppi: number;
    discount_ratio: number;
    median_discount_depth: number;
    avg_cohort_share: number;
  };
  brand_b: {
    id: string;
    name: string;
    styles: number;
    skus: number;
    variant_density: number;
    median_price: number;
    ppi: number;
    discount_ratio: number;
    median_discount_depth: number;
    avg_cohort_share: number;
  };
  benchmarks: CohortBenchmarks;
}

export interface PriceComparisonData {
  target: {
    id: string;
    name: string;
    median_price: number;
    price_iqr: number;
    ppi: number;
    cohort_median_price: number;
  };
  comparisons: Array<{
    brand_id: string;
    brand_name: string;
    median_price: number;
    price_iqr: number;
    ppi: number;
  }>;
}

export interface AssortmentComparisonData {
  target: {
    id: string;
    name: string;
    styles: number;
    skus: number;
    variant_density: number;
  };
  comparisons: Array<{
    brand_id: string;
    brand_name: string;
    styles: number;
    skus: number;
    variant_density: number;
  }>;
}

export interface GapsData {
  target_brand: {
    id: string;
    name: string;
    styles: number;
    variant_density: number;
  };
  missing_categories: string[];
  style_breadth_difference: number;
  max_peer_styles: number;
  variant_density_difference: number;
}

export interface SearchTrendData {
  target_brand: {
    id: string;
    name: string;
  };
  search_stats: {
    mean_rsi: number;
    median_rsi: number;
    max_rsi: number;
    min_rsi: number;
    peak_week: string;
    avg_cohort_share: number;
  };
}

export interface SearchSpikeItem {
  brand_id: string;
  brand_name: string;
  week_str: string;
  rsi_change: number;
  prev_rsi: number;
  current_rsi: number;
}
