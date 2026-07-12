import type { FC } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import MotorDetailsSummary from '../common/MotorDetailsSummary';
import ChatBotBubble from '../ai/ChatBotBubble';

const Layout: FC = () => {
  return (
    <div className="flex h-screen text-text-primary overflow-hidden font-sans">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-[1600px] mx-auto h-full flex flex-col space-y-4">
            <MotorDetailsSummary />
            <div className="flex-1 min-h-0">
              <Outlet />
            </div>
          </div>
        </main>
      </div>
      <ChatBotBubble />
    </div>
  );
};

export default Layout;
