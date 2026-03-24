import { Layout } from './components/Layout';
import DaedalusOrchestratorPanel from './components/DaedalusOrchestratorPanel';
import { CockpitNodeListPanel } from './components/CockpitNodeListPanel';
import { ConstitutionPanel } from './components/ConstitutionPanel';
import { SummaryPanel } from './components/SummaryPanel';
import { IncidentPanel } from './components/IncidentPanel';
import { EventHistoryPanel } from './components/EventHistoryPanel';
import { ActionLogPanel } from './components/ActionLogPanel';

export function App() {
  return (
    <Layout>
      <SummaryPanel />
      <DaedalusOrchestratorPanel />
      <IncidentPanel />
      <CockpitNodeListPanel />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <EventHistoryPanel />
        <ActionLogPanel />
      </div>
      <ConstitutionPanel />
    </Layout>
  );
}
