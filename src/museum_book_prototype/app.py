# -*- coding: utf-8 -*-
"""Main application module for the museum book prototype."""

from __future__ import annotations

import logging as lg
import pygame as pg

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

        self.current_page: str | None = "page1"

        self.clock: pg.time.Clock = pg.time.Clock()
        self.running: bool = True

        self.prepare_videos()

    def prepare_videos(self):
        """Prepare video clips."""
        self.logger.debug("Preparing video clips...")
        self.video_clips = {
            "front_cover": VideoFileClip("assets/1.mov"),
            "page1": VideoFileClip("assets/2.mov"),
            "page2": VideoFileClip("assets/3.mov"),
            "page3": VideoFileClip("assets/4.mov"),
            "page4": VideoFileClip("assets/5.mov"),
            "back_cover": VideoFileClip("assets/6.mov"),
        }
        self.video_times = {key: 0.0 for key in self.video_clips}

    def handle_input(self, inputs: dict[str, bool], error: str) -> None:
        """Switch the current page based on inputs.

        Args:
            inputs (dict[str, bool]): Dictionary of switch states.
        """
        self.logger.debug(f"Handling input: {inputs}, error: {error}")

    def run(self) -> None:
        self.logger.debug("Starting main application loop...")

        while self.running:
            dt = self.clock.get_time() / 1000.0

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.running = False

                # if event.type == pg.KEYDOWN:
                #     if event.key == pg.K_RIGHT:
                #         self.switch_page(1)
                #     if event.key == pg.K_LEFT:
                #         self.switch_page(-1)

            self.screen.fill((255, 255, 255))

            current_video = self.video_clips.get(self.current_page)
            if current_video:
                # advance video time
                self.video_times[self.current_page] += dt
                t = self.video_times[self.current_page] % current_video.duration

                frame = current_video.get_frame(t)
                frame_surface = pg.surfarray.make_surface(frame.swapaxes(0, 1))
                self.screen.blit(frame_surface, (0, 0))

            pg.display.flip()
            self.clock.tick(24)

        self.logger.debug("Exiting...")
        pg.quit()
