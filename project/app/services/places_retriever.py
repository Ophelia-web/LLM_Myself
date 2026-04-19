from typing import Any

import httpx

from app.models.schemas import PlaceLocation, PlaceResult


PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


async def retrieve_restaurant_candidates(
    lat: float,
    lng: float,
    cuisine: str,
    maps_api_key: str,
    limit: int = 10,
) -> list[PlaceResult]:
    if not maps_api_key.strip():
        raise ValueError("GOOGLE_MAPS_API_KEY is required.")

    async with httpx.AsyncClient(timeout=20.0) as client:
        nearby_payload = await _nearby_search(client, maps_api_key, lat, lng, cuisine)
        nearby_results = nearby_payload.get("results", [])[:limit]

        detailed_places: list[PlaceResult] = []
        for item in nearby_results:
            place_id = item.get("place_id")
            if not place_id:
                continue
            details = await _place_details(client, maps_api_key, place_id)
            normalized = _normalize_place(details.get("result", {}))
            if normalized:
                detailed_places.append(normalized)

    return detailed_places


async def _nearby_search(
    client: httpx.AsyncClient,
    api_key: str,
    lat: float,
    lng: float,
    cuisine: str,
) -> dict[str, Any]:
    params = {
        "location": f"{lat},{lng}",
        "radius": 5000,
        "type": "restaurant",
        "keyword": cuisine,
        "key": api_key,
    }
    response = await client.get(PLACES_NEARBY_URL, params=params)
    response.raise_for_status()
    payload = response.json()
    status = payload.get("status")
    if status not in {"OK", "ZERO_RESULTS"}:
        raise ValueError(f"Places nearby search failed: {status}")
    return payload


async def _place_details(
    client: httpx.AsyncClient,
    api_key: str,
    place_id: str,
) -> dict[str, Any]:
    params = {
        "place_id": place_id,
        "fields": (
            "place_id,name,formatted_address,rating,user_ratings_total,price_level,"
            "types,photos,reviews,geometry,reservable,url,website"
        ),
        "reviews_sort": "newest",
        "key": api_key,
    }
    response = await client.get(PLACES_DETAILS_URL, params=params)
    response.raise_for_status()
    payload = response.json()
    status = payload.get("status")
    if status not in {"OK", "ZERO_RESULTS"}:
        raise ValueError(f"Places details failed for {place_id}: {status}")
    return payload


def _normalize_place(raw: dict[str, Any]) -> PlaceResult | None:
    geometry = raw.get("geometry", {}).get("location", {})
    lat = geometry.get("lat")
    lng = geometry.get("lng")
    if lat is None or lng is None:
        return None

    reviews = []
    for review in raw.get("reviews", [])[:5]:
        reviews.append(
            {
                "author_name": review.get("author_name", ""),
                "rating": review.get("rating", 0),
                "text": review.get("text", ""),
                "relative_time_description": review.get("relative_time_description", ""),
            }
        )

    photos = []
    for photo in raw.get("photos", [])[:3]:
        photos.append(
            {
                "photo_reference": photo.get("photo_reference", ""),
                "width": photo.get("width", 0),
                "height": photo.get("height", 0),
            }
        )

    reservable = raw.get("reservable")
    reservation_link = raw.get("url")
    if reservation_link == "":
        reservation_link = None
    if reservable is None and reservation_link:
        reservable = True

    return PlaceResult(
        place_id=raw.get("place_id", ""),
        name=raw.get("name", "Unknown"),
        formatted_address=raw.get("formatted_address", ""),
        rating=raw.get("rating", 0.0),
        user_rating_count=raw.get("user_ratings_total", 0),
        price_level=raw.get("price_level", 0),
        types=raw.get("types", []),
        photos=photos,
        reviews=reviews,
        reservable=reservable if isinstance(reservable, bool) else None,
        reservation_link=reservation_link if isinstance(reservation_link, str) else None,
        location=PlaceLocation(lat=lat, lng=lng),
    )
