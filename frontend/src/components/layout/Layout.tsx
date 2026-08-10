import type { FC } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import MotorDetailsSummary from '../common/MotorDetailsSummary';
import ChatBotBubble from '../ai/ChatBotBubble';

const Layout: FC = () => {
  return (
    <>
      {/* Static background image instead of 3D canvas */}
      <div className="static-bg" />

      <div className="flex h-screen text-text-primary overflow-hidden font-sans relative z-10">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <Topbar />
          <main className="flex-1 overflow-y-auto p-5">
            <div className="max-w-[1600px] mx-auto space-y-4">
              <MotorDetailsSummary />
              <Outlet />
            </div>
          </main>
        </div>
        <ChatBotBubble />
      </div>
    </>
  );
};

export default Layout;
