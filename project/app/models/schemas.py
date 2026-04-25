from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    zipCode: str = Field(..., min_length=5, max_length=10)
    cuisine: str = Field(..., min_length=2, max_length=50)
    partySize: int = Field(..., ge=1, le=20)
    budget: str = Field(..., description="low | medium | high | luxury")
    value: str = ""
    service: str = ""
    wait: str = ""
    vibe: str = ""
    signature_dishes: list[str] = Field(default_factory=list)
    group_suitability: str = ""
    portion: str = ""
    noisy: bool = False
    quiet: bool = False
    casual: bool = False
    upscale: bool = False
    googleMapsApiKey: str = Field(..., min_length=20, max_length=200, exclude=True)
    geminiApiKey: str = Field(..., min_length=20, max_length=200, exclude=True)

    @field_validator("zipCode")
    @classmethod
    def validate_zipcode(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.replace("-", "").isdigit():
            raise ValueError("zipCode should be numeric (or ZIP+4).")
        return cleaned

    @field_validator("budget")
    @classmethod
    def validate_budget(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in {"low", "medium", "high", "luxury"}:
            raise ValueError("budget must be one of: low, medium, high, luxury")
        return cleaned

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
    types: list[str] = Field(default_factory=list)
    photos: list[dict] = Field(default_factory=list)
    reviews: list[dict] = Field(default_factory=list)
    reservable: bool | None = None
    reservation_link: str | None = None
    maps_link: str | None = None
    location: PlaceLocation


class ReviewEvidence(BaseModel):
    text: str
    rating: int | float = 0
    author_name: str = ""
    relative_time_description: str = ""
    source: str = "Google Places review"
    matched_terms: list[str] = Field(default_factory=list)


class ReviewAnalysisResult(BaseModel):
    signature_dishes: list[str] = Field(default_factory=list)
    service: str = "Unknown"
    value: str = "Unknown"
    wait_impression: str = "Unknown"
    vibe: str = "Unknown"
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    evidence: list[ReviewEvidence] = Field(default_factory=list)


class ImageAnalysisResult(BaseModel):
    visual_vibe: str = "unknown"
    space_impression: str = "unknown"
    food_visual_cues: list[str] = Field(default_factory=list)
    group_suitability: str = "unknown"
    visual_confidence: str = "low"
    image_evidence_summary: str = "Image analysis was unavailable."


class DossierResult(BaseModel):
    restaurant_name: str
    rating: float
    price_level: int = 0
    address: str
    signature_dishes: list[str] = Field(default_factory=list)
    service: str = "Unknown"
    value: str = "Unknown"
    wait_impression: str = "Unknown"
    vibe: str = "Unknown"
    summary: str = ""
    why_recommended: str = ""
    types: list[str] = Field(default_factory=list)
    user_rating_count: int = 0
    location: PlaceLocation
    photos: list[dict] = Field(default_factory=list)
    reviews: list[dict] = Field(default_factory=list)
    review_evidence: list[ReviewEvidence] = Field(default_factory=list)
    image_analysis: ImageAnalysisResult = Field(default_factory=ImageAnalysisResult)
    photo_urls: list[str] = Field(default_factory=list)
    recommendation_confidence: str = "medium"
    reservable: bool | None = None
    reservation_link: str | None = None
    maps_link: str | None = None


class ScoreBreakdown(BaseModel):
    cuisine_match: float
    budget_match: float
    rating: float
    review_value_match: float
    vibe_fit: float
    visual_vibe_fit: float = 0
    evidence_quality: float = 0
    wait_penalty: float
    total: float


class RankedResult(BaseModel):
    score: ScoreBreakdown
    dossier: DossierResult


class APIResponse(BaseModel):
    query: SearchRequest
    total_candidates: int
    top_results: list[RankedResult]
    notes: list[str] = Field(default_factory=list)
