# -*- coding: utf-8 -*-
"""Video stream handling with on-disk frame caching."""

import json
import logging as lg
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import pygame as pg

from moviepy import VideoFileClip


@dataclass(slots=True)
class VideoStream:
    """Stream video frames from an on-disk cache of predecoded surfaces."""

    path: str
    fps_limit: float
    target_size: tuple[int, int]
    cache_root: Path
    logger: lg.Logger

    frame_paths: list[Path] = field(default_factory=list, init=False)
    fps: float = 0.0
    frame_duration: float = 0.0
    accumulator: float = 0.0
    elapsed_time: float = 0.0
    frame_index: int = 0
    finished: bool = True
    last_surface: pg.Surface | None = None
    duration_seconds: float = 0.0

    def reset(self) -> None:
        """Restart playback from the first frame, building cache on demand."""

        self.ensure_cache()
        if not self.frame_paths:
            raise RuntimeError(f"No cached frames available for {self.path}")

        self.accumulator = 0.0
        self.elapsed_time = 0.0
        self.frame_index = 0
        self.finished = False
        self.last_surface = None
        self._load_frame(self.frame_index)

    def ensure_cache(self) -> None:
        """Make sure a decoded frame cache exists and is in sync with the source."""

        metadata = self._read_metadata()
        self._refresh_frame_paths()

        if not self._cache_is_valid(metadata):
            self.logger.info("Building frame cache for %s", self.path)
            self._rebuild_cache()
            metadata = self._read_metadata()
            self._refresh_frame_paths()

        if not metadata or not self.frame_paths:
            raise RuntimeError(f"Cache build failed for {self.path}")

        self._apply_metadata(metadata)

    def advance(self, dt: float) -> pg.Surface | None:
        """Return the surface for the current playback time after advancing."""

        if not self.frame_paths:
            return self.last_surface

        if self.finished:
            return self.last_surface

        self.accumulator += dt

        while self.accumulator >= self.frame_duration and not self.finished:
            self.accumulator -= self.frame_duration
            next_index = self.frame_index + 1
            if next_index >= len(self.frame_paths):
                self.finished = True
                self.frame_index = len(self.frame_paths) - 1
                self.accumulator = 0.0
            else:
                self.frame_index = next_index
                self._load_frame(self.frame_index)

        if self.finished and self.last_surface is None:
            self._load_frame(self.frame_index)

        if self.finished:
            self.elapsed_time = self.duration
        else:
            self.elapsed_time = self.frame_index * self.frame_duration + min(
                self.accumulator, self.frame_duration
            )

        return self.last_surface

    def close(self) -> None:
        """Release references to loaded surfaces."""

        self.accumulator = 0.0
        self.elapsed_time = 0.0
        self.frame_index = 0
        self.finished = True
        self.last_surface = None

    @property
    def cache_dir(self) -> Path:
        """Return the directory containing cached frames."""

        safe_name = Path(self.path).stem
        return self.cache_root / safe_name

    @property
    def metadata_path(self) -> Path:
        """Return the metadata file path for the cache."""

        return self.cache_dir / "metadata.json"

    @property
    def duration(self) -> float:
        """Total duration of the clip represented by this stream."""

        if self.duration_seconds > 0:
            return self.duration_seconds
        return len(self.frame_paths) * self.frame_duration if self.frame_paths else 0.0

    def _load_frame(self, index: int) -> None:
        """Load a frame surface from disk into memory."""

        if not self.frame_paths:
            return

        clamped = max(0, min(index, len(self.frame_paths) - 1))
        frame_path = self.frame_paths[clamped]
        while True:
            try:
                surface = pg.image.load(str(frame_path))
            except Exception:  # noqa: BLE001
                self.logger.exception("Failed to load cached frame %s", frame_path)
                # try to recache
                self.ensure_cache()
            else:
                break

        if surface.get_size() != self.target_size:
            surface = pg.transform.smoothscale(surface, self.target_size)
        self.last_surface = surface.convert()
        self.frame_index = clamped

    def _rebuild_cache(self) -> None:
        """Decode the source video and persist frames to disk."""

        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        frame_paths: list[Path] = []
        with VideoFileClip(self.path, audio=False) as clip:
            source_fps = clip.fps or 24.0
            playback_fps = (
                min(source_fps, self.fps_limit) if self.fps_limit > 0 else source_fps
            )
            if playback_fps <= 0:
                playback_fps = 24.0

            for index, frame in enumerate(
                clip.iter_frames(fps=playback_fps, dtype="uint8")
            ):
                surface = pg.surfarray.make_surface(frame.swapaxes(0, 1))
                if surface.get_size() != self.target_size:
                    surface = pg.transform.smoothscale(surface, self.target_size)
                surface = surface.convert()
                frame_path = self.cache_dir / f"frame_{index:05d}.bmp"
                pg.image.save(surface, frame_path)
                frame_paths.append(frame_path)

            duration = float(clip.duration or len(frame_paths) / playback_fps)

        if not frame_paths:
            raise RuntimeError(f"No frames decoded from {self.path}")

        metadata = {
            "fps": playback_fps,
            "frame_count": len(frame_paths),
            "duration": duration,
            "width": self.target_size[0],
            "height": self.target_size[1],
            "fps_limit": self.fps_limit,
            "source_mtime": Path(self.path).stat().st_mtime,
        }

        self._write_metadata(metadata)

    def _refresh_frame_paths(self) -> None:
        """Populate the in-memory list of cached frame paths."""

        if self.cache_dir.is_dir():
            self.frame_paths = sorted(self.cache_dir.glob("frame_*.bmp"))
        else:
            self.frame_paths = []

    def _apply_metadata(self, metadata: dict[str, object]) -> None:
        """Update playback parameters from cached metadata."""

        fps = float(metadata.get("fps", 24.0))
        if fps <= 0:
            fps = 24.0
        self.fps = fps
        self.frame_duration = 1.0 / fps
        self.duration_seconds = float(
            metadata.get("duration", len(self.frame_paths) * self.frame_duration)
        )

    def _cache_is_valid(self, metadata: dict[str, object] | None) -> bool:
        """Return True if the cached frames match the source video."""

        if not metadata:
            return False

        if not self.frame_paths:
            return False

        source_mtime = Path(self.path).stat().st_mtime

        return (
            metadata.get("source_mtime") == source_mtime
            and metadata.get("width") == self.target_size[0]
            and metadata.get("height") == self.target_size[1]
            and metadata.get("fps_limit") == self.fps_limit
            and metadata.get("frame_count") == len(self.frame_paths)
        )

    def _read_metadata(self) -> dict[str, object] | None:
        """Read cache metadata from disk if it exists."""

        metadata_path = self.metadata_path
        if not metadata_path.is_file():
            return None

        try:
            with metadata_path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:  # noqa: BLE001
            self.logger.warning("Failed to read cache metadata for %s", self.path)
            return None

    def _write_metadata(self, metadata: dict[str, object]) -> None:
        """Persist cache metadata alongside the cached frames."""

        with self.metadata_path.open("w", encoding="utf-8") as handle:
            json.dump(metadata, handle)
