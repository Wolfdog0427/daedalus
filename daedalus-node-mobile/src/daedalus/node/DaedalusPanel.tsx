import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useDaedalus } from '../useDaedalus';

export const DaedalusPanel: React.FC = () => {
  const { posture, identity, continuity, notify } = useDaedalus();

  const setComfort = () => {
    posture.setProfile('default.comfort');
    continuity.markEvent('posture.set.default.comfort');
    notify.info('Posture set to default comfort', { source: 'panel' });
  };

  const setAnalysis = () => {
    posture.setProfile('analysis.focused');
    continuity.markEvent('posture.set.analysis.focused');
    notify.info('Posture set to analysis focused', { source: 'panel' });
  };

  const lockDefense = () => {
    posture.setProfile('defense.locked');
    continuity.markEvent('posture.set.defense.locked');
    notify.warn('Defense posture locked', { source: 'panel' });
  };

  const setOperator = () => {
    identity.setAnchor('operator', 'Wolfdog');
    continuity.markEvent('identity.operator.set', { value: 'Wolfdog' });
    notify.info('Operator anchor set to Wolfdog', { source: 'panel' });
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Daedalus Controls</Text>
      <View style={styles.row}>
        <Button label="Comfort" onPress={setComfort} />
        <Button label="Analysis" onPress={setAnalysis} />
        <Button label="Lock Defense" onPress={lockDefense} />
      </View>
      <View style={styles.row}>
        <Button label="Set Operator" onPress={setOperator} />
      </View>
    </View>
  );
};

const Button: React.FC<{ label: string; onPress: () => void }> = ({ label, onPress }) => (
  <TouchableOpacity style={styles.button} onPress={onPress}>
    <Text style={styles.buttonLabel}>{label}</Text>
  </TouchableOpacity>
);

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
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  button: {
    backgroundColor: '#1C2140',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    marginRight: 8,
    marginBottom: 8,
  },
  buttonLabel: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '500',
  },
});
