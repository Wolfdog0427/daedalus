import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, spacing, fonts, radius } from '../theme';
import type { ExpressiveState } from '../api/daedalusApi';

const SUB_POSTURE_META: Record<string, { label: string; color: string }> = {
  none: { label: 'Neutral', color: colors.textMuted },
  analytic: { label: 'Analytic', color: colors.accent },
  creative: { label: 'Creative', color: '#a371f7' },
  sensitive: { label: 'Sensitive', color: '#f778ba' },
  defensive: { label: 'Defensive', color: colors.red },
  supportive: { label: 'Supportive', color: colors.green },
};

const OVERLAY_META: Record<string, { label: string; icon: string; color: string }> = {
  none: { label: 'None', icon: '—', color: colors.textMuted },
  focus: { label: 'Focus', icon: '◎', color: colors.accent },
  calm: { label: 'Calm', icon: '◌', color: colors.green },
  alert: { label: 'Alert', icon: '⚠', color: colors.red },
  recovery: { label: 'Recovery', icon: '↻', color: colors.yellow },
  transition: { label: 'Transition', icon: '⇄', color: '#a371f7' },
};

const MicroBar: React.FC<{ label: string; value: number; color: string }> = ({ label, value, color }) => (
  <View style={styles.microRow}>
    <Text style={styles.microLabel}>{label}</Text>
    <View style={styles.microTrack}>
      <View style={[styles.microFill, { width: `${Math.round(value * 100)}%`, backgroundColor: color }]} />
    </View>
    <Text style={[styles.microValue, { color }]}>{Math.round(value * 100)}%</Text>
  </View>
);

interface Props {
  expressive: ExpressiveState;
}

export const ExpressiveCard: React.FC<Props> = ({ expressive }) => {
  const sp = SUB_POSTURE_META[expressive.subPosture] ?? SUB_POSTURE_META.none;
  const ov = OVERLAY_META[expressive.overlay] ?? OVERLAY_META.none;

  return (
    <View style={styles.card}>
      <Text style={styles.title}>Expressive Physiology</Text>

      <View style={styles.stateRow}>
        <View style={styles.stateCell}>
          <Text style={styles.stateLabel}>Sub-Posture</Text>
          <View style={[styles.badge, { backgroundColor: sp.color + '22' }]}>
            <Text style={[styles.badgeText, { color: sp.color }]}>{sp.label}</Text>
          </View>
        </View>

        <View style={styles.stateCell}>
          <Text style={styles.stateLabel}>Overlay</Text>
          <View style={[styles.badge, { backgroundColor: ov.color + '22' }]}>
            <Text style={[styles.badgeText, { color: ov.color }]}>
              {ov.icon} {ov.label}
              {expressive.overlayTicksRemaining > 0 ? ` (${expressive.overlayTicksRemaining}t)` : ''}
            </Text>
          </View>
        </View>
      </View>

      <View style={styles.microSection}>
        <Text style={styles.sectionLabel}>Micro-Posture</Text>
        <MicroBar label="Responsiveness" value={expressive.microPosture.responsiveness} color={colors.accent} />
        <MicroBar label="Ease" value={1 - expressive.microPosture.caution} color={colors.green} />
        <MicroBar label="Expressiveness" value={expressive.microPosture.expressiveness} color="#a371f7" />
      </View>

      {expressive.contextual.reason !== 'idle' && (
        <View style={styles.contextRow}>
          <Text style={styles.contextLabel}>Context</Text>
          <Text style={styles.contextValue}>{expressive.contextual.reason}</Text>
        </View>
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
  title: {
    color: colors.text,
    fontSize: fonts.subtitle,
    fontWeight: '600',
  },
  stateRow: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  stateCell: {
    flex: 1,
    gap: spacing.xs,
  },
  stateLabel: {
    fontSize: fonts.caption,
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  badge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
    borderRadius: radius.pill,
    alignSelf: 'flex-start',
  },
  badgeText: {
    fontSize: fonts.small,
    fontWeight: '600',
  },
  sectionLabel: {
    fontSize: fonts.caption,
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 2,
  },
  microSection: {
    gap: spacing.xs,
  },
  microRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  microLabel: {
    fontSize: fonts.small,
    color: colors.textMuted,
    width: 100,
  },
  microTrack: {
    flex: 1,
    height: 5,
    backgroundColor: colors.borderSubtle,
    borderRadius: 3,
    overflow: 'hidden',
  },
  microFill: {
    height: '100%',
    borderRadius: 3,
  },
  microValue: {
    fontSize: fonts.micro,
    fontWeight: '600',
    width: 36,
    textAlign: 'right',
  },
  contextRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  contextLabel: {
    fontSize: fonts.body,
    color: colors.textMuted,
  },
  contextValue: {
    fontSize: fonts.small,
    color: colors.textSecondary,
    fontWeight: '500',
    flexShrink: 1,
    textAlign: 'right',
  },
});
