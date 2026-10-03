import React from 'react';
import { RefreshCw, ShieldCheck } from 'lucide-react';
import type { BrandContext } from '../api/types';

interface HeaderProps {
  context: BrandContext;
  availableDates: string[];
  selectedDate: string;
  onSelectDate: (date: string) => void;
  onResetSession: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  context,
  availableDates,
  selectedDate,
  onSelectDate,
  onResetSession
}) => {
  return (
    <header style={{
      background: '#ffffff',
      borderBottom: '1px solid #e2e8f0',
      padding: '12px 24px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center'
    }}>
      {/* Brand & Subhead */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1.45rem', fontWeight: 800, color: '#0f172a', letterSpacing: '-0.02em' }}>
            BrandSignal
          </span>
          <span style={{
            fontSize: '0.68rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            background: '#eff6ff',
            color: '#2563eb',
            border: '1px solid #bfdbfe',
            padding: '2px 6px',
            borderRadius: '3px'
          }}>
            Intelligence Terminal
          </span>
        </div>
        <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '1px' }}>
          "Understand the market. See the gap. Make the call."
        </div>
      </div>

      {/* Controls & Active Perspective */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        {/* Active Brand Context Badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          background: '#f8fafc',
          border: '1px solid #cbd5e1',
          padding: '5px 10px',
          borderRadius: '4px',
          fontSize: '0.78rem',
          color: '#334155'
        }}>
          <ShieldCheck size={14} style={{ color: '#16a34a' }} />
          <span>
            <b>Perspective:</b> {context.brand_name || 'Cohort Neutral'} ({context.category || context.industry || 'Footwear'})
          </span>
        </div>

        {/* Snapshot Date Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '0.74rem', fontWeight: 600, color: '#64748b' }}>
            Catalog Snapshot:
          </span>
          <select
            value={selectedDate}
            onChange={(e) => onSelectDate(e.target.value)}
            style={{
              padding: '4px 8px',
              fontSize: '0.78rem',
              fontWeight: 600,
              background: '#ffffff',
              border: '1px solid #cbd5e1',
              borderRadius: '3px',
              color: '#0f172a',
              outline: 'none'
            }}
          >
            {availableDates.map(date => (
              <option key={date} value={date}>{date}</option>
            ))}
          </select>
        </div>

        {/* Reset Session */}
        <button
          onClick={onResetSession}
          title="Reset conversational session memory"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            background: '#ffffff',
            border: '1px solid #cbd5e1',
            borderRadius: '3px',
            padding: '5px 9px',
            fontSize: '0.74rem',
            fontWeight: 600,
            color: '#475569',
            cursor: 'pointer'
          }}
        >
          <RefreshCw size={12} />
          Reset
        </button>
      </div>
    </header>
  );
};
