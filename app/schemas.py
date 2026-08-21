from pydantic import BaseModel, Field, field_validator

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)

    @field_validator("query")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query must not be blank")
        return v

class ParsedQuery(BaseModel):
    max_price: float | None = None
    veg_only: bool = False
    location: str | None = None
    category: str | None = None
    keywords: list[str] = []

class FoodItem(BaseModel):
    id: int
    name:  str
    restaurant: str
    price: float
    location: str
    veg: bool
    category: str
    rating: float = Field(ge=0, le=5)
    tags: list[str] = []

class SearchResponse(BaseModel):
    query: str
    parsed: ParsedQuery
    count: int
    results: list[FoodItem]