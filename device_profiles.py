from typing import Dict, List, Optional


DEVICE_PRESETS: Dict[str, Dict[str, str]] = {
    "poco_f5": {
        "name": "Poco F5",
        "resolution": "2712x1220",
        "aspect_ratio": "20:9",
        "dpi": "460",
        "notes": "Common portrait/landscape mix; useful default for mobile game capture",
    },
    "default": {
        "name": "Default",
        "resolution": "unknown",
        "aspect_ratio": "unknown",
        "dpi": "unknown",
        "notes": "Fallback preset",
    },
}


def get_screen_preset(device_key: Optional[str] = None) -> Dict[str, str]:
    key = (device_key or "default").strip().lower()
    return DEVICE_PRESETS.get(key, DEVICE_PRESETS["default"])


def list_screen_presets() -> List[str]:
    return list(DEVICE_PRESETS.keys())
