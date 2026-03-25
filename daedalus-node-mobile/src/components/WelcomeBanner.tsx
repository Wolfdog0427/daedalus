import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, spacing, fonts, radius } from '../theme';
import type { ConnectionStatus } from '../daedalus/DaedalusProvider';

interface WelcomeBannerProps {
  operatorName: string | null;
  connection: ConnectionStatus;
  alignment: number | null;
}

function greetingForTime(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

export const WelcomeBanner: React.FC<WelcomeBannerProps> = ({ operatorName, connection, alignment }) => {
  const greeting = greetingForTime();
  const name = operatorName ?? 'Operator';

  return (
    <View style={styles.container}>
      <View style={styles.sigilRow}>
        <View style={styles.sigil}>
          <Text style={styles.sigilText}>{'\u2666'}</Text>
        </View>
        <View style={styles.info}>
          <Text style={styles.greeting}>{greeting}, {name}</Text>
          <Text style={styles.subtitle}>
            {connection === 'connected'
              ? alignment !== null
                ? `Daedalus is aligned at ${alignment}%`
                : 'Daedalus is online'
              : 'Connecting to Daedalus...'}
          </Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
  },
  sigilRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  sigil: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.surfaceElevated,
    borderWidth: 1,
    borderColor: colors.accentBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sigilText: {
    fontSize: 20,
    color: colors.accent,
  },
  info: {
    flex: 1,
    gap: 2,
  },
  greeting: {
    fontSize: fonts.subtitle,
    fontWeight: '600',
    color: colors.text,
  },
  subtitle: {
    fontSize: fonts.body,
    color: colors.textMuted,
  },
});
