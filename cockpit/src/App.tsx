import { Layout } from './components/Layout';
import DaedalusOrchestratorPanel from './components/DaedalusOrchestratorPanel';
import { CockpitNodeListPanel } from './components/CockpitNodeListPanel';
import { ConstitutionPanel } from './components/ConstitutionPanel';
import { SummaryPanel } from './components/SummaryPanel';
import { IncidentPanel } from './components/IncidentPanel';
import { EventHistoryPanel } from './components/EventHistoryPanel';
import { ActionLogPanel } from './components/ActionLogPanel';
import { StrategyPanel } from './components/StrategyPanel';
import { AlignmentControls } from './components/AlignmentControls';
import { ApprovalGatePanel } from './components/ApprovalGatePanel';
import { RegulationPanel } from './components/RegulationPanel';
import { ChangeRegistryPanel } from './components/ChangeRegistryPanel';
import { OperatorTrustPanel } from './components/OperatorTrustPanel';
import { DaedalusChatPanel } from './components/DaedalusChatPanel';
import { EvolutionPanel } from './components/EvolutionPanel';

export function App() {
  return (
    <>
      <Layout>
        <SummaryPanel />
        <EvolutionPanel />
        <DaedalusOrchestratorPanel />
        <div className="grid-row-2col">
          <StrategyPanel />
          <IncidentPanel />
        </div>
        <CockpitNodeListPanel />
        <OperatorTrustPanel />
        <div className="grid-row-2col">
          <AlignmentControls />
          <ConstitutionPanel />
        </div>
        <div className="grid-row-2col">
          <RegulationPanel />
          <ApprovalGatePanel />
        </div>
        <ChangeRegistryPanel />
        <div className="grid-row-2col">
          <EventHistoryPanel />
          <ActionLogPanel />
        </div>
      </Layout>
      <DaedalusChatPanel />
    </>
  );
}
