import { useState, useRef, useEffect } from 'react';
import { useAIStore } from '../../stores';

interface ChatInterfaceProps {
  designId: string;
}

export function ChatInterface({ designId }: ChatInterfaceProps) {
  const { messages, isProcessing, addMessage, setProcessing } = useAIStore();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isProcessing) return;

    addMessage({ role: 'user', content: text });
    setInput('');
    setProcessing(true);

    // Auto-resize textarea back
    if (textareaRef.current) {
      textareaRef.current.style.height = '20px';
    }

    // Simulate AI response (replace with actual API call)
    setTimeout(() => {
      const responses: Record<string, string> = {
        'place': "I'll place the component for you. I recommend positioning it near the power section for optimal routing. Shall I proceed with the suggested coordinates?",
        'route': "I can auto-route that net. The optimal strategy for this trace is to use a 0.25mm width on F.Cu with a single via transition to B.Cu near pin 4. Want me to execute this?",
        'drc': "Running DRC... ✅ All checks passed! No clearance violations, trace widths are within spec, and impedance targets are met for all high-speed nets.",
        'review': "**Design Review Summary:**\n\n📊 Overall Score: **87/100**\n\n✅ Schematic: Complete, good decoupling\n⚠️ Placement: Consider moving U2 closer to U1 for shorter power traces\n✅ Routing: Clean signal integrity\n💡 Suggestion: Add thermal relief pads on GND connections",
        'fix': "I found 2 potential improvements:\n1. **Clearance**: Increase spacing between R1 and R2 by 0.2mm\n2. **Thermal**: Add copper pour on B.Cu under U1 for heat dissipation\n\nShall I apply these fixes?",
      };

      const key = Object.keys(responses).find((k) => text.toLowerCase().includes(k)) || '';
      const response = responses[key] ||
        `I understand you want to "${text}". Let me analyze your current design and suggest the best approach. Your board has 8 components on a 2-layer stackup with FR4 substrate. What specific aspect would you like me to help with?`;

      addMessage({
        role: 'assistant',
        content: response,
        actions: key === 'fix' ? [
          { type: 'adjust_clearance', params: { component_a: 'R1', component_b: 'R2', min_distance_mm: 0.35 } },
          { type: 'add_zone', params: { layer: 'B.Cu', net: 'GND', area: 'under_U1' } },
        ] : undefined,
      });
      setProcessing(false);
    }, 1200);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const handleTextareaInput = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = '20px';
      el.style.height = Math.min(el.scrollHeight, 100) + 'px';
    }
  };

  return (
    <div className="chat-panel" id="chat-panel">
      <div className="chat-panel__header">
        <span className="chat-panel__header-dot" />
        AI Design Assistant
        <span style={{ marginLeft: 'auto', fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
          GPT-4o
        </span>
      </div>

      <div className="chat-panel__messages" id="chat-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-message chat-message--${msg.role}`}>
            <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>

            {/* Action buttons */}
            {msg.actions && msg.actions.length > 0 && (
              <div style={{
                marginTop: 'var(--space-sm)',
                display: 'flex',
                gap: 'var(--space-xs)',
                flexWrap: 'wrap',
              }}>
                <button
                  className="btn btn--primary btn--sm"
                  onClick={() => {
                    addMessage({ role: 'assistant', content: '✅ Fixes applied successfully! Running DRC to verify...' });
                  }}
                  style={{ fontSize: 11 }}
                >
                  ✓ Apply Fixes
                </button>
                <button className="btn btn--secondary btn--sm" style={{ fontSize: 11 }}>
                  Preview Changes
                </button>
              </div>
            )}
          </div>
        ))}

        {isProcessing && (
          <div className="chat-message chat-message--ai" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div className="loading-spinner" />
            <span style={{ color: 'var(--text-muted)' }}>Analyzing design...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-panel__input">
        {/* Quick action chips */}
        <div style={{
          display: 'flex', gap: 4, marginBottom: 'var(--space-sm)',
          flexWrap: 'wrap',
        }}>
          {['Run DRC', 'Review design', 'Auto-route', 'Fix violations'].map((action) => (
            <button
              key={action}
              className="btn btn--secondary btn--sm"
              onClick={() => sendMessage(action.toLowerCase())}
              style={{ fontSize: 11, padding: '2px 8px' }}
            >
              {action}
            </button>
          ))}
        </div>

        <div className="chat-input-wrapper">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              handleTextareaInput();
            }}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your design..."
            rows={1}
            id="chat-input"
          />
          <button
            className="btn btn--primary btn--icon"
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || isProcessing}
            style={{ borderRadius: 'var(--radius-md)', width: 32, height: 32, flexShrink: 0 }}
            id="btn-send"
          >
            ↑
          </button>
        </div>
      </div>
    </div>
  );
}
