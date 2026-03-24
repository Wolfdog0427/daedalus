# runtime/watch_mode.py

from __future__ import annotations
import time
import json

from runtime.system_console import run_cycle


class WatchMode:
    """
    Real-time telemetry stream for observing the adaptive loop.
    """

    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self.running = False

    def start(self):
        """
        Begin streaming telemetry snapshots.
        """
        self.running = True
        print("🔍 Watch Mode started (Ctrl+C to stop)\n")

        try:
            while self.running:
                snapshot = run_cycle()

                # Pretty-print telemetry
                print(json.dumps(snapshot, indent=2))

                time.sleep(self.interval)

        except KeyboardInterrupt:
            print("\n🛑 Watch Mode stopped.")
            self.running = False


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
watch_mode = WatchMode()
