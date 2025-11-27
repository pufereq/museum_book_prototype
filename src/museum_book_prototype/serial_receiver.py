# -*- coding: utf-8 -*-
"""Serial receiver."""

from __future__ import annotations

import logging as lg
from typing import Callable
import serial
import serial.tools.list_ports
import time


class SerialReceiver:
    """Serial receiver class."""

    def __init__(
        self,
        parse_callback: Callable[[str], None],
        baudrate: int = 9600,
        timeout: float = 1.0,
    ) -> None:
        """Initialize the SerialReceiver.

        Args:
            parse_callback (Callable[[str], None]): Callback function to parse received lines.
            baudrate (int): Baud rate for serial communication.
            timeout (float): Timeout for serial communication.
        """
        self.logger: lg.Logger = lg.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.debug("Initializing SerialReceiver...")

        self.parse_callback: Callable[[str], None] = parse_callback
        self.baudrate: int = baudrate
        self.timeout: float = timeout
        self.serial_port: serial.Serial | None = None

    def list_usb_ports(self) -> list[str]:
        """List available USB serial ports.

        Returns:
            list[str]: List of USB serial port device names.
        """
        ports = serial.tools.list_ports.comports()
        usb_ports = [port.device for port in ports if "USB" in port.description]
        return usb_ports

    def try_connect(self, port: str) -> None:
        """Try to connect to the specified serial port.

        Args:
            port (str): The serial port to connect to.
        """
        self.logger.debug(f"Connecting to port: {port}")
        self.serial_port = serial.Serial(port, self.baudrate, timeout=self.timeout)

    def connect(self) -> None:
        """Connect to the serial port."""
        self.logger.info("Attempting to connect to serial port...")
        while True:
            available_ports = self.list_usb_ports()
            if available_ports:
                break
            time.sleep(1)

        while not self.is_connected():
            try:
                self.try_connect(available_ports[0])
            except serial.SerialException as e:
                self.logger.warning(
                    f"Failed to connect to port: {available_ports[0]}. Retrying... Error: {e}"
                )
                time.sleep(1)
        else:
            self.logger.info(f"Connected to serial port: {self.serial_port.port}")

    def disconnect(self) -> None:
        """Disconnect from the serial port."""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.serial_port = None

    def read_line(self) -> str | None:
        """Read a line from the serial port.

        Returns:
            str | None: The read line as a string, or None if not connected.
        """
        if self.serial_port and self.serial_port.is_open:
            try:
                line_raw = self.serial_port.readline()
            except serial.SerialException:
                self.disconnect()
                return None

            try:
                line = line_raw.decode("utf-8").strip()
            except UnicodeDecodeError as e:
                self.logger.error(
                    f"Invalid data received. Skipping line: {line_raw}. Error: {e}"
                )
                return None

            return line
        return None

    def is_connected(self) -> bool:
        """Check if the serial port is connected."""
        return self.serial_port is not None and self.serial_port.is_open

    def run(self) -> None:
        """Run the serial receiver."""
        self.logger.info("Starting SerialReceiver...")
        self.connect()
        while True:
            if self.is_connected():
                line = self.read_line()
                # TODO: parse line

                if line:
                    self.parse_callback(line)

                # if line:
                #     self.logger.info(f"Received line: {line}")
            else:
                self.logger.warning("Serial port disconnected. Reconnecting...")
                self.connect()
