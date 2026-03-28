# knowledge/plugins/base.py

"""
Plugin base and registry.
"""

from __future__ import annotations

import threading
from typing import Protocol, Dict, Any, Callable, List


class Plugin(Protocol):
    name: str

    def handles(self, command: str) -> bool:
        ...

    def run(self, command: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        ...


PLUGIN_REGISTRY: List[Plugin] = []
_registry_lock = threading.Lock()


def register_plugin(plugin: Plugin):
    with _registry_lock:
        PLUGIN_REGISTRY.append(plugin)


def dispatch_to_plugins(command: str, context: Dict[str, Any] | None = None) -> Dict[str, Any] | None:
    with _registry_lock:
        registry_snapshot = list(PLUGIN_REGISTRY)
    for plugin in registry_snapshot:
        if plugin.handles(command):
            return plugin.run(command, context=context)
    return None
