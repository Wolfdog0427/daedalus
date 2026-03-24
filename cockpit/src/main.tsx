import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import { DaedalusEventsProvider } from './contexts/DaedalusEventsContext';
import './styles/global.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <DaedalusEventsProvider>
      <App />
    </DaedalusEventsProvider>
  </StrictMode>,
);
