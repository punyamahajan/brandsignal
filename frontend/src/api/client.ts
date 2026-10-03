import type {
  BrandContext,
  EvidenceItem,
  MarketSnapshotData,
  BrandComparisonData,
  PriceComparisonData,
  AssortmentComparisonData,
  GapsData,
  SearchTrendData,
  SearchSpikeItem
} from './types';

const BASE_URL = '/api';

export async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const errorText = await res.text();
    let message = `API request failed with status ${res.status}`;
    try {
      const parsed = JSON.parse(errorText);
      if (parsed.detail) message = parsed.detail;
    } catch {
      if (errorText) message = errorText;
    }
    throw new Error(message);
  }
  return res.json();
}

export const api = {
  // Chat
  async sendChatMessage(message: string, sessionId: string = 'default', brandContext?: Partial<BrandContext>) {
    return fetchJson<{
      session_id: string;
      narrative: string;
      brand_context: BrandContext;
      cited_evidence: EvidenceItem[];
      suggested_followups: string[];
      visual_navigation_target?: string | null;
      visual_navigation_label?: string | null;
      why_are_you_saying_this_md: string;
      is_clarification: boolean;
    }>(`${BASE_URL}/chat/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId, brand_context: brandContext })
    });
  },

  // Context
  async getContext(sessionId: string = 'default'): Promise<BrandContext> {
    return fetchJson<BrandContext>(`${BASE_URL}/context/${sessionId}`);
  },

  async updateContext(sessionId: string = 'default', context: Partial<BrandContext>): Promise<BrandContext> {
    return fetchJson<BrandContext>(`${BASE_URL}/context/${sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(context)
    });
  },

  async resetContext(sessionId: string = 'default') {
    return fetchJson<{ status: string; message: string }>(`${BASE_URL}/context/${sessionId}/reset`, {
      method: 'POST'
    });
  },

  // Analytics
  async getSnapshotDates(): Promise<string[]> {
    return fetchJson<string[]>(`${BASE_URL}/analytics/snapshot-dates`);
  },

  async getCohortBrands(): Promise<Array<{ id: string; name: string }>> {
    return fetchJson<Array<{ id: string; name: string }>>(`${BASE_URL}/analytics/brands`);
  },

  async getMarketSnapshot(category: string = 'D2C Footwear', snapshotDate: string = '2026-09-29'): Promise<{ data: MarketSnapshotData; evidence_ids: string[] }> {
    return fetchJson(`${BASE_URL}/analytics/market?category=${encodeURIComponent(category)}&snapshot_date=${snapshotDate}`);
  },

  async compareBrands(brandA: string, brandB: string, snapshotDate: string = '2026-09-29'): Promise<{ data: BrandComparisonData; evidence_ids: string[] }> {
    return fetchJson(`${BASE_URL}/analytics/compare?brand_a=${brandA}&brand_b=${brandB}&snapshot_date=${snapshotDate}`);
  },

  async getPricing(targetBrand: string = 'baccabucci', snapshotDate: string = '2026-09-29'): Promise<{ data: PriceComparisonData; evidence_ids: string[] }> {
    return fetchJson(`${BASE_URL}/analytics/pricing?target_brand=${targetBrand}&snapshot_date=${snapshotDate}`);
  },

  async getAssortment(targetBrand: string = 'baccabucci', snapshotDate: string = '2026-09-29'): Promise<{ data: AssortmentComparisonData; evidence_ids: string[] }> {
    return fetchJson(`${BASE_URL}/analytics/assortment?target_brand=${targetBrand}&snapshot_date=${snapshotDate}`);
  },

  async getGaps(targetBrand: string = 'baccabucci', snapshotDate: string = '2026-09-29'): Promise<{ data: GapsData; evidence_ids: string[] }> {
    return fetchJson(`${BASE_URL}/analytics/gaps?target_brand=${targetBrand}&snapshot_date=${snapshotDate}`);
  },

  async getTrends(brandId: string): Promise<{ data: SearchTrendData; evidence_ids: string[] }> {
    return fetchJson(`${BASE_URL}/analytics/trends/${brandId}`);
  },

  async getSpikes(minDelta: number = 5): Promise<{ data: { spikes: SearchSpikeItem[]; min_threshold: number }; evidence_ids: string[] }> {
    return fetchJson(`${BASE_URL}/analytics/spikes?min_abs_delta=${minDelta}`);
  },

  async getCategoryMix(brandId: string, snapshotDate: string = '2026-09-29'): Promise<{ data: { brand_id: string; brand_name: string; categories: Array<{ category: string; sku_count: number; share_pct: number }> }; evidence_ids: string[] }> {
    return fetchJson(`${BASE_URL}/analytics/category-mix/${brandId}?snapshot_date=${snapshotDate}`);
  },

  // Evidence
  async getEvidenceItem(evidenceId: string): Promise<EvidenceItem> {
    return fetchJson<EvidenceItem>(`${BASE_URL}/evidence/${evidenceId}`);
  },

  async getSessionEvidence(sessionId: string = 'default'): Promise<EvidenceItem[]> {
    return fetchJson<EvidenceItem[]>(`${BASE_URL}/evidence/session/${sessionId}`);
  },

  async getWhyMarkdown(sessionId: string = 'default'): Promise<{ markdown: string }> {
    return fetchJson<{ markdown: string }>(`${BASE_URL}/evidence/provenance/why-md?session_id=${sessionId}`);
  }
};
