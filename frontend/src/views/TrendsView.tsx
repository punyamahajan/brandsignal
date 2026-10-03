import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { SearchTrendData, SearchSpikeItem } from '../api/types';
import { MetricCard } from '../components/MetricCard';

const BRANDS = [
  { id: 'baccabucci', name: 'Bacca Bucci' },
  { id: 'neemans', name: "Neeman's" },
  { id: 'elevarsports', name: 'Elevar Sports' },
  { id: 'plaeto', name: 'Plaeto' }
];

export const TrendsView: React.FC = () => {
  const [selectedBrand, setSelectedBrand] = useState('neemans');
  const [trendData, setTrendData] = useState<SearchTrendData | null>(null);
  const [spikes, setSpikes] = useState<SearchSpikeItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    Promise.all([
      api.getTrends(selectedBrand),
      api.getSpikes(5)
    ])
      .then(([tRes, sRes]) => {
        if (isMounted) {
          setTrendData(tRes.data);
          setSpikes(sRes.data.spikes);
          setLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) setLoading(false);
      });

    return () => { isMounted = false; };
  }, [selectedBrand]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header & Brand Selector */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <div className="title-xl">Search Attention & Momentum Lens</div>
          <div className="subtitle">
            Official 53-week Google Trends series (Sep 2025 – Sep 2026, India Web Search) tracking relative query interest and observed fluctuations.
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#ffffff', border: '1px solid #cbd5e1', padding: '6px 12px', borderRadius: '4px' }}>
          <label style={{ fontSize: '0.74rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Focus Brand:</label>
          <select
            value={selectedBrand}
            onChange={(e) => setSelectedBrand(e.target.value)}
            style={{ border: 'none', background: 'transparent', fontSize: '0.82rem', fontWeight: 700, color: '#0f172a', outline: 'none' }}
          >
            {BRANDS.map(b => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </select>
        </div>
      </div>

      {loading && <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>Loading Google Trends series...</div>}

      {trendData && !loading && (
        <>
          {/* KPI Summary Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
            <MetricCard
              label="Annual Mean RSI"
              value={`${trendData.search_stats.mean_rsi.toFixed(1)} / 100`}
              subtext="Normalized 53-week search interest"
              badge="Google Trends"
            />
            <MetricCard
              label="Peak Query Attention"
              value={`Index ${trendData.search_stats.max_rsi}`}
              subtext={`Recorded during week of ${trendData.search_stats.peak_week}`}
              badge="Peak"
              badgeType="blue"
            />
            <MetricCard
              label="Average Cohort Search Share"
              value={`${trendData.search_stats.avg_cohort_share.toFixed(1)}%`}
              subtext="Share of cohort attention across 50 comparable weeks"
              badge="Cohort Share"
              badgeType="amber"
            />
            <MetricCard
              label="Median RSI"
              value={`${trendData.search_stats.median_rsi.toFixed(1)}`}
              subtext="50th percentile weekly interest"
              badge="Baseline"
            />
          </div>

          {/* Observed Week-over-Week Search Movements (|Δ| ≥ 5) */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <div className="card-header" style={{ marginBottom: 0 }}>
                Observed Week-over-Week Search Movements (|Δ| ≥ 5 RSI)
              </div>
              <span className="badge badge-blue">
                {spikes.length} Fluctuations Detected
              </span>
            </div>
            <div style={{ fontSize: '0.78rem', color: '#64748b', marginBottom: '14px' }}>
              Significant weekly shifts in relative query interest. Descriptive only; BrandSignal does not attribute unverified external causes.
            </div>

            <table className="data-table">
              <thead>
                <tr>
                  <th>Brand Name</th>
                  <th>Week Starting</th>
                  <th>WoW Change (Δ)</th>
                  <th>Previous RSI</th>
                  <th>Current RSI</th>
                </tr>
              </thead>
              <tbody>
                {spikes.slice(0, 10).map((sp, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600 }}>{sp.brand_name}</td>
                    <td>{sp.week_str}</td>
                    <td style={{
                      fontWeight: 700,
                      color: sp.rsi_change > 0 ? '#15803d' : '#b91c1c'
                    }}>
                      {sp.rsi_change > 0 ? `+${sp.rsi_change}` : sp.rsi_change} pts
                    </td>
                    <td>{sp.prev_rsi.toFixed(0)}</td>
                    <td>{sp.current_rsi.toFixed(0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Methodological Caveat */}
          <div style={{
            background: '#f8fafc',
            border: '1px solid #e2e8f0',
            padding: '14px',
            borderRadius: '4px',
            fontSize: '0.76rem',
            color: '#475569'
          }}>
            <b>Google Trends Measurement Constraints:</b> Values represent normalized query interest indices [0-100], not absolute search volume or sales revenue.
            A value of `&lt;1` indicates search volume existed above zero but fell below the normalization threshold; it is preserved as an unquantified low-volume state, not zero.
          </div>
        </>
      )}
    </div>
  );
};
