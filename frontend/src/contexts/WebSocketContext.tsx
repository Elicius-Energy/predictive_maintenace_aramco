import { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import type { ReactNode, FC } from 'react';
import { WS_URL } from '../utils/constants';
import type { WSMessage } from '../types';
import { getAccessToken } from '../utils/api';
import { useAuth } from './AuthContext';

type MessageListener = (msg: WSMessage) => void;

interface WebSocketContextType {
  subscribe: (listener: MessageListener) => () => void;
  isConnected: boolean;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const listenersRef = useRef<Set<MessageListener>>(new Set());
  const { isAuthenticated } = useAuth();

  const subscribe = useCallback((listener: MessageListener) => {
    listenersRef.current.add(listener);
    return () => {
      listenersRef.current.delete(listener);
    };
  }, []);

  const connect = useCallback(() => {
    // Only connect if authenticated
    if (!isAuthenticated) return;
    
    if (socketRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const token = getAccessToken();
      // Add token query parameter for authentication
      const wsUrl = token ? `${WS_URL}?token=${token}` : WS_URL;
      
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          listenersRef.current.forEach(listener => listener(message));
        } catch (err) {
          console.error('Failed to parse WS message:', err);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Only attempt reconnect if still authenticated
        if (getAccessToken()) {
          reconnectTimeoutRef.current = window.setTimeout(connect, 5000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      if (getAccessToken()) {
        reconnectTimeoutRef.current = window.setTimeout(connect, 5000);
      }
    }
  }, [isAuthenticated]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      socketRef.current?.close();
    };
  }, [connect, isAuthenticated]);

  return (
    <WebSocketContext.Provider value={{ subscribe, isConnected }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

