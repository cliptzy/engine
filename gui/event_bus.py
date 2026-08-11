import threading
from collections import defaultdict
from typing import Any, Callable, Dict, List


class EventBus:
    """Thread-safe publish/subscribe event system. Replaces pyqtSignal."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[..., Any]]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event: str, callback: Callable[..., Any]) -> None:
        """Subscribe a callback to an event."""
        with self._lock:
            if callback not in self._subscribers[event]:
                self._subscribers[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable[..., Any]) -> None:
        """Unsubscribe a callback from an event."""
        with self._lock:
            if callback in self._subscribers[event]:
                self._subscribers[event].remove(callback)

    def publish(self, event: str, **kwargs: Any) -> None:
        """Publish an event with keyword arguments."""
        with self._lock:
            listeners = list(self._subscribers.get(event, []))

        for callback in listeners:
            try:
                callback(**kwargs)
            except Exception as e:
                import traceback

                print(
                    f"Error in event listener for '{event}': {e}\\n{traceback.format_exc()}"
                )


# Global singleton event bus
event_bus = EventBus()
