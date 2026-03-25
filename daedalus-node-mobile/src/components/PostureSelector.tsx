import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { colors, spacing, fonts, radius } from '../theme';
import type { PostureProfile } from '../daedalus/types';

interface PostureOption {
  id: string;
  label: string;
  icon: string;
  color: string;
}

const OPTIONS: PostureOption[] = [
  { id: 'default.comfort', label: 'Comfort', icon: '\u25C9', color: colors.green },
  { id: 'analysis.focused', label: 'Analysis', icon: '\u25CE', color: colors.accent },
  { id: 'defense.locked', label: 'Defense', icon: '\u25C8', color: colors.red },
];

export const PostureSelector: React.FC<{
  activeProfile: PostureProfile | null;
  onSelect: (id: string) => void;
}> = ({ activeProfile, onSelect }) => {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>Posture</Text>
      <View style={styles.row}>
        {OPTIONS.map(opt => {
          const active = activeProfile?.id === opt.id;
          return (
            <TouchableOpacity
              key={opt.id}
              style={[
                styles.button,
                active && { borderColor: opt.color, backgroundColor: opt.color + '15' },
              ]}
              onPress={() => onSelect(opt.id)}
              activeOpacity={0.7}
            >
              <Text style={[styles.icon, { color: active ? opt.color : colors.textFaint }]}>{opt.icon}</Text>
              <Text style={[styles.label, active && { color: opt.color }]}>{opt.label}</Text>
            </TouchableOpacity>
          );
        })}
      </View>
      {activeProfile && (
        <Text style={styles.description}>{activeProfile.description}</Text>
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
  row: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  button: {
    flex: 1,
    alignItems: 'center',
    gap: spacing.xs,
    paddingVertical: spacing.md,
    backgroundColor: colors.buttonBg,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: 'transparent',
  },
  icon: {
    fontSize: 20,
  },
  label: {
    fontSize: fonts.small,
    fontWeight: '500',
    color: colors.textSecondary,
  },
  description: {
    fontSize: fonts.caption,
    color: colors.textFaint,
    fontStyle: 'italic',
  },
});
