import React from 'react';
import { MessageSquare, BarChart3, Scale, Layers, TrendingUp, FileText } from 'lucide-react';

export type TabId = 'ask' | 'market' | 'competitors' | 'gaps' | 'trends' | 'evidence';

interface NavigationProps {
  activeTab: TabId;
  onSelectTab: (tab: TabId) => void;
}

export const Navigation: React.FC<NavigationProps> = ({ activeTab, onSelectTab }) => {
  const tabs: Array<{ id: TabId; label: string; icon: React.ReactNode }> = [
    { id: 'ask', label: 'Ask BrandSignal', icon: <MessageSquare size={15} /> },
    { id: 'market', label: 'Market', icon: <BarChart3 size={15} /> },
    { id: 'competitors', label: 'Competitors', icon: <Scale size={15} /> },
    { id: 'gaps', label: 'Gaps', icon: <Layers size={15} /> },
    { id: 'trends', label: 'Trends', icon: <TrendingUp size={15} /> },
    { id: 'evidence', label: 'Evidence', icon: <FileText size={15} /> }
  ];

  return (
    <nav style={{
      background: '#f8fafc',
      borderBottom: '1px solid #e2e8f0',
      padding: '8px 24px 0 24px',
      display: 'flex',
      gap: '4px'
    }}>
      {tabs.map(tab => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onSelectTab(tab.id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              fontSize: '0.82rem',
              fontWeight: isActive ? 700 : 500,
              color: isActive ? '#0f172a' : '#64748b',
              background: isActive ? '#ffffff' : 'transparent',
              border: isActive ? '1px solid #e2e8f0' : '1px solid transparent',
              borderBottom: isActive ? '1px solid #ffffff' : '1px solid transparent',
              borderTopLeftRadius: '4px',
              borderTopRightRadius: '4px',
              marginBottom: '-1px',
              outline: 'none',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            {tab.icon}
            {tab.label}
          </button>
        );
      })}
    </nav>
  );
};
