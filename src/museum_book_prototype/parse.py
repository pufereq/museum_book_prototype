# -*- coding: utf-8 -*-
"""Parse data received from serial port."""

from __future__ import annotations

from typing import Callable

import logging as lg


class DataParser:
    """Data parser class."""

    def __init__(
        self, state_update_callback: Callable[[dict[str, bool]], None]
    ) -> None:
        """Initialize the DataParser.

        Args:
            state_update_callback (Callable[[dict[str, bool]], None]):
                Callback function to update switch states.
        """
        self.logger: lg.Logger = lg.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.debug("Initializing DataParser...")
        self.map: dict[int, str] = {
            0: "page1_open",
            1: "page1_close",
            2: "page2_open",
            3: "page2_close",
            4: "page3_open",
            5: "page3_close",
            6: "page4_open",
            7: "page4_close",
            8: "page5_open",
            9: "page5_close",
        }
        self.state_update_callback: Callable[[dict[str, bool]], None] = (
            state_update_callback
        )
        self.parsed: dict[str, bool] = {}

    def input_line(self, line: str):
        """Input a line of data for parsing.

        Args:
            line (str): The line of data to parse.
        """
        # self.logger.debug(f"Input line for parsing: {line}")
        self.parsed = self.parse_line(line)
        if self.parsed:
            self.state_update_callback(self.parsed)

    def parse_line(self, line: str):
        """Parse a line of CSV switch states.

        Args:
            line (str): The line of data to parse.
        Returns:
            dict[int, bool]: Parsed data as a dictionary.
        """
        parsed_data: dict[str, bool] = {}
        try:
            states = line.strip().split(",")
            if len(states) != len(self.map):
                self.logger.warning(
                    f"Unexpected number of states: {len(states)}. Expected: {len(self.map)}"
                )
            for index, state in enumerate(states):
                key = self.map.get(index, f"unknown_{index}")
                parsed_data[key] = bool(int(state))

        except ValueError as e:
            self.logger.error(f"Failed to parse line: {line}. Error: {e}")
        return parsed_data
