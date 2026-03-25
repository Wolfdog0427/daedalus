import React from 'react';
import { ScrollView, View, Text, StyleSheet, RefreshControl } from 'react-native';
import { useDaedalus } from '../daedalus/useDaedalus';
import { NodeIdentityCard } from '../components/NodeIdentityCard';
import { colors, spacing, fonts, radius } from '../theme';

const EventItem: React.FC<{ kind: string; at: number }> = ({ kind, at }) => (
  <View style={styles.eventRow}>
    <View style={styles.eventDot} />
    <View style={styles.eventContent}>
      <Text style={styles.eventKind}>{kind}</Text>
      <Text style={styles.eventTime}>
        {new Date(at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
      </Text>
    </View>
  </View>
);

const DiagnosticRow: React.FC<{ label: string; value: string; status?: 'good' | 'warn' | 'bad' }> = ({ label, value, status }) => {
  const color = status === 'good' ? colors.green : status === 'warn' ? colors.yellow : status === 'bad' ? colors.red : colors.textSecondary;
  return (
    <View style={styles.diagRow}>
      <Text style={styles.diagLabel}>{label}</Text>
      <Text style={[styles.diagValue, { color }]}>{value}</Text>
    </View>
  );
};

export const NodeScreen: React.FC = () => {
  const { connection, state, systemStatus, refreshStatus } = useDaedalus();
  const [refreshing, setRefreshing] = React.useState(false);
  const recent = state.continuityEvents.slice(-20).reverse();

  const onRefresh = React.useCallback(async () => {
    setRefreshing(true);
    await refreshStatus();
    setRefreshing(false);
  }, [refreshStatus]);

  const connStatus = connection === 'connected' ? 'good' : connection === 'error' ? 'bad' : 'warn';

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={colors.accent}
          colors={[colors.accent]}
          progressBackgroundColor={colors.surface}
        />
      }
    >
      <NodeIdentityCard connection={connection} state={state} />

      {/* Diagnostics */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Diagnostics</Text>
        <DiagnosticRow label="Heartbeat" value={connection} status={connStatus} />
        <DiagnosticRow label="Posture" value={state.postureProfile?.label ?? 'None'} />
        <DiagnosticRow label="Defense" value={state.postureProfile?.defenseMode ?? '--'} />
        <DiagnosticRow label="Comfort" value={state.postureProfile?.comfort ?? '--'} />
        <DiagnosticRow label="Autonomy" value={state.postureProfile?.autonomy ?? '--'} />
        {systemStatus && (
          <>
            <View style={styles.diagDivider} />
            <DiagnosticRow
              label="Alignment"
              value={`${systemStatus.alignment}%`}
              status={systemStatus.alignment >= 85 ? 'good' : systemStatus.alignment >= 70 ? 'warn' : 'bad'}
            />
            <DiagnosticRow label="Strategy" value={systemStatus.strategy} />
            <DiagnosticRow
              label="Trust"
              value={`${systemStatus.trustScore} (${systemStatus.trustPosture})`}
              status={systemStatus.trustScore >= 85 ? 'good' : systemStatus.trustScore >= 50 ? 'warn' : 'bad'}
            />
            <DiagnosticRow label="Governance" value={systemStatus.governancePosture} />
            <DiagnosticRow
              label="Safe Mode"
              value={systemStatus.safeModeActive ? 'ACTIVE' : 'Off'}
              status={systemStatus.safeModeActive ? 'bad' : 'good'}
            />
            <DiagnosticRow
              label="Freeze"
              value={systemStatus.freezeFrozen ? 'ACTIVE' : 'Off'}
              status={systemStatus.freezeFrozen ? 'warn' : 'good'}
            />
          </>
        )}
      </View>

      {/* Continuity Timeline */}
      <View style={styles.card}>
        <View style={styles.timelineHeader}>
          <Text style={styles.sectionTitle}>Continuity Timeline</Text>
          <Text style={styles.eventCount}>{state.continuityEvents.length} events</Text>
        </View>
        {recent.length === 0 ? (
          <Text style={styles.empty}>No events recorded yet</Text>
        ) : (
          recent.map(e => <EventItem key={e.id} kind={e.kind} at={e.at} />)
        )}
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  content: {
    padding: spacing.lg,
    gap: spacing.lg,
    paddingBottom: 40,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    gap: spacing.sm,
  },
  sectionTitle: {
    fontSize: fonts.subtitle,
    fontWeight: '600',
    color: colors.text,
    marginBottom: spacing.xs,
  },
  empty: {
    fontSize: fonts.body,
    color: colors.textFaint,
    fontStyle: 'italic',
  },
  eventRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.md,
    paddingVertical: spacing.xs,
  },
  eventDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.accent,
    marginTop: 4,
  },
  eventContent: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
    paddingBottom: spacing.xs,
  },
  eventKind: {
    fontSize: fonts.small,
    color: colors.textSecondary,
    fontFamily: 'monospace',
    flex: 1,
  },
  eventTime: {
    fontSize: fonts.caption,
    color: colors.textFaint,
  },
  diagRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 3,
  },
  diagLabel: {
    fontSize: fonts.body,
    color: colors.textMuted,
  },
  diagValue: {
    fontSize: fonts.body,
    fontWeight: '500',
  },
  diagDivider: {
    height: 1,
    backgroundColor: colors.borderSubtle,
    marginVertical: spacing.xs,
  },
  timelineHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  eventCount: {
    fontSize: fonts.caption,
    color: colors.textFaint,
  },
});
