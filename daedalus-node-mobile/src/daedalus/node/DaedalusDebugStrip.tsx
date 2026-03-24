import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useDaedalus } from '../useDaedalus';

export const DaedalusDebugStrip: React.FC = () => {
  const { state } = useDaedalus();

  return (
    <View style={styles.container}>
      <Text style={styles.label}>Debug:</Text>
      <Text style={styles.text}>
        posture={state.postureProfile?.id ?? 'none'} | anchors={state.identityAnchors.length} | events={state.continuityEvents.length}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginTop: 8,
    paddingVertical: 6,
  },
  label: {
    color: '#6C7299',
    fontSize: 11,
    marginBottom: 2,
  },
  text: {
    color: '#8F95C2',
    fontSize: 11,
  },
});
