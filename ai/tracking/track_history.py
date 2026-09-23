import time
from typing import Dict, List, Tuple, Optional
from collections import deque


class TrackHistory:
    """
    Maintains in-memory rolling spatial-temporal history of tracked individuals.
    Stores the last 10 seconds of (x, y, timestamp) coordinates per person ID.
    """

    def __init__(self, max_history_seconds: float = 10.0):
        self.max_history_seconds = max_history_seconds
        # Mapping: person_id -> deque of (x, y, timestamp)
        self._history: Dict[int, deque] = {}
        self._last_seen: Dict[int, float] = {}

    def add_point(self, person_id: int, x: float, y: float, timestamp: Optional[float] = None) -> None:
        """
        Records a new (x, y) centroid position for a person ID with a timestamp.
        Automatically purges observations older than max_history_seconds.
        """
        now = timestamp if timestamp is not None else time.time()
        self._last_seen[person_id] = now

        if person_id not in self._history:
            self._history[person_id] = deque()

        queue = self._history[person_id]
        queue.append((float(x), float(y), float(now)))

        # Evict coordinates older than 10 seconds
        cutoff = now - self.max_history_seconds
        while queue and queue[0][2] < cutoff:
            queue.popleft()

    def get_history(self, person_id: int) -> List[Tuple[float, float, float]]:
        """
        Returns all recorded positions for the person over the last 10 seconds.
        """
        return list(self._history.get(person_id, []))

    def get_recent_positions(
        self,
        person_id: int,
        window_seconds: float = 2.0
    ) -> List[Tuple[float, float, float]]:
        """
        Retrieves points within the most recent window (default last 2 seconds)
        for instant velocity and direction calculations.
        """
        history = self._history.get(person_id)
        if not history:
            return []

        latest_time = history[-1][2]
        cutoff = latest_time - window_seconds
        return [pt for pt in history if pt[2] >= cutoff]

    def prune_stale_tracks(self, max_idle_seconds: float = 15.0, current_time: Optional[float] = None) -> None:
        """
        Removes history for person IDs that have not been observed for over max_idle_seconds.
        """
        now = current_time if current_time is not None else time.time()
        stale_ids = [
            pid for pid, last in self._last_seen.items()
            if now - last > max_idle_seconds
        ]
        for pid in stale_ids:
            self._history.pop(pid, None)
            self._last_seen.pop(pid, None)

    def clear(self) -> None:
        """Resets all track histories."""
        self._history.clear()
        self._last_seen.clear()
