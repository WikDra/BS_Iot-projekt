
import threading
from collections import deque


class MeasurementStore:
    def __init__(self, maxlen=1000):
        self._items = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._next_id = 1

    def add(self, measurement):
        with self._lock:
            record = {"id": self._next_id, **measurement}
            self._next_id += 1
            self._items.append(record)
            return record

    def get_all(self):
        with self._lock:
            return [record.copy() for record in self._items]

    def __len__(self):
        with self._lock:
            return len(self._items)
