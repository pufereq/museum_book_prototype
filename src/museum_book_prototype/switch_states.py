# -*- coding: utf-8 -*-
"""Switch states module."""

from __future__ import annotations

import logging as lg


class SwitchStates:
    """Switch states class."""

    def __init__(self) -> None:
        """Initialize the switch states."""
        self.logger: lg.Logger = lg.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.debug("Initializing SwitchStates...")
        self.states: dict[str, bool] = {
            "page1_open": False,
            "page1_close": False,
            "page2_open": False,
            "page2_close": False,
            "page3_open": False,
            "page3_close": False,
            "page4_open": False,
            "page4_close": False,
            "page5_open": False,
            "page5_close": False,
        }

    def validate_states(self) -> bool:
        """Validate the current switch states.

        Returns:
            bool: True if states are valid, False otherwise.
        """
        # Example validation: ensure no page is both open and closed
        for i in range(1, 6):
            if self.states[f"page{i}_open"] and self.states[f"page{i}_close"]:
                self.logger.error(
                    f"Invalid state: page {i} cannot be both open and closed."
                )
                return False
        return True

    def update_states(self, new_states: dict[str, bool]) -> None:
        """Update the switch states and notify if there are changes.

        Args:
            new_states (dict[str, bool]): New switch states to update.
        """
        for key, new_value in new_states.items():
            old_value = self.states.get(key)
            if old_value is None:
                self.logger.warning(f"Unknown switch state key: {key}")
                continue
            if old_value != new_value:
                self.logger.info(
                    f"Switch state changed: {key} from {old_value} to {new_value}"
                )
                self.states[key] = new_value

        _ = self.validate_states()
