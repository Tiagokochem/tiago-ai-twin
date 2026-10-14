from pydantic import BaseModel, Field, field_validator

from twin.agent.state import HandoffReason, Intent, Lang


class Analysis(BaseModel):
    intent: Intent
    lang: Lang
    search_query: str = Field(description="standalone keyword search query")
    handoff_reason: HandoffReason = "none"


class Grade(BaseModel):
    relevant_ids: list[int] = Field(description="ids of the useful passages")


class Rewrite(BaseModel):
    query: str


class Followups(BaseModel):
    questions: list[str] = Field(description="exactly 3 short questions")

    @field_validator("questions")
    @classmethod
    def _clean(cls, value: list[str]) -> list[str]:
        return [q.strip() for q in value if q.strip()][:3]
