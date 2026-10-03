import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Navigation, type TabId } from './components/Navigation';
import { ProvenanceDrawer } from './components/ProvenanceDrawer';
import { AskView } from './views/AskView';
import { MarketView } from './views/MarketView';
import { CompetitorsView } from './views/CompetitorsView';
import { GapsView } from './views/GapsView';
import { TrendsView } from './views/TrendsView';
import { EvidenceView } from './views/EvidenceView';
import type { BrandContext, EvidenceItem } from './api/types';
import { api } from './api/client';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('ask');
  const [selectedDate, setSelectedDate] = useState('2026-09-29');
  const [availableDates, setAvailableDates] = useState<string[]>(['2026-09-29']);
  const [context, setContext] = useState<BrandContext>({
    brand_name: "Bacca Bucci",
    industry: "Footwear",
    category: "D2C Footwear",
    geography: "IN",
    is_demo_vertical: true,
    demo_brand_id: "baccabucci",
    competitors: ["Neeman's", "Elevar Sports", "Plaeto"],
    status: "ESTABLISHED",
    summary: "Brand: Bacca Bucci | Industry: Footwear | Category: D2C Footwear",
    is_established: true
  });

  // Provenance Drawer State
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [drawerEvidence, setDrawerEvidence] = useState<EvidenceItem[]>([]);
  const [drawerMarkdown, setDrawerMarkdown] = useState<string | undefined>();

  useEffect(() => {
    // Load snapshot dates and initial context
    api.getSnapshotDates()
      .then(dates => {
        if (dates.length > 0) {
          setAvailableDates(dates);
          setSelectedDate(dates[0]);
        }
      })
      .catch(() => {});

    api.getContext('default')
      .then(ctx => {
        if (ctx.is_established) {
          setContext(ctx);
        }
      })
      .catch(() => {});
  }, []);

  const handleResetSession = async () => {
    try {
      await api.resetContext('default');
      const freshCtx = await api.getContext('default');
      setContext(freshCtx);
      // Reload page state
      window.location.reload();
    } catch (e) {
      console.error('Reset failed', e);
    }
  };

  const handleOpenProvenance = (items: EvidenceItem[], md?: string) => {
    setDrawerEvidence(items);
    setDrawerMarkdown(md);
    setIsDrawerOpen(true);
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#f8fafc' }}>
      {/* Top Header */}
      <Header
        context={context}
        availableDates={availableDates}
        selectedDate={selectedDate}
        onSelectDate={setSelectedDate}
        onResetSession={handleResetSession}
      />

      {/* Primary Tab Navigation */}
      <Navigation activeTab={activeTab} onSelectTab={setActiveTab} />

      {/* Main Content Workspace */}
      <main style={{ flex: 1, padding: '24px 32px', maxWidth: '1440px', width: '100%', margin: '0 auto' }}>
        {activeTab === 'ask' && (
          <AskView
            context={context}
            onNavigateTab={setActiveTab}
            onOpenProvenance={handleOpenProvenance}
          />
        )}
        {activeTab === 'market' && (
          <MarketView snapshotDate={selectedDate} />
        )}
        {activeTab === 'competitors' && (
          <CompetitorsView snapshotDate={selectedDate} />
        )}
        {activeTab === 'gaps' && (
          <GapsView snapshotDate={selectedDate} />
        )}
        {activeTab === 'trends' && (
          <TrendsView />
        )}
        {activeTab === 'evidence' && (
          <EvidenceView onInspectEvidence={(item) => handleOpenProvenance([item])} />
        )}
      </main>

      {/* Footer / Methodological Callout */}
      <footer style={{
        background: '#ffffff',
        borderTop: '1px solid #e2e8f0',
        padding: '16px 32px',
        fontSize: '0.74rem',
        color: '#64748b',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div>
          <b>BrandSignal Methodology:</b> Observable empirical differences across public storefront catalogs, Google Trends, and public research.
          Zero prescriptive strategy advice. "Understand the market. See the gap. Make the call."
        </div>
        <div style={{ display: 'flex', gap: '16px' }}>
          <span>Storefront Snapshot: {selectedDate}</span>
          <span>Google Trends: 53-Week Series</span>
          <span>Backend: FastAPI + DuckDB</span>
        </div>
      </footer>

      {/* Provenance Drawer */}
      <ProvenanceDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        evidenceItems={drawerEvidence}
        markdownSummary={drawerMarkdown}
      />
    </div>
  );
};

export default App;
