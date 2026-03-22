"""FlightClaw - FastAPI application."""

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.agent import run_agent, set_concurrency
from app.airports import AIRLINES, search_airports
from app.scraper import close_browser

APP_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app):
    concurrency = int(os.environ.get("WORKERS", "2"))
    set_concurrency(concurrency)
    yield
    await close_browser()


app = FastAPI(title="FlightClaw", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/search")


@app.get("/api/airports")
async def api_airports(q: str = Query("", min_length=1)):
    return search_airports(q)


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "airlines": AIRLINES,
    })


@app.get("/search/stream")
async def search_stream(
    origin: str = Query(...),
    destinations: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    min_days: int = Query(5),
    max_days: int = Query(30),
    airlines: str = Query(""),
    earliest_dep_out: str = Query(""),
    earliest_dep_ret: str = Query(""),
):
    dest_list = [d.strip() for d in destinations.split(",") if d.strip()]
    airline_list = [a.strip() for a in airlines.split(",") if a.strip()]

    async def event_stream():
        async for event in run_agent(
            origin=origin,
            destinations=dest_list,
            start_date=start_date,
            end_date=end_date,
            min_days=min_days,
            max_days=max_days,
            airlines=airline_list,
            earliest_dep_out=earliest_dep_out,
            earliest_dep_ret=earliest_dep_ret,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
