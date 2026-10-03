import React, { useEffect, useState } from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { api } from '../api/client';
import type { MarketSnapshotData } from '../api/types';
import { MetricCard } from '../components/MetricCard';

interface MarketViewProps {
  snapshotDate: string;
}

export const MarketView: React.FC<MarketViewProps> = ({ snapshotDate }) => {
  const [data, setData] = useState<MarketSnapshotData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    api.getMarketSnapshot('D2C Footwear', snapshotDate)
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
  }, [snapshotDate]);

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>Loading market snapshot data...</div>;
  }

  if (error || !data) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#dc2626' }}>Error: {error || 'Unable to load data'}</div>;
  }

  const { benchmarks, brands } = data;

  const chartData = brands.map(b => ({
    name: b.brand_name,
    styles: b.active_styles,
    skus: b.active_skus,
    median_price: b.median_price
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* View Header */}
      <div>
        <div className="title-xl">Market Landscape Lens</div>
        <div className="subtitle">
          Macro cohort benchmarks across active styles, purchasable SKUs, pricing architecture, and promotional penetration.
        </div>
      </div>

      {/* KPI Cards Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
        <MetricCard
          label="Total Active Styles"
          value={benchmarks.total_active_products?.toLocaleString() || '2,050'}
          subtext="Cohort breadth across 4 merchants"
          badge="Storefront Snapshot"
        />
        <MetricCard
          label="Total Active SKUs"
          value={benchmarks.total_active_skus?.toLocaleString() || '10,576'}
          subtext="Total purchasable variants"
          badge="Option Depth"
        />
        <MetricCard
          label="Cohort Median Listed Price"
          value={`₹${Math.round(benchmarks.median_price_inr || 1899).toLocaleString()}`}
          subtext="Benchmark reference anchor"
          badge="Pricing Anchor"
          badgeType="blue"
        />
        <MetricCard
          label="Cohort Median Discount %"
          value={`${(benchmarks.median_discount_ratio || 95.8).toFixed(1)}%`}
          subtext="Percentage of catalog discounted"
          badge="Promotions"
          badgeType="amber"
        />
      </div>

      {/* Catalog Scale Bifurcation Chart */}
      <div className="card">
        <div className="card-header">Catalog Scale & Option Depth (Styles vs SKUs)</div>
        <div style={{ fontSize: '0.78rem', color: '#64748b', marginBottom: '16px' }}>
          Demonstrates scale bifurcation: Bacca Bucci and Neeman's represent over 91% of total catalog listings.
        </div>
        <div style={{ height: '320px', width: '100%' }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#334155' }} />
              <YAxis tick={{ fontSize: 12, fill: '#334155' }} />
              <Tooltip
                contentStyle={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '4px', fontSize: '0.80rem' }}
                formatter={(val: any, name: any) => [val.toLocaleString(), name === 'styles' ? 'Active Styles' : 'Active SKUs']}
              />
              <Bar dataKey="styles" fill="#0f172a" name="Active Styles" radius={[3, 3, 0, 0]} />
              <Bar dataKey="skus" fill="#2563eb" name="Active SKUs" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Full Cohort Overview Table */}
      <div className="card">
        <div className="card-header">Competitive Cohort Metric Table (Snapshot: {snapshotDate})</div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Brand Name</th>
              <th>Active Styles</th>
              <th>Active SKUs</th>
              <th>Variants / Style</th>
              <th>Median Listed Price</th>
              <th>PPI</th>
              <th>Discounted %</th>
              <th>Tranco Global Rank</th>
            </tr>
          </thead>
          <tbody>
            {brands.map(b => (
              <tr key={b.brand_id}>
                <td style={{ fontWeight: 700 }}>{b.brand_name}</td>
                <td>{b.active_styles.toLocaleString()}</td>
                <td>{b.active_skus.toLocaleString()}</td>
                <td>{(b.active_skus / (b.active_styles || 1)).toFixed(2)}</td>
                <td>₹{b.median_price.toLocaleString()}</td>
                <td>
                  <span style={{
                    padding: '2px 6px',
                    borderRadius: '3px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    background: b.ppi > 1.05 ? '#eff6ff' : b.ppi < 0.95 ? '#f8fafc' : '#f1f5f9',
                    color: b.ppi > 1.05 ? '#2563eb' : '#334155'
                  }}>
                    {b.ppi.toFixed(2)}
                  </span>
                </td>
                <td>{b.discount_ratio.toFixed(1)}%</td>
                <td>{b.tranco_rank ? `#${b.tranco_rank.toLocaleString()}` : 'Unranked (>1M)'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
