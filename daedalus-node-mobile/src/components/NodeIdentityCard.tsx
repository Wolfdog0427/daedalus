import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, spacing, fonts, radius } from '../theme';
import { IDENTITY } from '../config/identity';
import type { ConnectionStatus } from '../daedalus/DaedalusProvider';
import type { DaedalusState } from '../daedalus/types';

const Row: React.FC<{ label: string; value: string; color?: string }> = ({ label, value, color }) => (
  <View style={styles.row}>
    <Text style={styles.rowLabel}>{label}</Text>
    <Text style={[styles.rowValue, color ? { color } : undefined]}>{value}</Text>
  </View>
);

export const NodeIdentityCard: React.FC<{
  connection: ConnectionStatus;
  state: DaedalusState;
}> = ({ connection, state }) => {
  const summary = state.continuityEvents.length;
  const trajectory = summary === 0
    ? 'idle'
    : state.continuityEvents[summary - 1]?.kind.includes('error')
      ? 'risk'
      : 'flow';

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View style={styles.sigil}>
          <Text style={styles.sigilText}>{'\u2666'}</Text>
        </View>
        <View style={styles.headerInfo}>
          <Text style={styles.name}>{IDENTITY.label}</Text>
          <Text style={styles.nodeId}>{IDENTITY.nodeId}</Text>
        </View>
      </View>

      <View style={styles.divider} />

      <Row label="Platform" value={`${IDENTITY.platform} · ${IDENTITY.deviceType}`} />
      <Row label="Operator" value={IDENTITY.operator} color={colors.accent} />
      <Row label="Posture" value={state.postureProfile?.label ?? 'None'} />
      <Row label="Anchors" value={String(state.identityAnchors.length)} />
      <Row label="Events" value={`${summary} (${trajectory})`} />
      <Row
        label="Connection"
        value={connection}
        color={connection === 'connected' ? colors.green : connection === 'error' ? colors.red : colors.textMuted}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    gap: spacing.md,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  sigil: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.surfaceElevated,
    borderWidth: 1,
    borderColor: colors.accentBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sigilText: {
    fontSize: 18,
    color: colors.accent,
  },
  headerInfo: {
    flex: 1,
  },
  name: {
    fontSize: fonts.subtitle,
    fontWeight: '600',
    color: colors.text,
  },
  nodeId: {
    fontSize: fonts.caption,
    color: colors.textFaint,
    fontFamily: 'monospace',
  },
  divider: {
    height: 1,
    backgroundColor: colors.borderSubtle,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  rowLabel: {
    fontSize: fonts.body,
    color: colors.textMuted,
  },
  rowValue: {
    fontSize: fonts.body,
    color: colors.textSecondary,
    fontWeight: '500',
  },
});
