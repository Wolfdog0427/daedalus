# knowledge/plugins/base.py

"""
Plugin base and registry.
"""

from __future__ import annotations

from typing import Protocol, Dict, Any, Callable, List


class Plugin(Protocol):
    name: str

    def handles(self, command: str) -> bool:
        ...

    def run(self, command: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        ...


PLUGIN_REGISTRY: List[Plugin] = []


def register_plugin(plugin: Plugin):
    PLUGIN_REGISTRY.append(plugin)


def dispatch_to_plugins(command: str, context: Dict[str, Any] | None = None) -> Dict[str, Any] | None:
    for plugin in PLUGIN_REGISTRY:
        if plugin.handles(command):
            return plugin.run(command, context=context)
    return None
