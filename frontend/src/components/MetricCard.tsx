import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  badge?: string;
  badgeType?: 'neutral' | 'blue' | 'amber' | 'green';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subtext,
  badge,
  badgeType = 'neutral'
}) => {
  const getBadgeStyle = () => {
    switch (badgeType) {
      case 'blue':
        return { background: '#eff6ff', color: '#2563eb', border: '1px solid #bfdbfe' };
      case 'amber':
        return { background: '#fef3c7', color: '#b45309', border: '1px solid #fde68a' };
      case 'green':
        return { background: '#dcfce7', color: '#15803d', border: '1px solid #bbf7d0' };
      default:
        return { background: '#f1f5f9', color: '#475569', border: '1px solid #cbd5e1' };
    }
  };

  return (
    <div style={{
      background: '#ffffff',
      border: '1px solid #e2e8f0',
      borderRadius: '4px',
      padding: '12px 16px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
        <span style={{
          fontSize: '0.70rem',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          color: '#64748b'
        }}>
          {label}
        </span>
        {badge && (
          <span style={{
            fontSize: '0.70rem',
            fontWeight: 600,
            padding: '1px 6px',
            borderRadius: '3px',
            ...getBadgeStyle()
          }}>
            {badge}
          </span>
        )}
      </div>

      <div style={{
        fontSize: '1.55rem',
        fontWeight: 800,
        color: '#0f172a',
        lineHeight: 1.15
      }}>
        {value}
      </div>

      {subtext && (
        <div style={{
          fontSize: '0.75rem',
          color: '#475569',
          marginTop: '4px'
        }}>
          {subtext}
        </div>
      )}
    </div>
  );
};
