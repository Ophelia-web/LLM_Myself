import httpx

from app.models.schemas import GeocodeResult


GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


async def geocode_zip(zip_code: str, maps_api_key: str) -> GeocodeResult:
    if not maps_api_key.strip():
        raise ValueError("GOOGLE_MAPS_API_KEY is required.")

    params = {
        "address": zip_code,
        "components": f"postal_code:{zip_code}|country:US",
        "key": maps_api_key,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(GEOCODE_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    results = payload.get("results", [])
    if payload.get("status") != "OK" or not results:
        raise ValueError(f"Could not geocode zip code '{zip_code}'.")

    location = results[0]["geometry"]["location"]
    return GeocodeResult(lat=location["lat"], lng=location["lng"], zipCode=zip_code)
