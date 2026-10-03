import React, { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, XCircle } from 'lucide-react';
import { api } from '../api/client';
import type { GapsData } from '../api/types';
import { MetricCard } from '../components/MetricCard';

interface GapsViewProps {
  snapshotDate: string;
}

const BRANDS = [
  { id: 'baccabucci', name: 'Bacca Bucci' },
  { id: 'neemans', name: "Neeman's" },
  { id: 'elevarsports', name: 'Elevar Sports' },
  { id: 'plaeto', name: 'Plaeto' }
];

export const GapsView: React.FC<GapsViewProps> = ({ snapshotDate }) => {
  const [selectedBrand, setSelectedBrand] = useState('baccabucci');
  const [data, setData] = useState<GapsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    api.getGaps(selectedBrand, snapshotDate)
      .then(res => {
        if (isMounted) {
          setData(res.data);
          setLoading(false);
        }
      })
      .catch(err => {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => { isMounted = false; };
  }, [selectedBrand, snapshotDate]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header & Target Brand Selector */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <div className="title-xl">Assortment & Category Gap Explorer</div>
          <div className="subtitle">
            Answers "What is my brand missing?" strictly by identifying observable characteristics present among peers but unrepresented in target catalog.
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#ffffff', border: '1px solid #cbd5e1', padding: '6px 12px', borderRadius: '4px' }}>
          <label style={{ fontSize: '0.74rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Target Brand:</label>
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

      {loading && <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>Analyzing catalog gaps...</div>}
      {error && <div style={{ padding: '40px', textAlign: 'center', color: '#dc2626' }}>Error: {error}</div>}

      {data && !loading && (
        <>
          {/* KPI Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
            <MetricCard
              label="Active Styles"
              value={data.target_brand.styles.toLocaleString()}
              subtext={`Peer peak: ${data.max_peer_styles.toLocaleString()} styles`}
              badge="Breadth"
            />
            <MetricCard
              label="Breadth Difference"
              value={data.style_breadth_difference > 0 ? `-${data.style_breadth_difference.toLocaleString()}` : '0'}
              subtext="Styles below highest peer"
              badgeType={data.style_breadth_difference > 0 ? 'amber' : 'green'}
              badge={data.style_breadth_difference > 0 ? 'Delta' : 'Catalog Leader'}
            />
            <MetricCard
              label="Missing Standardized Categories"
              value={data.missing_categories.length}
              subtext={data.missing_categories.length === 0 ? 'Full category coverage' : 'Categories unrepresented'}
              badgeType={data.missing_categories.length > 0 ? 'amber' : 'green'}
              badge="Presence"
            />
            <MetricCard
              label="Variant Density Delta"
              value={`${data.variant_density_difference.toFixed(2)}`}
              subtext="SKUs per style below peer peak"
              badge="Option Depth"
            />
          </div>

          {/* Missing Categories Breakdown */}
          <div className="card">
            <div className="card-header">Unrepresented Product Categories</div>
            <div style={{ fontSize: '0.82rem', color: '#475569', marginBottom: '14px' }}>
              Categories identified in peer catalogs but absent in <b>{data.target_brand.name}</b>'s digital storefront listings:
            </div>

            {data.missing_categories.length === 0 ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#15803d', fontSize: '0.85rem', background: '#f0fdf4', padding: '12px', borderRadius: '4px', border: '1px solid #bbf7d0' }}>
                <CheckCircle2 size={16} />
                <span><b>Complete Category Representation:</b> All standardized footwear categories found among cohort peers are present in {data.target_brand.name}'s active catalog.</span>
              </div>
            ) : (
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                {data.missing_categories.map((cat, idx) => (
                  <div key={idx} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    background: '#fffbeb',
                    border: '1px solid #fde68a',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    color: '#92400e'
                  }}>
                    <XCircle size={14} style={{ color: '#d97706' }} />
                    {cat}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Strict Methodological Guardrail */}
          <div style={{
            background: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderLeft: '4px solid #0f172a',
            padding: '16px',
            borderRadius: '4px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700, fontSize: '0.86rem', color: '#0f172a', marginBottom: '4px' }}>
              <AlertCircle size={16} />
              Methodological Guardrail on Assortment "Gaps"
            </div>
            <div style={{ fontSize: '0.80rem', color: '#475569', lineHeight: 1.5 }}>
              BrandSignal describes observable differences in public catalog listings. An assortment or category gap is strictly a descriptive delta.
              This does <b>NOT</b> constitute a strategic recommendation to launch new categories, expand SKUs, or match competitor catalog size.
              Assortment decisions depend on unit economics, inventory capital, brand positioning, and supply chain capability.
            </div>
          </div>
        </>
      )}
    </div>
  );
};
