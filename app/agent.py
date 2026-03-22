"""Flight search orchestrator — generates date pairs and runs parallel scrapes."""

import asyncio
from datetime import date, timedelta
from collections.abc import AsyncGenerator
from typing import Optional

from app.scraper import scrape_roundtrip

_concurrency = 1


def set_concurrency(n: int):
    global _concurrency
    _concurrency = n


async def run_agent(
    origin: str,
    destinations: list[str],
    start_date: str,
    end_date: str,
    min_days: int,
    max_days: int,
    airlines: list[str],
    earliest_dep_out: str = "",
    earliest_dep_ret: str = "",
) -> AsyncGenerator[dict, None]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    # Generate unique (depart, return) date pairs
    seen: set[str] = set()
    date_pairs: list[tuple[str, str]] = []
    d = start
    while d <= end:
        for stay in range(min_days, max_days + 1):
            ret = d + timedelta(days=stay - 1)
            if ret <= end:
                key = f"{d.isoformat()}|{ret.isoformat()}"
                if key not in seen:
                    seen.add(key)
                    date_pairs.append((d.isoformat(), ret.isoformat()))
        d += timedelta(days=1)

    search_args = [
        (dest, dep, ret)
        for dest in destinations
        for dep, ret in date_pairs
    ]
    total = len(search_args)

    yield {"type": "stage", "message": f"Scanning flights to {', '.join(destinations)}..."}

    # Run searches concurrently with live progress streaming
    event_queue: asyncio.Queue = asyncio.Queue()
    completed = 0

    async def _search(dest, dep, ret):
        nonlocal completed
        try:
            result = await scrape_roundtrip(
                origin=origin, destination=dest,
                depart_date=dep, return_date=ret,
                airlines=airlines or None,
            )
        except Exception:
            result = []
        completed += 1
        event_queue.put_nowait({"type": "progress", "completed": completed, "total": total})
        return result

    sem = asyncio.Semaphore(_concurrency)

    async def _bounded(dest, dep, ret):
        async with sem:
            return await _search(dest, dep, ret)

    tasks = [asyncio.create_task(_bounded(*a)) for a in search_args]

    # Stream events while tasks run
    while True:
        while not event_queue.empty():
            yield event_queue.get_nowait()
        if all(t.done() for t in tasks):
            break
        await asyncio.sleep(0.3)
    while not event_queue.empty():
        yield event_queue.get_nowait()

    # Collect and filter results
    all_trips = [trip for t in tasks for trip in (t.result() or [])]

    yield {"type": "stage", "message": f"Comparing {len(all_trips)} options..."}

    if not all_trips:
        yield {"type": "stage", "message": "No flights found for your dates."}
        yield {"type": "done", "trips": []}
        return

    if earliest_dep_out:
        all_trips = [t for t in all_trips if not _leg_before(t["outbound"], earliest_dep_out)]
    if earliest_dep_ret:
        all_trips = [t for t in all_trips if not _leg_before(t["return"], earliest_dep_ret)]

    # Deduplicate and rank
    seen_keys: set[str] = set()
    unique = []
    for t in all_trips:
        key = f"{t['outbound_date']}|{t['return_date']}|{t['price']}|{','.join(t['outbound'].get('airlines', []))}"
        if key not in seen_keys:
            seen_keys.add(key)
            unique.append(t)

    unique.sort(key=lambda t: t["price"])

    yield {"type": "stage", "message": "Search complete!" if unique else "No flights matched your criteria."}
    yield {"type": "done", "trips": unique}


def _parse_time(time_str: str) -> Optional[int]:
    """Parse time string like '8:35 AM' into minutes since midnight."""
    if not time_str:
        return None
    time_str = time_str.strip().upper()
    parts = time_str.split(" ")
    if len(parts) > 2:
        time_str = " ".join(parts[-2:])
    is_pm = "PM" in time_str
    is_am = "AM" in time_str
    time_str = time_str.replace("AM", "").replace("PM", "").strip()
    try:
        h, m = time_str.split(":")
        hour = int(h)
        if is_pm and hour != 12:
            hour += 12
        if is_am and hour == 12:
            hour = 0
        return hour * 60 + int(m)
    except (ValueError, IndexError):
        return None



def _leg_before(leg: dict, earliest: str) -> bool:
    """Return True if the leg departs before the earliest time (HH:MM)."""
    try:
        eh, em = earliest.split(":")
        threshold = int(eh) * 60 + int(em)
    except (ValueError, IndexError):
        return False
    dep = _parse_time(leg.get("departure_time", ""))
    return dep is not None and dep < threshold
