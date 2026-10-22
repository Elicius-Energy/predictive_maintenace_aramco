import React from 'react';

/** Quiet industrial-toned backdrop beneath the application content. */
export const AppBackdrop: React.FC = () => (
  <div
    aria-hidden="true"
    className="fixed inset-0 z-0 overflow-hidden pointer-events-none bg-[#fdfcf9]"
  />
);
