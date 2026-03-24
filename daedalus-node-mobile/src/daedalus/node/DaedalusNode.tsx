import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useDaedalus } from '../useDaedalus';
import { summarizeContinuity, deriveTrajectory } from '../continuity';

export const DaedalusNode: React.FC = () => {
  const { state } = useDaedalus();
  const summary = summarizeContinuity(state.continuityEvents);
  const trajectory = deriveTrajectory(state.continuityEvents);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Daedalus Node</Text>
      <Text style={styles.line}>
        Posture: {state.postureProfile?.label ?? 'None'}
      </Text>
      <Text style={styles.line}>
        Identity anchors: {state.identityAnchors.length}
      </Text>
      <Text style={styles.line}>
        Continuity events: {summary.count} (trajectory: {trajectory})
      </Text>
      {summary.lastEvent && (
        <Text style={styles.line}>
          Last event: {summary.lastEvent.kind} @ {new Date(summary.lastEvent.at).toLocaleTimeString()}
        </Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    borderRadius: 12,
    padding: 16,
    backgroundColor: '#0B0D16',
    borderWidth: 1,
    borderColor: '#262A3F',
    marginBottom: 16,
  },
  title: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 8,
  },
  line: {
    color: '#C3C7E0',
    fontSize: 14,
    marginBottom: 4,
  },
});
