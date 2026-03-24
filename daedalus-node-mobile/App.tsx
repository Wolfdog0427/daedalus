import React from "react";
import { SafeAreaView, StyleSheet, Text, View, Button } from "react-native";
import { StatusBar } from "expo-status-bar";
import { DaedalusProvider, useDaedalus } from "./src/context/DaedalusContext";

const HeartbeatBadge: React.FC = () => {
  const { heartbeatStatus } = useDaedalus();
  const color =
    heartbeatStatus === "ok"
      ? "#4ade80"
      : heartbeatStatus === "sending"
      ? "#facc15"
      : heartbeatStatus === "error"
      ? "#f97373"
      : "#6b7280";

  return (
    <View style={[styles.badge, { backgroundColor: color }]}>
      <Text style={styles.badgeText}>Heartbeat: {heartbeatStatus}</Text>
    </View>
  );
};

const JoinBadge: React.FC = () => {
  const { joinStatus } = useDaedalus();
  const color =
    joinStatus === "joined"
      ? "#4ade80"
      : joinStatus === "joining"
      ? "#facc15"
      : joinStatus === "error"
      ? "#f97373"
      : "#6b7280";

  return (
    <View style={[styles.badge, { backgroundColor: color }]}>
      <Text style={styles.badgeText}>Join: {joinStatus}</Text>
    </View>
  );
};

const ContinuityPanel: React.FC = () => {
  const { continuity } = useDaedalus();
  return (
    <View style={styles.panel}>
      <Text style={styles.panelTitle}>Continuity</Text>
      <Text style={styles.panelLine}>
        Last heartbeat: {continuity?.lastHeartbeatAt ?? "\u2014"}
      </Text>
      <Text style={styles.panelLine}>
        Last join: {continuity?.lastJoinAt ?? "\u2014"}
      </Text>
      <Text style={styles.panelLine}>
        Last presence ack: {continuity?.lastPresenceAckAt ?? "\u2014"}
      </Text>
    </View>
  );
};

const IdentityPanel: React.FC = () => {
  const { identity } = useDaedalus();
  return (
    <View style={styles.panel}>
      <Text style={styles.panelTitle}>Identity</Text>
      <Text style={styles.panelLine}>Node: {identity.nodeId}</Text>
      <Text style={styles.panelLine}>Label: {identity.label}</Text>
      <Text style={styles.panelLine}>Operator: {identity.operator}</Text>
      <Text style={styles.panelLine}>
        Device: {identity.deviceType} \u00b7 {identity.platform}
      </Text>
    </View>
  );
};

const JoinControls: React.FC = () => {
  const { sendJoin, joinStatus } = useDaedalus();
  return (
    <View style={styles.panel}>
      <Text style={styles.panelTitle}>Presence</Text>
      <Button
        title={
          joinStatus === "joined"
            ? "Re-send join request"
            : "Send join request"
        }
        onPress={sendJoin}
      />
    </View>
  );
};

const Shell: React.FC = () => {
  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" />
      <Text style={styles.title}>Daedalus \u00b7 Node 1</Text>
      <IdentityPanel />
      <HeartbeatBadge />
      <JoinBadge />
      <ContinuityPanel />
      <JoinControls />
    </SafeAreaView>
  );
};

export default function App() {
  return (
    <DaedalusProvider>
      <Shell />
    </DaedalusProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#020617",
    padding: 16,
    gap: 16
  },
  title: {
    color: "#e5e7eb",
    fontSize: 24,
    fontWeight: "700",
    marginBottom: 8
  },
  badge: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 999,
    alignSelf: "flex-start"
  },
  badgeText: {
    color: "#020617",
    fontWeight: "600"
  },
  panel: {
    backgroundColor: "#020617",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#1f2937",
    padding: 12,
    gap: 4
  },
  panelTitle: {
    color: "#e5e7eb",
    fontWeight: "600",
    marginBottom: 4
  },
  panelLine: {
    color: "#9ca3af",
    fontSize: 13
  }
});
