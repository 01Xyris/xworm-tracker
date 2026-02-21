import queue
from datetime import datetime, timezone

network_events = queue.Queue(maxsize=100)

def emit_network_event(event_type, country, ip=None):
    try:
        network_events.put_nowait({
            'type': event_type,
            'country': country,
            'ip': ip,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    except queue.Full:
        pass