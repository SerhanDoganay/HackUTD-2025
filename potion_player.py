# play_server.py
# Live playback over a LONG-format DataFrame: [timestamp, cauldron_id, volume]
import threading
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api_loader import fetch_cauldron_levels  # <-- uses your loader

# ----------------------------
# Core player (data-agnostic)
# ----------------------------
class LiveDFPlayer:
    """
    Minute-by-minute playback for a LONG-format DataFrame:
      required columns: ['timestamp', 'cauldron_id', 'volume']
      one 'frame' = dict of {cauldron_id: volume} for a single timestamp.
    """

    def __init__(self, df_long: pd.DataFrame, seconds_per_minute: float = 60.0):
        df = df_long.copy()
        # normalize + sort
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.sort_values(["timestamp", "cauldron_id"])

        # timeline (unique minutes)
        self.timeline: np.ndarray = df["timestamp"].drop_duplicates().to_numpy()

        # precompute frames for fast serving
        frames: List[Tuple[pd.Timestamp, Dict[str, float]]] = []
        for ts, grp in df.groupby("timestamp", sort=True):
            frames.append((ts, dict(zip(grp["cauldron_id"], grp["volume"]))))

        self.frames = frames
        self.n = len(frames)

        # playback state
        self.idx = 0
        self.direction = +1               # +1 forward, -1 reverse
        self.playing = False
        self.seconds_per_minute = float(seconds_per_minute)

        # thread safety
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop_evt = threading.Event()

    # ---------- helpers ----------
    def _clamp(self, i: int) -> int:
        return 0 if self.n == 0 else max(0, min(self.n - 1, i))

    def _sleep_tick(self):
        spm = max(0.0, self.seconds_per_minute)
        if spm > 0:
            time.sleep(spm)

    # ---------- public API ----------
    def current(self) -> Dict:
        with self._lock:
            if self.n == 0:
                return {"timestamp": None, "levels": {}, "index": 0}
            ts, levels = self.frames[self.idx]
            return {"timestamp": ts.isoformat(), "levels": levels, "index": self.idx}

    def state(self) -> Dict:
        with self._lock:
            return {
                "playing": self.playing,
                "index": self.idx,
                "total_frames": self.n,
                "direction": self.direction,
                "seconds_per_minute": self.seconds_per_minute,
                "timestamp": (self.frames[self.idx][0].isoformat() if self.n else None),
            }

    def set_speed(self, seconds_per_minute: float):
        with self._lock:
            self.seconds_per_minute = float(seconds_per_minute)

    def set_direction(self, direction: int):
        with self._lock:
            self.direction = +1 if direction >= 0 else -1

    def seek_index(self, i: int):
        with self._lock:
            self.idx = self._clamp(i)

    def seek_time(self, ts_iso: str):
        target = pd.to_datetime(ts_iso, utc=True)
        arr = self.timeline
        pos = int(np.searchsorted(arr, target))
        # pick nearest between pos and pos-1
        if pos == len(arr) or (pos > 0 and abs(arr[pos - 1] - target) < abs(arr[pos] - target)):
            pos -= 1
        self.seek_index(pos)

    def step(self, steps: int = 1, direction: Optional[int] = None):
        with self._lock:
            d = self.direction if direction is None else (+1 if direction >= 0 else -1)
            self.idx = self._clamp(self.idx + d * max(1, steps))

    def play(self, direction: Optional[int] = None):
        with self._lock:
            if direction is not None:
                self.direction = +1 if direction >= 0 else -1
            if not self.playing:
                self.playing = True
                if self._thread is None or not self._thread.is_alive():
                    self._stop_evt.clear()
                    self._thread = threading.Thread(target=self._loop, daemon=True)
                    self._thread.start()

    def pause(self):
        with self._lock:
            self.playing = False

    def stop(self):
        self._stop_evt.set()
        self.pause()

    # ---------- internal loop ----------
    def _loop(self):
        while not self._stop_evt.is_set():
            with self._lock:
                if not self.playing or self.n == 0:
                    pass
                else:
                    nxt = self.idx + self.direction
                    if nxt < 0 or nxt >= self.n:
                        self.playing = False  # pause at edges (or change to loop)
                    else:
                        self.idx = nxt
            self._sleep_tick()

# ----------------------------
# FastAPI layer (for React)
# ----------------------------
app = FastAPI(title="Potion Live Feed")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PLAYER: Optional[LiveDFPlayer] = None

class SpeedBody(BaseModel):
    seconds_per_minute: float

@app.on_event("startup")
def _startup():
    global PLAYER
    df_long = fetch_cauldron_levels()          # <-- uses YOUR loader (long-format)
    PLAYER = LiveDFPlayer(df_long, seconds_per_minute=60.0)  # real-time default
    print("Live player ready.")

@app.get("/live/frame")
def get_frame():
    return PLAYER.current() if PLAYER else {"error": "player not initialized"}

@app.get("/live/state")
def get_state():
    return PLAYER.state() if PLAYER else {"error": "player not initialized"}

@app.post("/live/play")
def do_play(direction: int = Query(default=+1)):
    PLAYER.play(direction=direction)
    return PLAYER.state()

@app.post("/live/pause")
def do_pause():
    PLAYER.pause()
    return PLAYER.state()

@app.post("/live/step")
def do_step(steps: int = Query(default=1), direction: int = Query(default=None)):
    PLAYER.step(steps=steps, direction=direction)
    return PLAYER.current()

@app.post("/live/seek/index")
def do_seek_index(index: int = Query(...)):
    PLAYER.seek_index(index)
    return PLAYER.current()

@app.post("/live/seek/time")
def do_seek_time(ts: str = Query(..., description="ISO timestamp (e.g., 2025-11-01T00:03:00Z)")):
    PLAYER.seek_time(ts)
    return PLAYER.current()

@app.post("/live/direction")
def set_direction(direction: int = Query(...)):
    PLAYER.set_direction(direction)
    return PLAYER.state()

@app.post("/live/speed")
def set_speed(body: SpeedBody):
    PLAYER.set_speed(body.seconds_per_minute)
    return PLAYER.state()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("play_server:app", host="127.0.0.1", port=8000, reload=False)
