# runtime/mobile_state_synchronizer.py

from __future__ import annotations
from typing import Dict, Any, Optional, Callable
import threading
import requests
import time

from runtime.mobile_ui_renderer import mobile_ui_renderer
from runtime.mobile_ui_command_bindings import create_mobile_command_bindings


_DEFAULT_TIMEOUT = 10  # seconds


class MobileStateSynchronizer:
    """
    Mobile State Synchronizer 1.1

    Responsibilities:
      - Poll the backend for new system state (authenticated)
      - Feed polled state into the UI render pipeline
      - Merge local UI state with backend state
      - Dispatch commands and reconcile results
      - Run in a background thread so the caller is never blocked
    """

    def __init__(
        self,
        base_url: str,
        poll_interval: float = 2.0,
        auth_token: Optional[str] = None,
        verify_tls: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.poll_interval = poll_interval
        self._auth_token = auth_token
        self._verify_tls = verify_tls

        self.commands = create_mobile_command_bindings(
            base_url, auth_token=auth_token, verify_tls=verify_tls,
        )

        self.local_state: Dict[str, Any] = {}
        self.last_render_tree: Optional[Dict[str, Any]] = None
        self.on_update: Optional[Callable[[Dict[str, Any]], None]] = None
        self._state_lock = threading.Lock()

        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def start(self, on_update: Callable[[Dict[str, Any]], None]) -> None:
        """Start the synchronizer in a background daemon thread."""
        if self._running:
            return
        self.on_update = on_update
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, name="mobile-sync", daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the background loop to stop and wait for it to finish."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    @property
    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------
    # Core Loop (runs on background thread)
    # ------------------------------------------------------------

    def _loop(self) -> None:
        while self._running:
            try:
                backend_state = self._poll_backend()
                render_tree = self._generate_render_tree(backend_state)
                with self._state_lock:
                    merged = self._merge_local_state(render_tree)
                    self.last_render_tree = merged

                if self.on_update:
                    self.on_update(merged)

            except Exception as e:
                if self.on_update:
                    self.on_update({"error": "sync_error"})

            time.sleep(self.poll_interval)

    # ------------------------------------------------------------
    # Backend Polling (authenticated)
    # ------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {}
        if self._auth_token:
            h["X-Daedalus-Key"] = self._auth_token
        return h

    def _poll_backend(self) -> Dict[str, Any]:
        """Call /tick on the backend to get the latest system state."""
        url = f"{self.base_url}/tick"
        resp = requests.post(
            url,
            headers=self._headers(),
            verify=self._verify_tls,
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------
    # Render Tree Generation
    # ------------------------------------------------------------

    def _generate_render_tree(self, backend_state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the UI render tree, enriched with polled backend state."""
        tree = mobile_ui_renderer.render()
        tree["backend_state"] = backend_state
        return tree

    # ------------------------------------------------------------
    # Local State Merge
    # ------------------------------------------------------------

    def _merge_local_state(self, render_tree: Dict[str, Any]) -> Dict[str, Any]:
        """Merge local UI state (expanded panels, filters, scroll positions)
        with the backend render tree."""
        merged: Dict[str, Any] = {
            "version": render_tree.get("version", "1.0"),
            "backend_state": render_tree.get("backend_state"),
            "render_tree": [],
        }

        for element in render_tree.get("render_tree", []):
            eid = element.get("title") or element.get("component")
            local = self.local_state.get(eid, {})
            merged["render_tree"].append({**element, **local})

        return merged

    # ------------------------------------------------------------
    # Command Dispatch
    # ------------------------------------------------------------

    def dispatch_command(self, command: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = self.commands.dispatch(command, payload)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------
    # Local UI State Management
    # ------------------------------------------------------------

    def update_local_state(self, key: str, value: Any) -> None:
        with self._state_lock:
            self.local_state[key] = value

    def clear_local_state(self) -> None:
        with self._state_lock:
            self.local_state.clear()


# ------------------------------------------------------------
# Factory helper
# ------------------------------------------------------------

def create_mobile_state_synchronizer(
    base_url: str,
    auth_token: Optional[str] = None,
    verify_tls: bool = True,
) -> MobileStateSynchronizer:
    return MobileStateSynchronizer(
        base_url, auth_token=auth_token, verify_tls=verify_tls,
    )
