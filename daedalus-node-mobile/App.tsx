import React from 'react';
import { SafeAreaView, View, Text, StyleSheet, StatusBar } from 'react-native';
import { DaedalusProvider } from './src/daedalus/DaedalusProvider';
import { DaedalusPanel } from './src/daedalus/node/DaedalusPanel';
import { DaedalusDebugStrip } from './src/daedalus/node/DaedalusDebugStrip';
import { useDaedalus } from './src/daedalus/useDaedalus';

const Home: React.FC = () => {
  const { posture, identity, continuity, notify } = useDaedalus();

  React.useEffect(() => {
    posture.setProfile('default.comfort');
    identity.setAnchor('operator', 'Wolfdog');
    continuity.markEvent('app.home.mounted', { at: Date.now() });
    notify.info('Daedalus node mobile online', { surface: 'home' });
  }, [posture, identity, continuity, notify]);

  return (
    <View style={styles.content}>
      <Text style={styles.title}>Daedalus Node — Mobile</Text>
      <DaedalusPanel />
      <DaedalusDebugStrip />
    </View>
  );
};

export default function App() {
  return (
    <DaedalusProvider>
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" />
        <Home />
      </SafeAreaView>
    </DaedalusProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#05060A',
  },
  content: {
    flex: 1,
    paddingTop: 32,
    paddingHorizontal: 16,
  },
  title: {
    color: '#FFFFFF',
    fontSize: 24,
    fontWeight: '600',
    marginBottom: 16,
  },
});
