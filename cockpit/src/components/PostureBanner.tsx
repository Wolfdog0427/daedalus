import { useEffect, useState } from "react";
import { fetchPosture } from "../api/daedalusClient";
import { useDaedalusEvents } from "../hooks/useDaedalusEvents";
import type { PostureSnapshot } from "../shared/daedalus/contracts";
import "./PostureBanner.css";

export function PostureBanner() {
  const [snapshot, setSnapshot] = useState<PostureSnapshot | null>(null);

  useEffect(() => {
    fetchPosture().then(setSnapshot).catch(() => {});
  }, []);

  useDaedalusEvents((event) => {
    if (event.type === "POSTURE_CHANGED" && event.posture) {
      setSnapshot({
        posture: event.posture,
        reason: event.summary ?? "",
        since: event.timestamp,
        activeOverrides: [],
        activeDrifts: [],
      });
    }
  });

  if (!snapshot) return null;

  return (
    <div className={`posture-banner posture-${snapshot.posture.toLowerCase()}`}>
      <strong>{snapshot.posture}</strong> — {snapshot.reason}
    </div>
  );
}
