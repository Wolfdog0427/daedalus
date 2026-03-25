import React from 'react';
import { SafeAreaView, View, Text, TouchableOpacity, StyleSheet, StatusBar } from 'react-native';
import { DaedalusProvider } from './src/daedalus/DaedalusProvider';
import { useDaedalus } from './src/daedalus/useDaedalus';
import { ConnectionBar } from './src/components/ConnectionBar';
import { HomeScreen } from './src/screens/HomeScreen';
import { ChatScreen } from './src/screens/ChatScreen';
import { NodeScreen } from './src/screens/NodeScreen';
import { EvolutionScreen } from './src/screens/EvolutionScreen';
import { colors, spacing, fonts } from './src/theme';

type Tab = 'home' | 'evolve' | 'chat' | 'node';

interface TabDef {
  id: Tab;
  label: string;
  icon: string;
}

const TABS: TabDef[] = [
  { id: 'home', label: 'Home', icon: '\u25C9' },
  { id: 'evolve', label: 'Evolve', icon: '\u25C8' },
  { id: 'chat', label: 'Chat', icon: '\u2731' },
  { id: 'node', label: 'Node', icon: '\u2666' },
];

const TabBar: React.FC<{ active: Tab; onSelect: (t: Tab) => void }> = ({ active, onSelect }) => (
  <View style={styles.tabBar}>
    {TABS.map(tab => {
      const isActive = active === tab.id;
      return (
        <TouchableOpacity
          key={tab.id}
          style={styles.tab}
          onPress={() => onSelect(tab.id)}
          activeOpacity={0.7}
        >
          <Text style={[styles.tabIcon, isActive && styles.tabIconActive]}>{tab.icon}</Text>
          <Text style={[styles.tabLabel, isActive && styles.tabLabelActive]}>{tab.label}</Text>
          {isActive && <View style={styles.tabIndicator} />}
        </TouchableOpacity>
      );
    })}
  </View>
);

const AppContent: React.FC = () => {
  const [tab, setTab] = React.useState<Tab>('home');
  const { posture, identity, continuity, notify, connection } = useDaedalus();

  React.useEffect(() => {
    posture.setProfile('default.comfort');
    identity.setAnchor('operator', 'Wolfdog');
    continuity.markEvent('app.launched', { at: Date.now() });
    notify.info('Daedalus node mobile online', { surface: 'app' });
  }, []);

  return (
    <View style={styles.flex}>
      <ConnectionBar status={connection} />

      <View style={styles.flex}>
        {tab === 'home' && <HomeScreen onNavigateChat={() => setTab('chat')} onNavigateEvolve={() => setTab('evolve')} />}
        {tab === 'evolve' && <EvolutionScreen />}
        {tab === 'chat' && <ChatScreen />}
        {tab === 'node' && <NodeScreen />}
      </View>

      <TabBar active={tab} onSelect={setTab} />
    </View>
  );
};

export default function App() {
  return (
    <DaedalusProvider>
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor={colors.bg} />
        <AppContent />
      </SafeAreaView>
    </DaedalusProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  flex: {
    flex: 1,
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingBottom: spacing.sm,
    paddingTop: spacing.xs,
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    gap: 2,
    paddingVertical: spacing.xs + 2,
    position: 'relative',
  },
  tabIcon: {
    fontSize: 18,
    color: colors.textFaint,
  },
  tabIconActive: {
    color: colors.accent,
  },
  tabLabel: {
    fontSize: fonts.micro,
    color: colors.textFaint,
    fontWeight: '500',
  },
  tabLabelActive: {
    color: colors.accent,
  },
  tabIndicator: {
    position: 'absolute',
    top: 0,
    width: 20,
    height: 2,
    borderRadius: 1,
    backgroundColor: colors.accent,
  },
});
