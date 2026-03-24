# runtime/mobile_state_synchronizer.py

from __future__ import annotations
from typing import Dict, Any, Optional, Callable
import requests
import time

from runtime.mobile_ui_renderer import mobile_ui_renderer
from runtime.mobile_ui_command_bindings import create_mobile_command_bindings


class MobileStateSynchronizer:
    """
    Mobile State Synchronizer 1.0

    Responsibilities:
      - Poll the backend for new system state
      - Update the UI render tree
      - Merge local UI state with backend state
      - Handle optimistic UI updates
      - Dispatch commands and reconcile results
      - Provide a clean state stream for the mobile app
    """

    def __init__(self, base_url: str, poll_interval: float = 2.0):
        self.base_url = base_url.rstrip("/")
        self.poll_interval = poll_interval

        # Command binding layer
        self.commands = create_mobile_command_bindings(base_url)

        # Local UI state (filters, expanded panels, etc.)
        self.local_state: Dict[str, Any] = {}

        # Last full render tree
        self.last_render_tree: Optional[Dict[str, Any]] = None

        # Callback for UI updates
        self.on_update: Optional[Callable[[Dict[str, Any]], None]] = None

        # Control flag
        self.running = False

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def start(self, on_update: Callable[[Dict[str, Any]], None]):
        """
        Start the synchronizer loop.
        """
        self.on_update = on_update
        self.running = True
        self._loop()

    def stop(self):
        """
        Stop the synchronizer loop.
        """
        self.running = False

    # ------------------------------------------------------------
    # Core Loop
    # ------------------------------------------------------------

    def _loop(self):
        """
        Poll → Merge → Render → Notify
        """
        while self.running:
            try:
                backend_state = self._poll_backend()
                render_tree = self._generate_render_tree(backend_state)
                merged = self._merge_local_state(render_tree)

                self.last_render_tree = merged

                if self.on_update:
                    self.on_update(merged)

            except Exception as e:
                if self.on_update:
                    self.on_update({"error": str(e)})

            time.sleep(self.poll_interval)

    # ------------------------------------------------------------
    # Backend Polling
    # ------------------------------------------------------------

    def _poll_backend(self) -> Dict[str, Any]:
        """
        Calls /tick on the backend to get the latest system state.
        """
        url = f"{self.base_url}/tick"
        return requests.post(url).json()

    # ------------------------------------------------------------
    # Render Tree Generation
    # ------------------------------------------------------------

    def _generate_render_tree(self, backend_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate the UI render tree from the schema + backend state.
        """
        return mobile_ui_renderer.render()

    # ------------------------------------------------------------
    # Local State Merge
    # ------------------------------------------------------------

    def _merge_local_state(self, render_tree: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge local UI state (expanded panels, filters, scroll positions)
        with the backend render tree.
        """
        merged = {
            "version": render_tree["version"],
            "render_tree": [],
        }

        for element in render_tree["render_tree"]:
            eid = element.get("title") or element.get("component")

            local = self.local_state.get(eid, {})
            merged_element = {**element, **local}

            merged["render_tree"].append(merged_element)

        return merged

    # ------------------------------------------------------------
    # Command Dispatch
    # ------------------------------------------------------------

    def dispatch_command(self, command: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatch a UI command and return the backend response.
        """
        try:
            result = self.commands.dispatch(command, payload)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------
    # Local UI State Management
    # ------------------------------------------------------------

    def update_local_state(self, key: str, value: Any):
        """
        Update local UI state (e.g., expanded panels).
        """
        self.local_state[key] = value

    def clear_local_state(self):
        self.local_state.clear()


# ------------------------------------------------------------
# Factory helper
# ------------------------------------------------------------

def create_mobile_state_synchronizer(base_url: str) -> MobileStateSynchronizer:
    return MobileStateSynchronizer(base_url)
