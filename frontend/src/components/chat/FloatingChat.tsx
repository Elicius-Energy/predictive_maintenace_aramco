import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send, Bot, User, Sparkles, RefreshCw } from 'lucide-react';
import { useDevice } from '../../contexts/DeviceContext';
import ReactMarkdown from 'react-markdown';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export const FloatingChat: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: 'Hello! I am your **Elicius Energy Assistant**. Ask me anything about motor consumption, active wiring faults, or report generation.'
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const { selectedDevice, selectedDeviceId } = useDevice();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (messagesEndRef.current?.scrollIntoView) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const handleSend = async (textToSend?: string) => {
    const text = textToSend || inputValue.trim();
    if (!text || isStreaming) return;

    const userMsg: ChatMessage = { role: 'user', content: text };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    if (!textToSend) setInputValue('');
    setIsStreaming(true);

    const assistantMsgIndex = newMessages.length;
    setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);
    const controller = new AbortController();
    const requestTimeout = window.setTimeout(() => controller.abort(), 90000);

    try {
      const userTz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Kolkata';

      // Ensure CSRF token is available when running in browser
      let csrfToken = '';
      const match = document.cookie
        .split('; ')
        .find((part) => part.startsWith('elicius_csrf=') || part.startsWith('ledl_csrf='));
      if (match) {
        csrfToken = decodeURIComponent(match.split('=').slice(1).join('='));
      }
      if (!csrfToken) {
        try {
          await fetch('/api/auth/me', { credentials: 'include' });
          const retryMatch = document.cookie
            .split('; ')
            .find((part) => part.startsWith('elicius_csrf=') || part.startsWith('ledl_csrf='));
          if (retryMatch) {
            csrfToken = decodeURIComponent(retryMatch.split('=').slice(1).join('='));
          }
        } catch {
          // ignore error if auth check fails
        }
      }

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
      }

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers,
        credentials: 'include',
        signal: controller.signal,
        body: JSON.stringify({
          messages: newMessages.slice(-16).map((m) => ({ role: m.role, content: m.content.slice(-1400) })),
          device_id: selectedDeviceId,
          timezone: userTz,
        }),
      });

      if (!response.ok) {
        let errorDetail = '';
        try {
          const errData = await response.json();
          errorDetail = errData.detail || errData.message || '';
        } catch {
          // Response was not JSON
        }
        throw new Error(errorDetail || `Chat service returned HTTP ${response.status}`);
      }

      if (!response.body) {
        throw new Error('No response body from server');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let accumulated = '';
      let buffer = '';
      let streamFinished = false;

      while (!streamFinished) {
        const { value, done } = await reader.read();
        if (done) {
          buffer += decoder.decode();
          if (buffer.trim()) {
            const finalLines = buffer.split('\n');
            for (const line of finalLines) {
              if (line.startsWith('data: ')) {
                const payload = line.slice(6).trim();
                if (payload && payload !== '[DONE]') {
                  try {
                    const parsed = JSON.parse(payload);
                    if (parsed.content) accumulated += parsed.content;
                  } catch { /* Ignore an incomplete trailing SSE frame. */ }
                }
              }
            }
          }
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const event of events) {
          const dataStr = event.split('\n').find((line) => line.startsWith('data: '))?.slice(6).trim();
          if (!dataStr) continue;
          if (dataStr === '[DONE]') {
            streamFinished = true;
            break;
          }
          try {
            const parsed = JSON.parse(dataStr);
            if (parsed.content) {
              accumulated += parsed.content;
              setMessages((prev) => {
                const updated = [...prev];
                updated[assistantMsgIndex] = {
                  role: 'assistant',
                  content: accumulated,
                };
                return updated;
              });
            }
          } catch {
            // Ignore malformed SSE events; continue reading subsequent frames.
          }
        }

        if (streamFinished) {
          await reader.cancel();
        }
      }

      if (!accumulated.trim()) {
        setMessages((prev) => {
          const updated = [...prev];
          updated[assistantMsgIndex] = {
            role: 'assistant',
            content: 'The chat service ended without a reply. Please try again.',
          };
          return updated;
        });
      } else {
        setMessages((prev) => {
          const updated = [...prev];
          updated[assistantMsgIndex] = { role: 'assistant', content: accumulated };
          return updated;
        });
      }
    } catch (err: any) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[assistantMsgIndex] = {
          role: 'assistant',
          content: err.name === 'AbortError'
            ? 'The chat request timed out. Please try again with a shorter question.'
            : `Connection error: ${err.message || 'Could not communicate with chat service.'}`,
        };
        return updated;
      });
    } finally {
      window.clearTimeout(requestTimeout);
      setIsStreaming(false);
    }
  };

  return (
    <>
      {/* Floating Action Button (bottom-right) */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-50 flex items-center justify-center w-14 h-14 rounded-full bg-[#1F3A8A] text-white shadow-xl hover:bg-[#1E3A8A] hover:scale-105 active:scale-95 transition-all cursor-pointer focus:outline-hidden"
        title="Open AI Diagnostics Assistant"
      >
        {isOpen ? <X className="w-6 h-6" /> : <MessageSquare className="w-6 h-6" />}
      </button>

      {/* Slide-out Chat Drawer / Window */}
      {isOpen && (
        <div className="fixed bottom-24 right-6 z-50 w-[92vw] sm:w-[420px] h-[580px] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-200">
          
          {/* Header */}
          <div className="bg-[#1F3A8A] text-white px-4 py-3.5 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div>
                <div className="text-sm font-bold flex items-center gap-1.5 leading-tight">
                  Elicius AI Assistant
                  <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                </div>
                <div className="text-[11px] text-slate-200 font-medium leading-tight mt-0.5">
                  Device: {selectedDevice?.alias || selectedDeviceId.slice(-6)}
                </div>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-white/80 hover:text-white p-1 rounded-md transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Messages History */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3.5 bg-slate-50 text-xs">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex gap-2.5 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {m.role === 'assistant' && (
                  <div className="w-6 h-6 rounded-full bg-[#1F3A8A] text-white flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="w-3.5 h-3.5" />
                  </div>
                )}
                <div
                  className={`max-w-[82%] px-3.5 py-2.5 rounded-xl shadow-2xs leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-[#1F3A8A] text-white rounded-br-2xs'
                      : 'bg-white text-slate-800 border border-slate-200 rounded-bl-2xs'
                  }`}
                >
                  <div className="markdown-content prose prose-xs prose-slate max-w-none">
                    <ReactMarkdown>{m.content}</ReactMarkdown>
                  </div>
                </div>
                {m.role === 'user' && (
                  <div className="w-6 h-6 rounded-full bg-slate-300 text-slate-700 flex items-center justify-center shrink-0 mt-0.5">
                    <User className="w-3.5 h-3.5" />
                  </div>
                )}
              </div>
            ))}

            {isStreaming && (
              <div className="flex items-center gap-2 text-slate-400 text-[11px] pl-8">
                <RefreshCw className="w-3 h-3 animate-spin" />
                Analyzing motor telemetry...
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Box */}
          <div className="p-3 bg-white border-t border-slate-200">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Ask about motor energy, alerts, or reports..."
                disabled={isStreaming}
                className="flex-1 text-xs border border-slate-300 rounded-lg px-3 py-2 focus:outline-hidden focus:border-[#1F3A8A] focus:ring-1 focus:ring-[#1F3A8A]"
              />
              <button
                type="submit"
                disabled={!inputValue.trim() || isStreaming}
                className="p-2 rounded-lg bg-[#1F3A8A] text-white hover:bg-[#1E3A8A] disabled:opacity-40 transition-colors cursor-pointer"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>

        </div>
      )}
    </>
  );
};
