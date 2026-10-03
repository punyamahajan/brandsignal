import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, FileText, ArrowRight, Loader2, Info } from 'lucide-react';
import type { ChatMessage, EvidenceItem, BrandContext } from '../api/types';
import { api } from '../api/client';
import type { TabId } from '../components/Navigation';

interface AskViewProps {
  context: BrandContext;
  onNavigateTab: (tab: TabId) => void;
  onOpenProvenance: (items: EvidenceItem[], md?: string) => void;
}

const SUGGESTED_CHIPS = [
  "What is happening in my market?",
  "How does my brand compare with Neeman's?",
  "What is my brand missing?",
  "Who is cheaper?",
  "What changed recently?"
];

export const AskView: React.FC<AskViewProps> = ({
  context,
  onNavigateTab,
  onOpenProvenance
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSendMessage = async (textToSend: string) => {
    const trimmed = textToSend.trim();
    if (!trimmed || isLoading) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: trimmed
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const resp = await api.sendChatMessage(trimmed, 'default', context);
      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: resp.narrative,
        cited_evidence: resp.cited_evidence,
        suggested_followups: resp.suggested_followups,
        visual_navigation_target: resp.visual_navigation_target,
        visual_navigation_label: resp.visual_navigation_label,
        why_are_you_saying_this_md: resp.why_are_you_saying_this_md,
        is_clarification: resp.is_clarification
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Error retrieving analytical intelligence: ${err.message || 'Network error'}`
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const mapNavigationTarget = (target?: string | null): TabId | null => {
    if (!target) return null;
    const lower = target.toLowerCase();
    if (lower.includes('market')) return 'market';
    if (lower.includes('comp')) return 'competitors';
    if (lower.includes('gap')) return 'gaps';
    if (lower.includes('trend')) return 'trends';
    if (lower.includes('evidence')) return 'evidence';
    return null;
  };

  return (
    <div style={{ maxWidth: '980px', margin: '0 auto', display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)' }}>
      {/* Header Prompt Chips */}
      <div style={{ padding: '14px 0 10px 0', borderBottom: '1px solid #e2e8f0', marginBottom: '14px' }}>
        <div style={{ fontSize: '0.70rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>
          Suggested Inquiries
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {SUGGESTED_CHIPS.map((chip, idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(chip)}
              disabled={isLoading}
              style={{
                background: '#ffffff',
                border: '1px solid #cbd5e1',
                borderRadius: '4px',
                padding: '6px 12px',
                fontSize: '0.78rem',
                color: '#1e293b',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                cursor: 'pointer',
                transition: 'all 0.1s ease'
              }}
            >
              <Sparkles size={12} style={{ color: '#2563eb' }} />
              {chip}
            </button>
          ))}
        </div>
      </div>

      {/* Messages Thread */}
      <div style={{ flex: 1, overflowY: 'auto', paddingRight: '6px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {messages.length === 0 && (
          <div style={{
            background: '#ffffff',
            border: '1px solid #e2e8f0',
            borderRadius: '4px',
            padding: '24px',
            marginTop: '20px'
          }}>
            <div style={{ fontSize: '1.10rem', fontWeight: 700, color: '#0f172a', marginBottom: '6px' }}>
              Welcome to BrandSignal Conversational Analytics
            </div>
            <div style={{ fontSize: '0.86rem', color: '#475569', lineHeight: 1.5, marginBottom: '18px' }}>
              Understand your market, discover competitor differences, identify observable gaps, and inspect verified primary evidence.
              BrandSignal answers what is happening without prescribing strategy.
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '0.80rem' }}>
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '12px', borderRadius: '4px' }}>
                <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '4px' }}>📊 Market Landscape & Pricing</div>
                <div style={{ color: '#64748b' }}>
                  • <i>"What is happening in my market?"</i><br/>
                  • <i>"Who is cheaper?"</i><br/>
                  • <i>"Who discounts the most?"</i>
                </div>
              </div>
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '12px', borderRadius: '4px' }}>
                <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '4px' }}>🔍 Assortment Gaps & Trends</div>
                <div style={{ color: '#64748b' }}>
                  • <i>"How does my brand compare with Neeman's?"</i><br/>
                  • <i>"What is my brand missing?"</i><br/>
                  • <i>"What changed recently in search?"</i>
                </div>
              </div>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start'
          }}>
            <div style={{
              maxWidth: msg.role === 'user' ? '75%' : '100%',
              background: msg.role === 'user' ? '#0f172a' : '#ffffff',
              color: msg.role === 'user' ? '#ffffff' : '#0f172a',
              border: msg.role === 'user' ? 'none' : '1px solid #e2e8f0',
              borderRadius: '4px',
              padding: '14px 18px',
              fontSize: '0.88rem',
              lineHeight: 1.55,
              whiteSpace: 'pre-wrap'
            }}>
              {msg.content}

              {/* Action Buttons for Assistant Responses */}
              {msg.role === 'assistant' && (
                <div style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px solid #f1f5f9', display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
                  {/* Provenance Drawer Trigger */}
                  {msg.cited_evidence && msg.cited_evidence.length > 0 && (
                    <button
                      onClick={() => onOpenProvenance(msg.cited_evidence || [], msg.why_are_you_saying_this_md)}
                      style={{
                        background: '#f8fafc',
                        border: '1px solid #cbd5e1',
                        borderRadius: '3px',
                        padding: '4px 10px',
                        fontSize: '0.74rem',
                        fontWeight: 600,
                        color: '#334155',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        cursor: 'pointer'
                      }}
                    >
                      <FileText size={13} style={{ color: '#2563eb' }} />
                      Why are you saying this? ({msg.cited_evidence.length} evidence items)
                    </button>
                  )}

                  {/* Visual Exploration Deep Link */}
                  {msg.visual_navigation_target && mapNavigationTarget(msg.visual_navigation_target) && (
                    <button
                      onClick={() => onNavigateTab(mapNavigationTarget(msg.visual_navigation_target)!)}
                      style={{
                        background: '#eff6ff',
                        border: '1px solid #bfdbfe',
                        borderRadius: '3px',
                        padding: '4px 10px',
                        fontSize: '0.74rem',
                        fontWeight: 600,
                        color: '#2563eb',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        cursor: 'pointer'
                      }}
                    >
                      {msg.visual_navigation_label || `Explore in ${msg.visual_navigation_target}`}
                      <ArrowRight size={13} />
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Follow-up suggestions */}
            {msg.role === 'assistant' && msg.suggested_followups && msg.suggested_followups.length > 0 && (
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '8px' }}>
                {msg.suggested_followups.map((fup, f_idx) => (
                  <button
                    key={f_idx}
                    onClick={() => handleSendMessage(fup)}
                    disabled={isLoading}
                    style={{
                      background: '#ffffff',
                      border: '1px solid #e2e8f0',
                      borderRadius: '3px',
                      padding: '3px 8px',
                      fontSize: '0.72rem',
                      color: '#475569',
                      cursor: 'pointer'
                    }}
                  >
                    ↳ {fup}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#64748b', fontSize: '0.82rem', padding: '12px' }}>
            <Loader2 size={16} className="animate-spin" />
            Analyzing verified primary datasets...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Box & Guardrail */}
      <div style={{ paddingTop: '12px', borderTop: '1px solid #e2e8f0', marginTop: '8px' }}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage(input);
          }}
          style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a market, competitor, pricing, or gap question..."
            disabled={isLoading}
            style={{
              flex: 1,
              padding: '10px 14px',
              fontSize: '0.88rem',
              border: '1px solid #cbd5e1',
              borderRadius: '4px',
              outline: 'none',
              background: '#ffffff',
              color: '#0f172a'
            }}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            style={{
              background: input.trim() && !isLoading ? '#0f172a' : '#94a3b8',
              color: '#ffffff',
              border: 'none',
              borderRadius: '4px',
              padding: '0 18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: input.trim() && !isLoading ? 'pointer' : 'default'
            }}
          >
            <Send size={16} />
          </button>
        </form>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '0.72rem',
          color: '#64748b',
          background: '#f8fafc',
          border: '1px solid #e2e8f0',
          padding: '6px 10px',
          borderRadius: '3px'
        }}>
          <Info size={13} style={{ flexShrink: 0 }} />
          <span><b>Methodological Discipline:</b> BrandSignal reports observable facts in public storefront data. It does not fabricate causal claims or formulate strategy.</span>
        </div>
      </div>
    </div>
  );
};
