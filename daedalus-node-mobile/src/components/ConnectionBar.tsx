import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, spacing, fonts, radius } from '../theme';
import type { ConnectionStatus } from '../daedalus/DaedalusProvider';

const STATUS_CONFIG: Record<ConnectionStatus, { color: string; label: string }> = {
  connected: { color: colors.green, label: 'Connected' },
  connecting: { color: colors.yellow, label: 'Connecting...' },
  disconnected: { color: colors.textFaint, label: 'Disconnected' },
  error: { color: colors.red, label: 'Connection Error' },
};

export const ConnectionBar: React.FC<{ status: ConnectionStatus }> = ({ status }) => {
  const cfg = STATUS_CONFIG[status];
  return (
    <View style={styles.bar}>
      <View style={[styles.dot, { backgroundColor: cfg.color }]} />
      <Text style={[styles.label, { color: cfg.color }]}>{cfg.label}</Text>
      <Text style={styles.nodeLabel}>Node Mobile</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 4,
  },
  label: {
    fontSize: fonts.caption,
    fontWeight: '500',
  },
  nodeLabel: {
    marginLeft: 'auto',
    fontSize: fonts.caption,
    color: colors.textFaint,
  },
});
