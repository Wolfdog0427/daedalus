import React from 'react';
import { ScrollView, RefreshControl, StyleSheet } from 'react-native';
import { useDaedalus } from '../daedalus/useDaedalus';
import { WelcomeBanner } from '../components/WelcomeBanner';
import { StatusCard } from '../components/StatusCard';
import { TrustMeter } from '../components/TrustMeter';
import { PostureSelector } from '../components/PostureSelector';
import { QuickActions } from '../components/QuickActions';
import { ExpressiveCard } from '../components/ExpressiveCard';
import { colors, spacing } from '../theme';

interface HomeScreenProps {
  onNavigateChat: () => void;
  onNavigateEvolve?: () => void;
}

export const HomeScreen: React.FC<HomeScreenProps> = ({ onNavigateChat, onNavigateEvolve }) => {
  const { systemStatus, connection, state, posture, continuity, notify, refreshStatus } = useDaedalus();
  const [refreshing, setRefreshing] = React.useState(false);

  const handlePosture = (id: string) => {
    posture.setProfile(id);
    continuity.markEvent(`posture.set.${id}`);
    notify.info(`Posture set to ${id}`, { source: 'home' });
  };

  const onRefresh = React.useCallback(async () => {
    setRefreshing(true);
    await refreshStatus();
    setRefreshing(false);
  }, [refreshStatus]);

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
      <WelcomeBanner
        operatorName={systemStatus?.operatorName ?? null}
        connection={connection}
        alignment={systemStatus?.alignment ?? null}
      />

      <StatusCard status={systemStatus} loading={connection === 'connecting'} />

      {systemStatus && (
        <TrustMeter
          trustScore={systemStatus.trustScore}
          posture={systemStatus.trustPosture}
          calibrated={systemStatus.trustPosture === 'trusted_canonical'}
          operatorName={systemStatus.operatorName}
        />
      )}

      {systemStatus?.expressive && (
        <ExpressiveCard expressive={systemStatus.expressive} />
      )}

      <QuickActions
        onChat={onNavigateChat}
        onEvolve={onNavigateEvolve}
        onRefresh={onRefresh}
        onPosture={handlePosture}
      />

      <PostureSelector activeProfile={state.postureProfile} onSelect={handlePosture} />
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
});
