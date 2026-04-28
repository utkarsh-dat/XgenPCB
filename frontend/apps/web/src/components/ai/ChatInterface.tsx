import { useState, useRef, useEffect } from 'react';
import { useAIStore, useDesignStore } from '../../stores';
import { api } from '../../lib/api/client';
import { AlertCircle } from 'lucide-react';

interface ChatInterfaceProps {
  designId: string;
}

export function ChatInterface({ designId }: ChatInterfaceProps) {
  const { messages, isProcessing, addMessage, setProcessing } = useAIStore();
  const { currentDesign } = useDesignStore();
  const [input, setInput] = useState('');
  const [error, setError] = useState<string | null>(null);
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
    setError(null);

    if (textareaRef.current) {
      textareaRef.current.style.height = '20px';
    }

    try {
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
    } catch (err: any) {
      setError(err.message || 'Failed to get response. Please try again.');
      addMessage({
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
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
        {error && (
          <div className="chat-message chat-message--error">
            <div className="chat-message__avatar"><AlertCircle className="h-4 w-4" /></div>
            <div className="chat-message__content">
              <p className="text-red-500">{error}</p>
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
