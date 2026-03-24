import React, { createContext, useContext, useEffect, useState } from "react";
import { IDENTITY } from "../config/identity";
import { createHeartbeatEngine, HeartbeatStatus } from "../services/heartbeat";
import {
  ContinuityState,
  loadContinuity
} from "../services/continuity";
import {
  createPresenceClient,
  JoinStatus
} from "../services/presenceClient";

type DaedalusContextValue = {
  identity: typeof IDENTITY;
  heartbeatStatus: HeartbeatStatus;
  joinStatus: JoinStatus;
  continuity: ContinuityState | null;
  sendJoin: () => void;
};

const DaedalusContext = createContext<DaedalusContextValue | null>(null);

export const useDaedalus = () => {
  const ctx = useContext(DaedalusContext);
  if (!ctx) throw new Error("DaedalusContext not available");
  return ctx;
};

export const DaedalusProvider = ({
  children
}: {
  children: React.ReactNode;
}) => {
  const [heartbeatStatus, setHeartbeatStatus] =
    useState<HeartbeatStatus>("idle");
  const [joinStatus, setJoinStatus] = useState<JoinStatus>("idle");
  const [continuity, setContinuity] = useState<ContinuityState | null>(null);

  const [heartbeat] = useState(() => createHeartbeatEngine());
  const [presence] = useState(() => createPresenceClient());

  useEffect(() => {
    const unsubHb = heartbeat.subscribe(setHeartbeatStatus);
    const unsubJoin = presence.subscribe(setJoinStatus);
    heartbeat.start();
    void (async () => {
      const c = await loadContinuity();
      setContinuity(c);
    })();
    return () => {
      unsubHb();
      unsubJoin();
      heartbeat.stop();
    };
  }, [heartbeat, presence]);

  const sendJoin = () => {
    void presence.sendJoinRequest().then(async () => {
      const c = await loadContinuity();
      setContinuity(c);
    });
  };

  return (
    <DaedalusContext.Provider
      value={{
        identity: IDENTITY,
        heartbeatStatus,
        joinStatus,
        continuity,
        sendJoin
      }}
    >
      {children}
    </DaedalusContext.Provider>
  );
};
