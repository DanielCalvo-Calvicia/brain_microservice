from datetime import datetime
from typing import Any


def console_log(component: str, message: str, **fields: Any) -> None:
    timestamp = datetime.now().isoformat(timespec="seconds")
    suffix = ""
    if fields:
        rendered = " ".join(f"{key}={value}" for key, value in fields.items())
        suffix = f" | {rendered}"
    print(f"[{timestamp}] [{component}] {message}{suffix}", flush=True)

