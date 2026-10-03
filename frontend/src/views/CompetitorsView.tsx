import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { BrandComparisonData } from '../api/types';
import { MetricCard } from '../components/MetricCard';

interface CompetitorsViewProps {
  snapshotDate: string;
}

const BRANDS = [
  { id: 'baccabucci', name: 'Bacca Bucci' },
  { id: 'neemans', name: "Neeman's" },
  { id: 'elevarsports', name: 'Elevar Sports' },
  { id: 'plaeto', name: 'Plaeto' }
];

export const CompetitorsView: React.FC<CompetitorsViewProps> = ({ snapshotDate }) => {
  const [brandA, setBrandA] = useState('baccabucci');
  const [brandB, setBrandB] = useState('neemans');
  const [data, setData] = useState<BrandComparisonData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    api.compareBrands(brandA, brandB, snapshotDate)
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
  }, [brandA, brandB, snapshotDate]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header & Brand Selector Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <div className="title-xl">Competitor Benchmark Lens</div>
          <div className="subtitle">
            Side-by-side head-to-head benchmarking across catalog breadth, price positioning, and promotional markdowns.
          </div>
        </div>

        {/* Brand Dropdowns */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: '#ffffff', border: '1px solid #cbd5e1', padding: '6px 12px', borderRadius: '4px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.68rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Brand A</label>
            <select
              value={brandA}
              onChange={(e) => setBrandA(e.target.value)}
              style={{ border: 'none', background: 'transparent', fontSize: '0.82rem', fontWeight: 700, color: '#0f172a', outline: 'none' }}
            >
              {BRANDS.map(b => (
                <option key={b.id} value={b.id} disabled={b.id === brandB}>{b.name}</option>
              ))}
            </select>
          </div>

          <span style={{ fontSize: '0.80rem', fontWeight: 700, color: '#94a3b8' }}>vs</span>

          <div>
            <label style={{ display: 'block', fontSize: '0.68rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Brand B</label>
            <select
              value={brandB}
              onChange={(e) => setBrandB(e.target.value)}
              style={{ border: 'none', background: 'transparent', fontSize: '0.82rem', fontWeight: 700, color: '#0f172a', outline: 'none' }}
            >
              {BRANDS.map(b => (
                <option key={b.id} value={b.id} disabled={b.id === brandA}>{b.name}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {loading && <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>Comparing brands...</div>}
      {error && <div style={{ padding: '40px', textAlign: 'center', color: '#dc2626' }}>Error: {error}</div>}

      {data && !loading && (
        <>
          {/* Quick Head-to-Head Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
            <MetricCard
              label={`${data.brand_a.name} Styles`}
              value={data.brand_a.styles.toLocaleString()}
              subtext={`${data.brand_a.skus.toLocaleString()} SKUs (${data.brand_a.variant_density.toFixed(2)} / style)`}
            />
            <MetricCard
              label={`${data.brand_b.name} Styles`}
              value={data.brand_b.styles.toLocaleString()}
              subtext={`${data.brand_b.skus.toLocaleString()} SKUs (${data.brand_b.variant_density.toFixed(2)} / style)`}
            />
            <MetricCard
              label={`${data.brand_a.name} Price`}
              value={`₹${data.brand_a.median_price.toLocaleString()}`}
              subtext={`Price Positioning Index: ${data.brand_a.ppi.toFixed(2)}`}
              badgeType="blue"
              badge={`PPI ${data.brand_a.ppi.toFixed(2)}`}
            />
            <MetricCard
              label={`${data.brand_b.name} Price`}
              value={`₹${data.brand_b.median_price.toLocaleString()}`}
              subtext={`Price Positioning Index: ${data.brand_b.ppi.toFixed(2)}`}
              badgeType="blue"
              badge={`PPI ${data.brand_b.ppi.toFixed(2)}`}
            />
          </div>

          {/* Detailed Side-by-Side Comparison Table */}
          <div className="card">
            <div className="card-header">Head-to-Head Metric Comparison</div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Analytical Dimension</th>
                  <th>{data.brand_a.name}</th>
                  <th>{data.brand_b.name}</th>
                  <th>Observed Difference</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style={{ fontWeight: 600 }}>Active Parent Styles</td>
                  <td>{data.brand_a.styles.toLocaleString()}</td>
                  <td>{data.brand_b.styles.toLocaleString()}</td>
                  <td>
                    {data.brand_a.styles >= data.brand_b.styles
                      ? `+${(data.brand_a.styles - data.brand_b.styles).toLocaleString()} styles (${data.brand_a.name})`
                      : `+${(data.brand_b.styles - data.brand_a.styles).toLocaleString()} styles (${data.brand_b.name})`}
                  </td>
                </tr>
                <tr>
                  <td style={{ fontWeight: 600 }}>Active Purchasable SKUs</td>
                  <td>{data.brand_a.skus.toLocaleString()}</td>
                  <td>{data.brand_b.skus.toLocaleString()}</td>
                  <td>
                    {data.brand_a.skus >= data.brand_b.skus
                      ? `+${(data.brand_a.skus - data.brand_b.skus).toLocaleString()} SKUs (${data.brand_a.name})`
                      : `+${(data.brand_b.skus - data.brand_a.skus).toLocaleString()} SKUs (${data.brand_b.name})`}
                  </td>
                </tr>
                <tr>
                  <td style={{ fontWeight: 600 }}>Variant Density (SKUs / Style)</td>
                  <td>{data.brand_a.variant_density.toFixed(2)}</td>
                  <td>{data.brand_b.variant_density.toFixed(2)}</td>
                  <td>
                    {(data.brand_a.variant_density - data.brand_b.variant_density).toFixed(2)} variants
                  </td>
                </tr>
                <tr>
                  <td style={{ fontWeight: 600 }}>Median Listed Selling Price</td>
                  <td>₹{data.brand_a.median_price.toLocaleString()}</td>
                  <td>₹{data.brand_b.median_price.toLocaleString()}</td>
                  <td>
                    ₹{Math.abs(data.brand_a.median_price - data.brand_b.median_price).toLocaleString()}{' '}
                    {data.brand_a.median_price > data.brand_b.median_price ? `higher (${data.brand_a.name})` : `higher (${data.brand_b.name})`}
                  </td>
                </tr>
                <tr>
                  <td style={{ fontWeight: 600 }}>Price Positioning Index (PPI)</td>
                  <td>{data.brand_a.ppi.toFixed(2)}</td>
                  <td>{data.brand_b.ppi.toFixed(2)}</td>
                  <td>{(data.brand_a.ppi - data.brand_b.ppi).toFixed(2)} pts</td>
                </tr>
                <tr>
                  <td style={{ fontWeight: 600 }}>Discounted Catalog Ratio</td>
                  <td>{data.brand_a.discount_ratio.toFixed(1)}%</td>
                  <td>{data.brand_b.discount_ratio.toFixed(1)}%</td>
                  <td>{(data.brand_a.discount_ratio - data.brand_b.discount_ratio).toFixed(1)}%</td>
                </tr>
                <tr>
                  <td style={{ fontWeight: 600 }}>Median Markdown Depth</td>
                  <td>{data.brand_a.median_discount_depth.toFixed(1)}%</td>
                  <td>{data.brand_b.median_discount_depth.toFixed(1)}%</td>
                  <td>{(data.brand_a.median_discount_depth - data.brand_b.median_discount_depth).toFixed(1)}%</td>
                </tr>
                <tr>
                  <td style={{ fontWeight: 600 }}>Cohort Search Attention Share</td>
                  <td>{data.brand_a.avg_cohort_share.toFixed(1)}%</td>
                  <td>{data.brand_b.avg_cohort_share.toFixed(1)}%</td>
                  <td>{(data.brand_a.avg_cohort_share - data.brand_b.avg_cohort_share).toFixed(1)}%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
};
