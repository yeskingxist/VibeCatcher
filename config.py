import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).parent.resolve()
SESSION_FILE = BASE_DIR / "session.json"
CONFIG_FILE = BASE_DIR / "settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "safety_preset": "safe",  # "safe", "normal", "aggressive"
    "proxy": None,            # e.g., "http://user:pass@host:port" or "socks5://host:port"
    "custom_device": {
        "app_version": "315.0.0.35.109",
        "android_version": 30,
        "android_release": "11.0",
        "device_model": "Pixel 5",
        "manufacturer": "Google",
    },
    "rate_limits": {
        "safe": {
            "comment_delay": (8, 20),      # min, max seconds
            "follow_delay": (15, 35),
            "dm_delay": (5, 12),
            "post_delete_delay": (3, 8),
            "max_comments_per_hour": 15,
            "max_follows_per_day": 35,
            "max_dms_per_hour": 30,
        },
        "normal": {
            "comment_delay": (5, 12),
            "follow_delay": (8, 20),
            "dm_delay": (3, 8),
            "post_delete_delay": (2, 5),
            "max_comments_per_hour": 30,
            "max_follows_per_day": 75,
            "max_dms_per_hour": 60,
        },
        "aggressive": {
            "comment_delay": (2, 6),
            "follow_delay": (4, 10),
            "dm_delay": (2, 5),
            "post_delete_delay": (1, 3),
            "max_comments_per_hour": 60,
            "max_follows_per_day": 150,
            "max_dms_per_hour": 120,
        }
    }
}

class AppConfig:
    def __init__(self):
        self.config_path = CONFIG_FILE
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Merge with default settings
                    merged = DEFAULT_SETTINGS.copy()
                    merged.update(loaded)
                    return merged
            except Exception:
                return DEFAULT_SETTINGS.copy()
        return DEFAULT_SETTINGS.copy()

    def save(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

    @property
    def proxy(self) -> Optional[str]:
        return self.data.get("proxy")

    @proxy.setter
    def proxy(self, val: Optional[str]):
        self.data["proxy"] = val
        self.save()

    @property
    def safety_preset(self) -> str:
        return self.data.get("safety_preset", "safe")

    @safety_preset.setter
    def safety_preset(self, val: str):
        if val in ("safe", "normal", "aggressive"):
            self.data["safety_preset"] = val
            self.save()

    def get_delays_and_limits(self) -> Dict[str, Any]:
        preset = self.safety_preset
        limits = self.data.get("rate_limits", DEFAULT_SETTINGS["rate_limits"])
        return limits.get(preset, limits["safe"])

config = AppConfig()
