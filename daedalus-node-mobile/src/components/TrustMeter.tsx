import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, spacing, fonts, radius } from '../theme';

interface TrustMeterProps {
  trustScore: number;
  posture: string;
  calibrated: boolean;
  operatorName: string | null;
}

function scoreColor(v: number): string {
  if (v >= 85) return colors.green;
  if (v >= 60) return colors.yellow;
  if (v > 0) return colors.red;
  return colors.textFaint;
}

function postureLabel(p: string): string {
  switch (p) {
    case 'trusted_canonical': return 'Trusted';
    case 'trusted_uncalibrated': return 'Calibrating';
    case 'cautious': return 'Cautious';
    case 'hostile_or_unknown': return 'Unknown';
    case 'unbound': return 'Unbound';
    default: return p;
  }
}

export const TrustMeter: React.FC<TrustMeterProps> = ({ trustScore, posture, calibrated, operatorName }) => {
  const color = scoreColor(trustScore);
  const pLabel = postureLabel(posture);

  const segments = 20;
  const filled = Math.round((trustScore / 100) * segments);

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.title}>Operator Trust</Text>
        <Text style={[styles.score, { color }]}>{trustScore}</Text>
      </View>

      <View style={styles.barRow}>
        {Array.from({ length: segments }, (_, i) => (
          <View
            key={i}
            style={[
              styles.segment,
              { backgroundColor: i < filled ? color : colors.borderSubtle },
            ]}
          />
        ))}
      </View>

      <View style={styles.details}>
        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>Posture</Text>
          <View style={[styles.postureTag, { borderColor: color }]}>
            <Text style={[styles.postureText, { color }]}>{pLabel}</Text>
          </View>
        </View>
        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>Operator</Text>
          <Text style={styles.detailValue}>{operatorName ?? 'None'}</Text>
        </View>
        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>Calibrated</Text>
          <Text style={[styles.detailValue, { color: calibrated ? colors.green : colors.textFaint }]}>
            {calibrated ? 'Yes' : 'No'}
          </Text>
        </View>
      </View>
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
    fontSize: fonts.subtitle,
    fontWeight: '600',
    color: colors.text,
  },
  score: {
    fontSize: 28,
    fontWeight: '700',
    fontVariant: ['tabular-nums'],
  },
  barRow: {
    flexDirection: 'row',
    gap: 2,
    height: 8,
  },
  segment: {
    flex: 1,
    borderRadius: 2,
  },
  details: {
    gap: spacing.sm,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  detailLabel: {
    fontSize: fonts.body,
    color: colors.textMuted,
  },
  detailValue: {
    fontSize: fonts.body,
    color: colors.textSecondary,
    fontWeight: '500',
  },
  postureTag: {
    borderWidth: 1,
    borderRadius: radius.pill,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: 1,
  },
  postureText: {
    fontSize: fonts.small,
    fontWeight: '600',
  },
});
