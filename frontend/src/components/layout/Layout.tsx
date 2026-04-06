import type { FC } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

const Layout: FC = () => {
  return (
    <div className="flex h-screen bg-surface-alt text-text-primary overflow-hidden font-sans">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6 bg-surface-muted">
          <div className="max-w-[1600px] mx-auto min-h-full">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
