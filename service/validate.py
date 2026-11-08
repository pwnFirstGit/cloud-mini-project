"""Pure-stdlib schema validation for the 4-key JSON output.

Shared by service/app.py and tests/test_service.py so the test exercises
the real rule: exactly the keys intent/date/time/place, intent one of the
8 in schema.json, slots strings or null. Returns the parsed object or None.
"""
import json

INTENTS = {"alarm_set", "alarm_query", "calendar_set", "calendar_query",
           "calendar_remove", "weather_query", "datetime_query",
           "recommendation_events"}
KEYS = {"intent", "date", "time", "place"}


def validate(raw: str):
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(obj, dict) or set(obj) != KEYS:
        return None
    if obj["intent"] not in INTENTS:
        return None
    if any(v is not None and not isinstance(v, str)
           for k, v in obj.items() if k != "intent"):
        return None
    return obj
