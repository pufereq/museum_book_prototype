# -*- coding: utf-8 -*-
"""Main application module for the museum book prototype."""

from __future__ import annotations

import logging as lg
import pygame as pg
import time

from moviepy import VideoFileClip


class App:
    """Main application class."""

    def __init__(self) -> None:
        """Initialize the application."""
        self.logger: lg.Logger = lg.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.debug("Initializing App...")
        self.video_clips: dict[str, VideoFileClip] = {}
        self.video_times: dict[str, float] = {}

        _ = pg.init()
        self.screen: pg.Surface = pg.display.set_mode((1920, 1080))
        pg.display.set_caption("Museum Book Prototype")

        self.error_surface: pg.Surface = pg.Surface((self.screen.get_width() - 40, 200))
        _ = self.error_surface.fill((255, 255, 255))
        self.error_surface.set_colorkey((255, 255, 255))
        self.error_surface.set_alpha(200)

        self._current_page: str | None = None

        self.clock: pg.time.Clock = pg.time.Clock()
        self.running: bool = True

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
        if value != self._current_page:
            self.logger.info(
                f"Current page changed from {self._current_page} to {value}"
            )
            self._current_page = value
            if value in self.video_times:
                self.video_times[value] = 0.0

    def prepare_videos(self):
        """Prepare video clips."""
        self.logger.debug("Preparing video clips...")
        try:
            self.video_clips = {
                "front_cover": VideoFileClip("assets/1.mov"),
                "page1": VideoFileClip("assets/2.mov"),
                "page2": VideoFileClip("assets/3.mov"),
                "page3": VideoFileClip("assets/4.mov"),
                "page4": VideoFileClip("assets/5.mov"),
                "back_cover": VideoFileClip("assets/6.mov"),
            }
        except FileNotFoundError:
            self.logger.exception("Failed to load video clips.")
            self.critical_errors["video_load_failure"] = True
            self.video_clips = {}
        self.video_times = {key: 0.0 for key in self.video_clips}

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

    def handle_input(self, inputs: dict[str, bool]) -> None:
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

        # If any page is floating (neither open nor close) - start/continue floating timer.
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
            self.logger.debug("All pages closed -> front_cover")
            return

        if all_open:
            self.current_page = "back_cover"
            self.logger.debug("All pages open -> back_cover")
            return

        # If page5 is OPEN and not CLOSED, show back_cover
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

        while self.running:
            dt = self.clock.get_time() / 1000.0

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.running = False

            _ = self.screen.fill((255, 255, 255))

            current_video = self.video_clips.get(self.current_page)
            if current_video:
                # advance video time
                self.video_times[self.current_page] += dt
                t = min(
                    self.video_times[self.current_page], current_video.duration - 0.001
                )

                frame = current_video.get_frame(t)
                frame_surface = pg.surfarray.make_surface(frame.swapaxes(0, 1))
                _ = self.screen.blit(
                    pg.transform.smoothscale(frame_surface, self.screen.get_size()),
                    (0, 0),
                )

            error_text: str = ""

            if self.critical_errors["serial_fail"]:
                error_text += "Cannot connect to serial port.\n"

            if self.critical_errors["serial_waiting"]:
                error_text += "Waiting for serial device...\n"
                # TODO: determine if should show blank screen here

            if self.critical_errors["video_load_failure"]:
                error_text += "Failed to load video clips.\n"

            if self.reported_faults:
                error_text += f"{', '.join(str(i) for fault in self.reported_faults for i in sorted(fault))}\n"

            if self.suspected_faulty:
                error_text = "!"

            # check if any errors occured
            _ = self.error_surface.fill((255, 255, 255))
            if error_text:
                font = pg.font.SysFont(None, 20)
                lines = error_text.strip().split("\n")
                for i, line in enumerate(lines):
                    text_surf = font.render(line, False, (255, 0, 0))
                    self.error_surface.blit(text_surf, (0, 0 + i * 24))

            _ = self.screen.blit(self.error_surface, (20, 20))

            pg.display.flip()
            _ = self.clock.tick(24)

        self.logger.debug("Exiting...")
        pg.quit()
