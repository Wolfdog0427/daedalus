# runtime/mobile_ui_renderer.py

from __future__ import annotations
from typing import Dict, Any, List

from runtime.mobile_ui_schema import mobile_ui_schema


class MobileUIRenderer:
    """
    Mobile UI Renderer 1.0

    Responsibilities:
      - Convert the Mobile UI Schema into a platform-agnostic render tree
      - Provide a clean, declarative structure for:
          - cards
          - panels
          - metrics
          - lists
          - actions
      - Serve as the rendering contract for React Native / Flutter / SwiftUI
      - Keep UI rendering logic separate from system logic
    """

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def render(self) -> Dict[str, Any]:
        """
        Produce a fully expanded render tree from the UI schema.
        """

        schema = mobile_ui_schema.get_schema()

        return {
            "version": schema["version"],
            "render_tree": [
                self._render_element(element)
                for element in schema["layout"]
            ],
        }

    # ------------------------------------------------------------
    # Element Rendering
    # ------------------------------------------------------------

    def _render_element(self, element: Dict[str, Any]) -> Dict[str, Any]:
        etype = element["type"]

        if etype == "card":
            return self._render_card(element)

        if etype == "panel":
            return self._render_panel(element)

        raise ValueError(f"Unknown UI element type: {etype}")

    # ------------------------------------------------------------
    # Card Rendering
    # ------------------------------------------------------------

    def _render_card(self, card: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "component": "Card",
            "title": card.get("title", "(untitled)"),
            "style": card.get("style", "default"),
            "content": self._render_card_content(card),
        }

    def _render_card_content(self, card: Dict[str, Any]) -> Dict[str, Any]:
        if "metrics" in card:
            return {
                "type": "metrics",
                "items": [
                    {"label": m["label"], "value": m["value"]}
                    for m in card["metrics"]
                ],
            }

        if "score" in card:
            return {
                "type": "score",
                "value": card["score"],
                "components": card.get("components", []),
            }

        if card.get("style") == "governor":
            return {
                "type": "governor_state",
                "tier": card.get("tier", "?"),
                "strict_mode": card.get("strict_mode", False),
            }

        return {"type": "empty"}

    # ------------------------------------------------------------
    # Panel Rendering
    # ------------------------------------------------------------

    def _render_panel(self, panel: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "component": "Panel",
            "title": panel.get("title", "(untitled)"),
            "items": self._render_panel_items(panel),
            "actions": self._render_panel_actions(panel),
        }

    def _render_panel_items(self, panel: Dict[str, Any]) -> List[Dict[str, Any]]:
        items = panel.get("items", [])
        return [
            self._render_panel_item(item)
            for item in items
        ]

    def _render_panel_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "component": "ListItem",
            "content": item,
        }

    def _render_panel_actions(self, panel: Dict[str, Any]) -> List[Dict[str, Any]]:
        actions = panel.get("actions", [])
        return [
            {
                "component": "ActionButton",
                "label": action["label"],
                "command": action["command"],
            }
            for action in actions
        ]


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
mobile_ui_renderer = MobileUIRenderer()
