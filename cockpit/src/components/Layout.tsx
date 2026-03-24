import type { ReactNode } from 'react';

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="layout">
      <header className="layout-header">
        <h1>Daedalus Cockpit</h1>
        <span>v0.4</span>
      </header>
      <div className="grid">{children}</div>
    </div>
  );
}
