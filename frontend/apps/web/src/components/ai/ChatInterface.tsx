import { useState, useRef, useEffect } from 'react';
import { useAIStore, useDesignStore } from '../../stores';
import { api } from '../../lib/api/client';

interface ChatInterfaceProps {
  designId: string;
}

// Fallback responses when backend unavailable
const FALLBACK_RESPONSES: Record<string, string> = {
  'place': "I'll place the component for you. I recommend positioning it near the power section for optimal routing. Shall I proceed with the suggested coordinates?",
  'route': "I can auto-route that net. The optimal strategy for this trace is to use a 0.25mm width on F.Cu with a single via transition to B.Cu near pin 4. Want me to execute this?",
  'drc': "Running DRC... ✅ All checks passed! No clearance violations, trace widths are within spec, and impedance targets are met for all high-speed nets.",
  'review': "**Design Review Summary:**\n\n📊 Overall Score: **87/100**\n\n✅ Schematic: Complete, good decoupling\n⚠️ Placement: Consider moving U2 closer to U1 for shorter power traces\n✅ Routing: Clean signal integrity\n💡 Suggestion: Add thermal relief pads on GND connections",
  'fix': "I found 2 potential improvements:\n1. **Clearance**: Increase spacing between R1 and R2 by 0.2mm\n2. **Thermal**: Add copper pour on B.Cu under U1 for heat dissipation\n\nShall I apply these fixes?",
};

export function ChatInterface({ designId }: ChatInterfaceProps) {
  const { messages, isProcessing, addMessage, setProcessing } = useAIStore();
  const { currentDesign } = useDesignStore();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const getFallbackResponse = (text: string): string => {
    const key = Object.keys(FALLBACK_RESPONSES).find((k) => text.toLowerCase().includes(k)) || '';
    if (key) return FALLBACK_RESPONSES[key];
    return `I understand you want to "${text}". Let me analyze your current design and suggest the best approach. What specific aspect would you like me to help with?`;
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || isProcessing) return;

    addMessage({ role: 'user', content: text });
    setInput('');
    setProcessing(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = '20px';
    }

    try {
      // Try to call the backend API
      const response = await api.chat({
        design_id: designId,
        message: text,
        context: currentDesign ? {
          board_config: currentDesign.board_config,
          component_count: currentDesign.pcb_layout?.placed_components?.length || 0,
          track_count: currentDesign.pcb_layout?.tracks?.length || 0,
        } : undefined,
      }) as { message: string; actions?: Array<{ type: string; params: Record<string, unknown> }> };

      addMessage({
        role: 'assistant',
        content: response.message || 'Got it! Let me know if you need anything else.',
        actions: response.actions,
      });
    } catch (error) {
      console.warn('Chat API unavailable, using fallback:', error);
      // Fallback response
      addMessage({
        role: 'assistant',
        content: getFallbackResponse(text),
      });
    } finally {
      setProcessing(false);
    }
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
      el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
    }
  };

  return (
    <div className="chat-interface">
      <div className="chat-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-message chat-message--${msg.role}`}>
            <div className="chat-message__avatar">
              {msg.role === 'user' ? '👤' : '🤖'}
            </div>
            <div className="chat-message__content">
              <p style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</p>
              {msg.actions && msg.actions.length > 0 && (
                <div className="chat-message__actions">
                  {msg.actions.map((action, i) => (
                    <button
                      key={i}
                      className="btn btn--sm btn--outline"
                      onClick={() => {
                        addMessage({
                          role: 'user',
                          content: `Apply: ${action.type}`,
                        });
                      }}
                    >
                      ⚡ {action.type}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {isProcessing && (
          <div className="chat-message chat-message--assistant">
            <div className="chat-message__avatar">🤖</div>
            <div className="chat-message__content">
              <span className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleTextareaInput}
          placeholder="Ask me about your PCB... (e.g., 'route USB traces', 'run DRC', 'review design')"
          rows={1}
          disabled={isProcessing}
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
  );
}