import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, spacing, fonts, radius } from '../theme';
import type { SystemStatus } from '../api/daedalusApi';

function formatTimeAgo(iso: string): string {
  try {
    const diff = Date.now() - new Date(iso).getTime();
    if (diff < 5_000) return 'just now';
    if (diff < 60_000) return `${Math.floor(diff / 1000)}s ago`;
    if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function alignmentColor(v: number): string {
  if (v >= 85) return colors.green;
  if (v >= 70) return colors.yellow;
  return colors.red;
}

function postureColor(p: string): string {
  switch (p) {
    case 'trusted_canonical': return colors.green;
    case 'trusted_uncalibrated': return colors.accent;
    case 'cautious': return colors.yellow;
    case 'hostile_or_unknown': return colors.red;
    default: return colors.textMuted;
  }
}

const ProgressBar: React.FC<{ value: number; color: string }> = ({ value, color }) => (
  <View style={styles.progressTrack}>
    <View style={[styles.progressFill, { width: `${Math.min(100, Math.max(0, value))}%`, backgroundColor: color }]} />
  </View>
);

const Row: React.FC<{ label: string; value: string; color?: string }> = ({ label, value, color }) => (
  <View style={styles.row}>
    <Text style={styles.rowLabel}>{label}</Text>
    <Text style={[styles.rowValue, color ? { color } : undefined]}>{value}</Text>
  </View>
);

export const StatusCard: React.FC<{ status: SystemStatus | null; loading?: boolean }> = ({ status, loading }) => {
  if (!status) {
    return (
      <View style={styles.card}>
        <Text style={styles.title}>System Status</Text>
        <Text style={styles.loading}>{loading ? 'Connecting to Daedalus...' : 'No data yet'}</Text>
      </View>
    );
  }

  const alColor = alignmentColor(status.alignment);

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.title}>System Status</Text>
        <View style={[styles.badge, { backgroundColor: alColor + '22' }]}>
          <Text style={[styles.badgeText, { color: alColor }]}>{status.alignment}%</Text>
        </View>
      </View>

      <View style={styles.alignmentSection}>
        <Text style={styles.alignmentLabel}>Alignment</Text>
        <ProgressBar value={status.alignment} color={alColor} />
      </View>

      <Row label="Strategy" value={status.strategy} />
      <Row label="Confidence" value={`${status.confidence}%`} />
      <Row
        label="Operator"
        value={status.operatorBound ? (status.operatorName ?? 'Bound') : 'Unbound'}
        color={status.operatorBound ? colors.green : colors.textMuted}
      />
      <Row
        label="Trust"
        value={status.trustPosture}
        color={postureColor(status.trustPosture)}
      />
      <Row label="Governance" value={status.governancePosture} />

      {status.safeModeActive && (
        <View style={styles.alert}>
          <Text style={styles.alertText}>Safe Mode Active</Text>
        </View>
      )}
      {status.freezeFrozen && (
        <View style={[styles.alert, { backgroundColor: colors.yellowDim }]}>
          <Text style={[styles.alertText, { color: colors.yellow }]}>Constitutional Freeze</Text>
        </View>
      )}

      {status.lastUpdated && (
        <Text style={styles.updated}>
          Updated {formatTimeAgo(status.lastUpdated)}
        </Text>
      )}
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
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    color: colors.text,
    fontSize: fonts.subtitle,
    fontWeight: '600',
  },
  loading: {
    color: colors.textMuted,
    fontSize: fonts.body,
    fontStyle: 'italic',
  },
  badge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radius.pill,
  },
  badgeText: {
    fontSize: fonts.small,
    fontWeight: '700',
  },
  alignmentSection: {
    gap: spacing.xs,
  },
  alignmentLabel: {
    fontSize: fonts.caption,
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  progressTrack: {
    height: 6,
    backgroundColor: colors.borderSubtle,
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 3,
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
  alert: {
    backgroundColor: colors.redDim,
    borderRadius: radius.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  alertText: {
    fontSize: fonts.small,
    color: colors.red,
    fontWeight: '600',
    textAlign: 'center',
  },
  updated: {
    fontSize: fonts.micro,
    color: colors.textFaint,
    textAlign: 'right',
  },
});
