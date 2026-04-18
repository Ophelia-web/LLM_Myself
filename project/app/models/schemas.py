from pydantic import BaseModel, Field, field_validator


class SearchQuery(BaseModel):
    zipCode: str = Field(..., min_length=5, max_length=10)
    cuisine: str = Field(..., min_length=2, max_length=50)
    partySize: int = Field(..., ge=1, le=20)
    budget: str = Field(..., description="low|medium|high|luxury")

    @field_validator("zipCode")
    @classmethod
    def validate_zipcode(cls, value: str) -> str:
        if not value.replace("-", "").isdigit():
            raise ValueError("zipCode should be numeric (or ZIP+4).")
        return value

    @field_validator("budget")
    @classmethod
    def validate_budget(cls, value: str) -> str:
        allowed = {"low", "medium", "high", "luxury"}
        normalized = value.lower().strip()
        if normalized not in allowed:
            raise ValueError(f"budget must be one of {sorted(allowed)}")
        return normalized


class SearchRequest(SearchQuery):
    googleMapsApiKey: str = Field(..., min_length=20, max_length=200)
    geminiApiKey: str = Field(..., min_length=20, max_length=200)

    @field_validator("googleMapsApiKey", "geminiApiKey")
    @classmethod
    def validate_api_key(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("API key cannot be empty.")
        return cleaned


class GeocodeResult(BaseModel):
    zipCode: str
    lat: float
    lng: float


class PlaceLocation(BaseModel):
    lat: float
    lng: float


class PlaceResult(BaseModel):
    place_id: str
    name: str
    formatted_address: str
    rating: float = 0.0
    user_rating_count: int = 0
    price_level: int = 0
    types: list[str] = []
    photos: list[dict] = []
    reviews: list[dict] = []
    location: PlaceLocation


class ReviewAnalysisResult(BaseModel):
    signature_dishes: list[str] = []
    service: str
    value: str
    wait_impression: str
    vibe: str
    pros: list[str] = []
    cons: list[str] = []


class DossierResult(BaseModel):
    restaurant_name: str
    rating: float
    price_level: int
    address: str
    summary: str
    signature_dishes: list[str]
    service: str
    value: str
    wait_impression: str
    vibe: str
    why_recommended: str
    types: list[str] = []
    user_rating_count: int = 0
    location: PlaceLocation
    photos: list[dict] = []
    reviews: list[dict] = []


class ScoreBreakdown(BaseModel):
    cuisine_match: float
    budget_match: float
    rating: float
    review_value_match: float
    vibe_fit: float
    wait_penalty: float
    total: float


class RankedResult(BaseModel):
    score: ScoreBreakdown
    dossier: DossierResult


class APIResponse(BaseModel):
    query: SearchQuery
    total_candidates: int
    top_results: list[RankedResult]
    notes: list[str] = []
