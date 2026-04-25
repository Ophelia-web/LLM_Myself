import os
from urllib.parse import urlencode


GOOGLE_PLACE_PHOTO_URL = "https://maps.googleapis.com/maps/api/place/photo"


def build_photo_url(photo_reference: str, max_width: int = 900) -> str:
    cleaned_reference = (photo_reference or "").strip()
    if not cleaned_reference:
        return ""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key:
        return ""

    params = urlencode(
        {
            "maxwidth": str(max_width),
            "photoreference": cleaned_reference,
            "key": api_key,
        }
    )
    return f"{GOOGLE_PLACE_PHOTO_URL}?{params}"
