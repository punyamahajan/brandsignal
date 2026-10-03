import React from 'react';
import { X, ExternalLink, Database, AlertCircle, Calendar } from 'lucide-react';
import type { EvidenceItem } from '../api/types';

interface ProvenanceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  evidenceItems: EvidenceItem[];
  markdownSummary?: string;
}

export const ProvenanceDrawer: React.FC<ProvenanceDrawerProps> = ({
  isOpen,
  onClose,
  evidenceItems,
  markdownSummary
}) => {
  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(15, 23, 42, 0.45)',
      display: 'flex',
      justifyContent: 'flex-end',
      zIndex: 1000
    }}>
      <div style={{
        background: '#ffffff',
        width: '100%',
        maxWidth: '620px',
        height: '100%',
        boxShadow: '-4px 0 20px rgba(0, 0, 0, 0.1)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        {/* Drawer Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid #e2e8f0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: '#f8fafc'
        }}>
          <div>
            <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#0f172a' }}>
              Why Are You Saying This?
            </div>
            <div style={{ fontSize: '0.78rem', color: '#64748b' }}>
              Primary Source Provenance & Certified Evidence Items
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              padding: '6px',
              borderRadius: '4px',
              display: 'flex',
              alignItems: 'center',
              color: '#64748b'
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Drawer Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
          {evidenceItems.length === 0 ? (
            <div style={{
              background: '#f8fafc',
              border: '1px dashed #cbd5e1',
              borderRadius: '4px',
              padding: '24px',
              textAlign: 'center',
              color: '#64748b',
              fontSize: '0.85rem'
            }}>
              No empirical tools or primary evidence items cited for this turn.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {evidenceItems.map((item, idx) => (
                <div key={item.evidence_id || idx} style={{
                  background: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '4px',
                  padding: '14px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
                }}>
                  {/* Top Bar */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span style={{
                      background: '#0f172a',
                      color: '#ffffff',
                      fontSize: '0.70rem',
                      fontWeight: 700,
                      padding: '2px 8px',
                      borderRadius: '3px',
                      letterSpacing: '0.04em'
                    }}>
                      {item.evidence_id}
                    </span>
                    <span style={{
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      background: '#f1f5f9',
                      border: '1px solid #cbd5e1',
                      padding: '2px 6px',
                      borderRadius: '3px',
                      color: '#334155'
                    }}>
                      {item.source_type.replace('_', ' ').toUpperCase()}
                    </span>
                  </div>

                  {/* Source Name */}
                  <div style={{ fontSize: '0.90rem', fontWeight: 700, color: '#0f172a', marginBottom: '4px' }}>
                    {item.source_name}
                  </div>

                  {/* Observation */}
                  <div style={{ fontSize: '0.82rem', color: '#1e293b', lineHeight: 1.4, marginBottom: '8px' }}>
                    {item.observation}
                  </div>

                  {/* Metadata Row */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '8px',
                    fontSize: '0.74rem',
                    color: '#64748b',
                    padding: '8px 10px',
                    background: '#f8fafc',
                    borderRadius: '4px',
                    marginBottom: '8px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Calendar size={13} />
                      <span>{item.collected_at?.slice(0, 10) || 'N/A'}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Database size={13} />
                      <span title={item.raw_reference || ''}>{item.dataset_name || 'DuckDB'}</span>
                    </div>
                  </div>

                  {/* Source URL if available */}
                  {item.source_url && (
                    <div style={{ marginBottom: '8px' }}>
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          fontSize: '0.74rem',
                          color: '#2563eb',
                          textDecoration: 'none',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          fontWeight: 500
                        }}
                      >
                        <ExternalLink size={12} />
                        View Canonical Source Reference
                      </a>
                    </div>
                  )}

                  {/* Limitation Note */}
                  {item.limitation_note && (
                    <div style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '6px',
                      fontSize: '0.72rem',
                      color: '#475569',
                      background: '#fffbeb',
                      border: '1px solid #fef3c7',
                      padding: '6px 8px',
                      borderRadius: '3px'
                    }}>
                      <AlertCircle size={14} style={{ color: '#d97706', flexShrink: 0, marginTop: '1px' }} />
                      <span><b>Limitation:</b> {item.limitation_note}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {markdownSummary && (
            <div style={{ marginTop: '20px', borderTop: '1px solid #e2e8f0', paddingTop: '16px' }}>
              <div style={{ fontSize: '0.80rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: '8px' }}>
                Full Audit Summary
              </div>
              <pre style={{
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: '4px',
                padding: '12px',
                fontSize: '0.75rem',
                whiteSpace: 'pre-wrap',
                fontFamily: 'monospace',
                color: '#334155'
              }}>
                {markdownSummary}
              </pre>
            </div>
          )}
        </div>

        {/* Drawer Footer */}
        <div style={{
          padding: '12px 20px',
          borderTop: '1px solid #e2e8f0',
          background: '#f8fafc',
          fontSize: '0.72rem',
          color: '#64748b'
        }}>
          <b>Auditable Provenance:</b> All metrics originate from public storefront crawls, official Google Trends series, or verified APIs without generative extrapolation.
        </div>
      </div>
    </div>
  );
};
