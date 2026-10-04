import json
import os
import threading
import uuid
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
_lock = threading.RLock()


def uid(prefix):
    return prefix + uuid.uuid4().hex[:8]


def now():
    return datetime.now().isoformat(timespec="seconds")


def path(name):
    return os.path.join(DATA, name + ".json")


def load(name):
    with _lock:
        with open(path(name), encoding="utf-8") as f:
            return json.load(f)


def save(name, data):
    with _lock:
        tmp = path(name) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path(name))


def get(name, item_id):
    return next((x for x in load(name) if x["id"] == item_id), None)
