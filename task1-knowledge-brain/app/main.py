from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.storage import init_db, search_articles
from app.scraper import ingest


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI Tech Consultant - Knowledge Brain",
    version="0.1.0",
    lifespan=lifespan,
)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


@app.get("/health")
def health():
    return {"status": "ok", "service": "knowledge-brain"}


@app.post("/ingest")
async def run_ingestion(max_pages: int = 10):
    if not 1 <= max_pages <= 50:
        raise HTTPException(
            status_code=400,
            detail="max_pages must be between 1 and 50",
        )

    return await ingest(max_pages=max_pages)


@app.post("/ask")
def ask(request: AskRequest):
    matches = search_articles(request.question, limit=3)

    if not matches or matches[0]["score"] < 2:
        return {
            "answer": (
                "I could not find enough relevant information "
                "in the indexed articles to answer reliably. "
                "Please ask a human expert."
            ),
            "sources": [],
            "needs_human_review": True,
        }

    sources = [
        {"title": item["title"], "url": item["url"]}
        for item in matches
    ]

    return {
        "answer": (
            "I found potentially relevant help-center articles. "
            "Review these sources to verify the answer: "
            + " ".join(
                f"{item['title']}: {item['content'][:700]}"
                for item in matches
            )
        ),
        "sources": sources,
        "needs_human_review": True,
    }