import { Layout } from './components/Layout';
import { HealthPanel } from './components/HealthPanel';
import { GlowPanel } from './components/GlowPanel';
import { RiskPanel } from './components/RiskPanel';
import { StatePanel } from './components/StatePanel';
import { NodesPanel } from './components/NodesPanel';
import { NodeCapabilitiesPanel } from './components/NodeCapabilitiesPanel';
import { CapabilitiesPanel } from './components/CapabilitiesPanel';
import { ProfilesPanel } from './components/ProfilesPanel';
import { EventsPanel } from './components/EventsPanel';
import { EchoCommandPanel } from './components/EchoCommandPanel';
import { NotificationsPanel } from './components/NotificationsPanel';
import { ContinuityTimelinePanel } from './components/ContinuityTimelinePanel';

export function App() {
  return (
    <Layout>
      <HealthPanel />
      <GlowPanel />
      <RiskPanel />
      <CapabilitiesPanel />
      <ProfilesPanel />
      <StatePanel />
      <NodesPanel />
      <NodeCapabilitiesPanel />
      <EventsPanel />
      <EchoCommandPanel />
      <NotificationsPanel />
      <ContinuityTimelinePanel />
    </Layout>
  );
}
