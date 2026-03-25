import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { colors, spacing, fonts, radius } from '../theme';

interface QuickAction {
  icon: string;
  label: string;
  description: string;
  color: string;
  onPress: () => void;
}

const ActionTile: React.FC<QuickAction> = ({ icon, label, description, color, onPress }) => (
  <TouchableOpacity style={styles.tile} onPress={onPress} activeOpacity={0.7}>
    <Text style={[styles.icon, { color }]}>{icon}</Text>
    <Text style={styles.label}>{label}</Text>
    <Text style={styles.description} numberOfLines={1}>{description}</Text>
  </TouchableOpacity>
);

export const QuickActions: React.FC<{
  onChat: () => void;
  onRefresh: () => void;
  onPosture: (id: string) => void;
  onEvolve?: () => void;
}> = ({ onChat, onRefresh, onPosture, onEvolve }) => {
  const actions: QuickAction[] = [
    { icon: '◈', label: 'Evolve', description: 'Proposals & approvals', color: colors.yellow, onPress: onEvolve ?? (() => {}) },
    { icon: '✱', label: 'Chat', description: 'Talk to Daedalus', color: colors.accent, onPress: onChat },
    { icon: '↻', label: 'Refresh', description: 'Update status', color: colors.green, onPress: onRefresh },
    { icon: '◎', label: 'Focus', description: 'Analysis mode', color: colors.purple, onPress: () => onPosture('analysis.focused') },
  ];

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Quick Actions</Text>
      <View style={styles.grid}>
        {actions.map(a => <ActionTile key={a.label} {...a} />)}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    gap: spacing.md,
  },
  title: {
    fontSize: fonts.subtitle,
    fontWeight: '600',
    color: colors.text,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  tile: {
    width: '48%',
    flexGrow: 1,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    gap: spacing.xs,
  },
  icon: {
    fontSize: 20,
  },
  label: {
    fontSize: fonts.body,
    fontWeight: '600',
    color: colors.text,
  },
  description: {
    fontSize: fonts.caption,
    color: colors.textFaint,
  },
});
