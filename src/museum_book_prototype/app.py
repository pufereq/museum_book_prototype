# -*- coding: utf-8 -*-
"""Main application module for the museum book prototype."""

from __future__ import annotations

import logging as lg
import time
from pathlib import Path

import pygame as pg
import yaml

from museum_book_prototype.video_stream import VideoStream


VIDEO_SOURCES: dict[str, str] = {
    "front_cover": "assets/1.mov",
    "page1": "assets/2.mov",
    "page2": "assets/3.mov",
    "page3": "assets/4.mov",
    "page4": "assets/5.mov",
    "back_cover": "assets/6.mov",
}

PAGE_LABELS: dict[str | None, str | None] = {
    "front_cover": "page1",
    "page1": "page2",
    "page2": "page3",
    "page3": "page4",
    "page4": "page5",
    "back_cover": "page6",
    None: "None",
}


class App:
    """Main application class."""

    def __init__(self) -> None:
        """Initialize the application."""
        self.logger: lg.Logger = lg.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.debug("Initializing App...")
        self.videos: dict[str, VideoStream] = {}
        self.video_times: dict[str, float] = {}

        self.config = self.get_config()
        self.inputs: dict[str, bool] = {}

        cache_dir_setting = self.config.get("frame_cache_dir", "assets/frame_cache")
        self.cache_root: Path = Path(cache_dir_setting)
        try:
            self.cache_root.mkdir(parents=True, exist_ok=True)
        except Exception:  # noqa: BLE001
            self.logger.exception(
                "Failed to create cache directory at %s", self.cache_root
            )
            raise

        _ = pg.init()
        self.screen: pg.Surface = pg.display.set_mode((0, 0), pg.FULLSCREEN)
        pg.display.set_caption("Museum Book Prototype")

        self.error_surface: pg.Surface = pg.Surface((self.screen.get_width() - 40, 200))
        _ = self.error_surface.fill((255, 255, 255))
        self.error_surface.set_colorkey((255, 255, 255))
        self.error_surface.set_alpha(200)

        self._current_page: str | None = None

        self.clock: pg.time.Clock = pg.time.Clock()
        self.running: bool = True

        self.target_fps: int = self._config_int("target_fps", 24)
        self.max_video_fps: float = self._config_float("max_video_fps", 24.0)

        self.floating_start_time: float | None = None
        self.floating_pages: set[int] | None = None

        self.suspected_faulty: list[int] | None = None
        self.reported_faults: set[frozenset[int]] = set()

        self.critical_errors: dict[str, bool] = {
            "serial_fail": False,
            "serial_waiting": False,
            "video_load_failure": False,
        }

        self.prepare_videos()

    @property
    def current_page(self) -> str | None:
        """Get the current page.

        Returns:
            str | None: The current page identifier.
        """
        return self._current_page

    @current_page.setter
    def current_page(self, value: str | None) -> None:
        """Set the current page.

        Args:
            value (str | None): The new current page identifier.
        """
        if value == self._current_page:
            return

        previous = self._current_page
        if previous and previous in self.videos:
            self.videos[previous].close()

        new_page = value

        if value and value in self.videos:
            self.video_times[value] = 0.0
            try:
                self.videos[value].reset()
            except FileNotFoundError:
                self.logger.exception("Video file for %s could not be opened", value)
                self.critical_errors["video_load_failure"] = True
                self.videos[value].close()
                del self.videos[value]
                new_page = None
            except Exception:  # noqa: BLE001
                self.logger.exception("Failed to start video stream for %s", value)
                self.critical_errors["video_load_failure"] = True
                new_page = None
        elif value is None:
            new_page = None
        else:
            self.logger.warning("No video stream configured for page %s", value)

        previous_label = PAGE_LABELS.get(previous, previous)
        new_label = PAGE_LABELS.get(new_page, new_page)

        self.logger.info(
            "Current page changed from %s to %s", previous_label, new_label
        )

        self._current_page = new_page

    def get_config(self) -> dict:
        """Load configuration from YAML file.

        Returns:
            dict: Configuration dictionary.
        """
        self.logger.debug("Loading configuration...")
        try:
            with open("config.yaml", "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            self.logger.exception("Configuration file not found.")
            return {}

    def _config_int(self, key: str, default: int) -> int:
        """Return a positive integer configuration value."""

        raw_value = self.config.get(key, default)
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            self.logger.warning("Invalid %s in config; defaulting to %s", key, default)
            return default
        if value <= 0:
            self.logger.warning(
                "Non-positive %s in config; defaulting to %s", key, default
            )
            return default
        return value

    def _config_float(self, key: str, default: float) -> float:
        """Return a positive float configuration value."""

        raw_value = self.config.get(key, default)
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            self.logger.warning(
                "Invalid %s in config; defaulting to %.1f", key, default
            )
            return default
        if value <= 0:
            self.logger.warning(
                "Non-positive %s in config; defaulting to %.1f", key, default
            )
            return default
        return value

    def prepare_videos(self):
        """Prepare video clips."""
        self.logger.debug("Preparing video clips...")

        self.videos.clear()
        self.video_times.clear()

        target_size = self.screen.get_size()
        missing_any = False

        for key, path in VIDEO_SOURCES.items():
            video_path = Path(path)
            if not video_path.is_file():
                self.logger.error("Video file for %s not found at %s", key, video_path)
                missing_any = True
                continue

            self.videos[key] = VideoStream(
                path=str(video_path),
                fps_limit=self.max_video_fps,
                target_size=target_size,
                cache_root=self.cache_root,
                logger=self.logger.getChild(f"VideoStream[{key}]"),
            )
            self.video_times[key] = 0.0
            self.logger.debug("Prepared lazy stream for %s from %s", key, video_path)

        if missing_any:
            self.critical_errors["video_load_failure"] = True

    def _close_videos(self) -> None:
        """Release all video stream resources."""

        for stream in self.videos.values():
            stream.close()

    def _check_invalid_state(self, page_states: list[tuple[bool, bool]]) -> None:
        """Check for any page with both OPEN and CLOSED and report it.
        This marks the page as suspected_faulty, resets floating timers, sets current_page
        to None and logs an error the first time the fault is observed.

        Args:
            page_states (list[tuple[bool, bool]]): List of (OPEN, CLOSED) states for each page.
        """
        for i, (open_, close) in enumerate(page_states, start=1):
            if open_ and close:
                self.logger.warning(f"Invalid state for page {i}: both OPEN and CLOSED")
                self.floating_start_time = None
                self.floating_pages = None
                self.suspected_faulty = [i]
                self.current_page = None
                fault_key = frozenset({i})
                if fault_key not in self.reported_faults:
                    self.reported_faults.add(fault_key)
                    msg = f"Contactor fault detected on page {i}: both OPEN and CLOSED"
                    self.logger.error(msg)
                else:
                    self.logger.debug(
                        f"Fault for page {i} already reported; not logging again."
                    )
                return
            else:
                fault_key = frozenset({i})
                if fault_key in self.reported_faults:
                    self.reported_faults.discard(fault_key)
                    self.logger.debug(
                        f"Contactor fault on page {i} cleared; removing from reported faults."
                    )

    def handle_input(self, inputs: dict[str, bool]) -> None:
        """Public method to handle input updates.

        Args:
            inputs (dict[str, bool]): Dictionary of switch states.
        """
        self.inputs = inputs

    def _handle_input(self, inputs: dict[str, bool]) -> None:
        """Update current_page based on the 5 pairs of OPEN/CLOSED switches.
        If any page is floating for more than 30 seconds the condition is logged once
        for that specific set of pages; no exceptions are raised.

        Args:
            inputs (dict[str, bool]): Dictionary of switch states.
        """
        page_states: list[tuple[bool, bool]] = [
            (
                bool(inputs.get(f"page{i}_open", False)),
                bool(inputs.get(f"page{i}_close", False)),
            )
            for i in range(1, 6)
        ]

        self._check_invalid_state(page_states)

        # if any page is floating (neither open nor close) - start/continue floating timer.
        floating_now = {
            i
            for i, (open_, close) in enumerate(page_states, start=1)
            if (not open_ and not close)
        }
        if floating_now:
            now = time.time()
            # if set of floating pages changed, restart timer with new set
            if self.floating_start_time is None or self.floating_pages != floating_now:
                self.floating_start_time = now
                self.floating_pages = set(floating_now)
                self.logger.debug(
                    f"Floating state started for pages {sorted(self.floating_pages)} at {self.floating_start_time}"
                )
            else:
                elapsed = now - self.floating_start_time
                self.logger.debug(
                    f"Floating state for pages {sorted(self.floating_pages)} elapsed: {elapsed:.1f}s"
                )
                if elapsed > 30.0:
                    fault_key = frozenset(self.floating_pages)
                    if fault_key not in self.reported_faults:
                        # mark suspected faulty contactors
                        self.suspected_faulty = sorted(self.floating_pages)
                        msg = f"Floating state for pages {self.suspected_faulty} persisted longer than 30 seconds"
                        self.reported_faults.add(fault_key)
                        self.logger.error(msg)
                    else:
                        self.logger.debug(
                            f"Floating fault for pages {sorted(self.floating_pages)} already reported; not logging again."
                        )
            # unset current page while floating
            self.current_page = None
            return
        else:
            if self.floating_pages:
                previously_floating_key = frozenset(self.floating_pages)

                if previously_floating_key in self.reported_faults:
                    self.reported_faults.discard(previously_floating_key)

            self.floating_start_time = None
            self.floating_pages = None
            self.suspected_faulty = None

        all_open = all(open_ and not close for open_, close in page_states)
        all_closed = all(close and not open_ for open_, close in page_states)

        if all_closed:
            self.current_page = "front_cover"
            self.logger.debug("All pages closed -> page1")
            return

        if all_open:
            self.current_page = "back_cover"
            self.logger.debug("All pages open -> page6")
            return

        # If page5 is OPEN and not CLOSED, show page6
        p5_open, p5_close = page_states[4]
        if p5_open and not p5_close:
            self.current_page = "back_cover"
            return

        open_pages = [
            i + 1 for i, (open_, close) in enumerate(page_states) if open_ and not close
        ]
        if open_pages:
            chosen = max(open_pages)
            self.current_page = f"page{chosen}"
            return

        self.logger.debug(
            "Unable to determine page from inputs; setting current_page = None"
        )
        self.current_page = None

    def run(self) -> None:
        """Run the main application loop."""
        self.logger.debug("Starting main application loop...")
        for key in self.videos:
            self.videos[key].ensure_cache()

        while self.running:
            dt = self.clock.tick(self.target_fps) / 1000.0

            self._handle_input(self.inputs)

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.running = False

            _ = self.screen.fill(self.config.get("background_color", (255, 255, 255)))

            current_page = self.current_page
            stream = self.videos.get(current_page) if current_page else None
            if stream:
                frame_surface = stream.advance(dt)
                if frame_surface is not None:
                    _ = self.screen.blit(frame_surface, (0, 0))
                    if current_page in self.video_times:
                        self.video_times[current_page] = stream.elapsed_time

            error_text: str = ""

            if self.critical_errors["serial_fail"]:
                error_text += "Cannot connect to serial port.\n"

            if self.critical_errors["serial_waiting"]:
                error_text += "Waiting for serial device...\n"
                # TODO: determine if should show blank screen here

            if self.critical_errors["video_load_failure"]:
                error_text += "Failed to load video clips.\n"

            # if self.reported_faults:
            #     error_text += f"{', '.join(str(i) for fault in self.reported_faults for i in sorted(fault))}\n"

            if self.suspected_faulty:
                error_text = "!"

            # check if any errors occured
            _ = self.error_surface.fill((255, 255, 255))
            if error_text:
                font = pg.font.SysFont(None, 20)
                lines = error_text.strip().split("\n")
                for i, line in enumerate(lines):
                    text_surf = font.render(line, False, (255, 0, 0))
                    _ = self.error_surface.blit(text_surf, (0, 0 + i * 24))

            _ = self.screen.blit(self.error_surface, (20, 20))

            pg.display.flip()

        self.logger.debug("Exiting...")
        self._close_videos()
        pg.quit()
