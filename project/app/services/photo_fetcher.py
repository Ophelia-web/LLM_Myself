from urllib.parse import urlencode


GOOGLE_PLACE_PHOTO_URL = "https://maps.googleapis.com/maps/api/place/photo"


def build_photo_url(
    photo_reference: str,
    maps_api_key: str,
    max_width: int = 900,
) -> str:
    cleaned_reference = (photo_reference or "").strip()
    if not cleaned_reference:
        return ""
    api_key = (maps_api_key or "").strip()
    if not api_key:
        return ""

    params = urlencode(
        {
            "maxwidth": str(max_width),
            "photo_reference": cleaned_reference,
            "photoreference": cleaned_reference,
            "key": api_key,
        }
    )
    return f"{GOOGLE_PLACE_PHOTO_URL}?{params}"


def build_photo_urls(
    restaurant_name: str,
    photos: list[dict],
    maps_api_key: str,
    max_width: int = 900,
    limit: int = 3,
) -> list[str]:
    if not photos:
        print(f"[PHOTO FETCHER] {restaurant_name}: produced 0 photo URLs (no photos).")
        return []

    urls: list[str] = []
    for photo in photos[:limit]:
        reference = str(photo.get("photo_reference", "")).strip()
        if not reference:
            continue
        url = build_photo_url(
            photo_reference=reference,
            maps_api_key=maps_api_key,
            max_width=max_width,
        )
        if url:
            urls.append(url)
    print(f"[PHOTO FETCHER] {restaurant_name}: produced {len(urls)} photo URLs.")
    return urls
