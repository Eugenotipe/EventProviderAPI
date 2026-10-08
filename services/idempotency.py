import hashlib
import json

from schemas import TicketCreate


def hash_request(data: TicketCreate) -> str:
    payload = {
        "event_id": str(data.event_id),
        "first_name": data.first_name.strip(),
        "last_name": data.last_name.strip(),
        "email": str(data.email).lower().strip(),
        "seat": data.seat.strip(),
    }
    normalized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
