import { useState, useRef, useEffect } from 'react';
import type { FC } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { useChat } from '../../contexts/ChatContext';
import { useMachine } from '../../contexts/MachineContext';
import api from '../../utils/api';
import { MessageSquare, X, Send, User, Bot } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const ChatBotBubble: FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  
  const { messages, setMessages } = useChat();
  const { activeMachine } = useMachine();
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen, isTyping]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = chatInput.trim();
    const currentHistory = [...messages];

    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setChatInput('');
    setIsTyping(true);

    try {
      const response = await api.post('/api/rag/chat', {
        message: userMsg,
        machine_id: activeMachine?.machine_id || 'sim-pump-001',
        history: currentHistory
      });

      setMessages(prev => [...prev, { role: 'assistant', content: response.data.response }]);
    } catch (err: any) {
      console.error('Chat Error:', err);
      let errorMsg = 'I managed to encounter an error connecting to the AI server. Please ensure the backend is running with a valid OpenAI API key.';
      if (err.response && err.response.status === 429) {
        errorMsg = 'Rate limit exceeded. Please wait a moment before sending another message.';
      } else if (err.response && err.response.status === 401) {
        errorMsg = 'Session expired. Please log in again.';
      }
      
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: errorMsg
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <>
      {/* Floating Action Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "fixed bottom-6 right-6 w-14 h-14 rounded-full flex items-center justify-center text-white shadow-xl transition-all duration-300 z-50",
          isOpen ? "bg-accent-red hover:bg-red-700 rotate-90" : "bg-primary hover:bg-primary-dark"
        )}
      >
        {isOpen ? <X size={24} /> : <MessageSquare size={24} />}
      </button>

      {/* Chat Window */}
      <div
        className={cn(
          "fixed bottom-24 right-6 w-96 max-w-[calc(100vw-3rem)] h-[500px] max-h-[calc(100vh-8rem)] bg-surface border border-border rounded-2xl shadow-2xl flex flex-col z-50 transition-all duration-300 origin-bottom-right",
          isOpen ? "scale-100 opacity-100" : "scale-0 opacity-0 pointer-events-none"
        )}
      >
        {/* Header */}
        <div className="p-4 border-b border-border bg-gradient-to-r from-primary to-cyan-500 rounded-t-2xl flex items-center gap-3">
          <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
            <Bot size={18} className="text-white" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">AI Maintenance Assistant</h3>
            <p className="text-[10px] text-cyan-100">Powered by Elicius Energy</p>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-surface-muted/50">
          {messages.length === 0 && (
            <div className="text-center text-text-muted text-sm mt-4">
              Hello! Ask me about machine health, efficiency optimization, or maintenance records.
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={cn("flex gap-2", msg.role === 'user' ? "flex-row-reverse" : "flex-row")}>
              <div className={cn(
                "w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-1",
                msg.role === 'user' ? "bg-primary text-white" : "bg-cyan-100 text-primary border border-cyan-200"
              )}>
                {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
              </div>
              <div className={cn(
                "max-w-[80%] p-3 rounded-2xl text-sm leading-relaxed",
                msg.role === 'user'
                  ? "bg-primary text-white rounded-tr-none shadow-md shadow-primary/20"
                  : "bg-surface text-text-primary rounded-tl-none border border-border shadow-sm"
              )}>
                <div className={cn("prose prose-sm max-w-none break-words overflow-x-auto", msg.role === 'user' ? "prose-invert" : "prose-p:leading-relaxed prose-pre:bg-surface-muted prose-pre:border prose-pre:border-border")}>
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm, remarkMath]} 
                    rehypePlugins={[rehypeKatex]}
                  >
                    {msg.content.replace(/\\\[/g, () => '$$').replace(/\\\]/g, () => '$$').replace(/\\\(/g, () => '$').replace(/\\\)/g, () => '$')}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex gap-2 flex-row">
              <div className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-1 bg-cyan-100 text-primary border border-cyan-200">
                <Bot size={14} />
              </div>
              <div className="max-w-[80%] p-4 rounded-2xl bg-surface text-text-primary rounded-tl-none border border-border shadow-sm flex gap-1 items-center">
                <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce delay-75" />
                <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce delay-150" />
                <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce delay-300" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-3 bg-surface border-t border-border rounded-b-2xl">
          <form onSubmit={handleSendMessage} className="relative flex items-center">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Type your message..."
              className="w-full bg-surface-muted border border-border rounded-xl pl-4 pr-12 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 text-text-primary"
            />
            <button
              type="submit"
              disabled={!chatInput.trim() || isTyping}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors disabled:opacity-50"
            >
              <Send size={14} />
            </button>
          </form>
        </div>
      </div>
    </>
  );
};

export default ChatBotBubble;
