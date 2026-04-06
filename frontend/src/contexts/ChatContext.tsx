import { createContext, useContext, useState } from 'react';
import type { ReactNode, FC } from 'react';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatContextType {
  messages: ChatMessage[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: 'Hello! I am your AI Maintenance Copilot from Elicius. I have access to real-time telemetry and RAG document stores (manuals, historical logs). How can I help you analyze the asset today?'
    }
  ]);

  return (
    <ChatContext.Provider value={{ messages, setMessages }}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};
