"""Google Flights scraper using Playwright."""

from __future__ import annotations

import asyncio
from datetime import date as date_type

from playwright.async_api import async_playwright, Browser, Playwright

from app.airports import WEEKDAYS
from app.flight_search import google_flights_url

_playwright: Playwright | None = None
_browser: Browser | None = None
_lock = asyncio.Lock()


async def get_browser() -> Browser:
    global _playwright, _browser
    async with _lock:
        if _browser and _browser.is_connected():
            return _browser
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        return _browser


async def close_browser():
    global _playwright, _browser
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None


async def scrape_roundtrip(
    origin: str,
    destination: str,
    depart_date: str,
    return_date: str,
    airlines: list[str] | None = None,
) -> list[dict]:
    """Scrape Google Flights for round-trip results."""
    url = google_flights_url(origin, destination, depart_date, return_date,
                             airlines=airlines)

    out_d = date_type.fromisoformat(depart_date)
    ret_d = date_type.fromisoformat(return_date)
    trip_days = (ret_d - out_d).days + 1

    browser = await get_browser()

    TOP_N = 5

    async def _scrape_nth(rank: int):
        """Load a fresh page, click the Nth outbound, return top trips."""
        context = await browser.new_context(viewport={"width": 1280, "height": 900}, locale="en-US")
        try:
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            try:
                await page.wait_for_selector("li[class*='pIav2d']", timeout=8000)
            except Exception:
                return None

            await _dismiss_dialogs(page)

            flights = await _extract_flight_list(page)
            unique = _dedup_flights(flights)

            if rank >= len(unique):
                return None

            outbound = unique[rank]
            dom_idx = outbound.get("_dom_index")
            if dom_idx is None:
                return None

            await asyncio.sleep(1)
            items = await page.query_selector_all("li[class*='pIav2d']")
            if dom_idx >= len(items):
                return None
            await items[dom_idx].click()
            await page.wait_for_function(
                "() => document.body.innerText.toLowerCase().includes('returning')",
                timeout=15000,
            )

            return_flights = await _extract_flight_list(page)
            if return_flights:
                return [
                    _build_trip(
                        origin, destination, depart_date, return_date,
                        out_d, ret_d, trip_days, outbound, ret_f,
                        airlines,
                    )
                    for ret_f in return_flights[:TOP_N]
                ]
            return None
        except Exception as e:
            print(f'[rank={rank}] {e}')
            return None
        finally:
            await context.close()

    trips = []
    for i in range(TOP_N):
        result = await _scrape_nth(i)
        if result:
            trips.extend(result)
    return trips


def _build_trip(origin, destination, depart_date, return_date,
                out_d, ret_d, trip_days, outbound, best_return,
                airlines):
    return {
        "outbound_date": depart_date,
        "outbound_weekday": WEEKDAYS[out_d.weekday()],
        "return_date": return_date,
        "return_weekday": WEEKDAYS[ret_d.weekday()],
        "trip_days": trip_days,
        "origin": origin,
        "destination": destination,
        "price": outbound["price"],
        "num_stops": max(outbound["num_stops"], best_return["num_stops"]),
        "outbound": {
            "airlines": outbound["airlines"],
            "flight_numbers": outbound["flight_numbers"],
            "departure_time": outbound["dep_time"],
            "arrival_time": outbound["arr_time"],
            "stop_category": outbound["stop_category"],
            "duration": outbound.get("duration", ""),
        },
        "return": {
            "airlines": best_return["airlines"],
            "flight_numbers": best_return["flight_numbers"],
            "departure_time": best_return["dep_time"],
            "arrival_time": best_return["arr_time"],
            "stop_category": best_return["stop_category"],
            "duration": best_return.get("duration", ""),
        },
        "google_flights_url": google_flights_url(
            origin, destination, depart_date, return_date,
            airlines=airlines,
        ),
    }



def _dedup_flights(flights):
    """Deduplicate flights by dep_time + arr_time + price, preserving order."""
    seen: set[str] = set()
    unique = []
    for f in flights:
        key = f"{f['dep_time']}|{f['arr_time']}|{f['price']}"
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


async def _dismiss_dialogs(page):
    for selector in [
        "button:has-text('Accept all')",
        "button:has-text('Accept')",
        "button:has-text('Reject all')",
        "button:has-text('I agree')",
        "button[aria-label='Accept all']",
    ]:
        try:
            btn = await page.query_selector(selector)
            if btn:
                await btn.click()
                break
        except Exception:
            continue


async def _extract_flight_list(page) -> list[dict]:
    """Extract flight options from the current page via JS evaluation."""
    flights_data = await page.evaluate("""() => {
        const flights = [];
        const items = document.querySelectorAll('li[class*="pIav2d"]');

        for (let domIdx = 0; domIdx < items.length; domIdx++) {
            const item = items[domIdx];
            const text = item.innerText || '';
            if (text.length < 20) continue;

            let price = 0;
            const priceMatch = text.match(/\\$([\\d,]+)/);
            if (priceMatch) price = parseInt(priceMatch[1].replace(',', ''));
            if (!price) continue;

            // Extract dep/arr times from aria-labels
            let dep_time = '';
            let arr_time = '';
            for (const el of item.querySelectorAll('[aria-label]')) {
                const label = el.getAttribute('aria-label') || '';
                const depMatch = label.match(/[Dd]epart(?:ure)?\\s*(?:time)?[:\\s]+([\\d]{1,2}:[\\d]{2}\\s*(?:AM|PM))/i);
                if (depMatch) { dep_time = depMatch[1].trim(); continue; }
                const arrMatch = label.match(/[Aa]rriv(?:al|e)?\\s*(?:time)?[:\\s]+([\\d]{1,2}:[\\d]{2}\\s*(?:AM|PM))/i);
                if (arrMatch) { arr_time = arrMatch[1].trim(); }
            }

            // Extract flight numbers first — used to infer airline
            const flightNums = [];
            for (const fn of (text.match(/\\b[A-Z][A-Z0-9]\\s?\\d{2,4}\\b/g) || [])) {
                if (!/AM|PM|CO\\d/i.test(fn)) flightNums.push(fn.trim());
            }

            // Infer airline from flight number IATA prefix
            const codeToName = {
                'UA': 'United', 'DL': 'Delta', 'AA': 'American',
                'WN': 'Southwest', 'B6': 'JetBlue', 'AS': 'Alaska',
                'NK': 'Spirit', 'F9': 'Frontier', 'HA': 'Hawaiian',
                'SY': 'Sun Country', 'G4': 'Allegiant',
            };
            let airline = '';
            if (flightNums.length > 0) {
                const code = flightNums[0].replace(/\\s?\\d+$/, '');
                airline = codeToName[code] || code;
            }
            if (!airline) {
                const airlineEl = item.querySelector('[class*="sSHqwe"], [class*="h1fkLb"]');
                if (airlineEl) {
                    airline = airlineEl.innerText.trim().replace(/Operated by.*/i, '').replace(/Separate tickets?/i, '').trim();
                    const parts = airline.match(/^[A-Z][a-zA-Z]+(?:\\s[A-Z][a-zA-Z]+)*/);
                    if (parts) airline = parts[0];
                }
            }

            let stopsText = '';
            let numStops = 0;
            const stopsEl = item.querySelector('[class*="EfT7Ae"], [class*="rGRiKd"]');
            if (stopsEl) stopsText = stopsEl.innerText.trim();
            for (const el of item.querySelectorAll('[aria-label]')) {
                const label = el.getAttribute('aria-label') || '';
                if (label.includes('stop') || label.includes('Nonstop')) {
                    stopsText = label;
                    break;
                }
            }
            if (/nonstop/i.test(stopsText) || /nonstop/i.test(text)) {
                numStops = 0;
            } else {
                const m = (stopsText || text).match(/(\\d+)\\s*stop/i);
                if (m) numStops = parseInt(m[1]);
            }

            let duration = '';
            for (const el of item.querySelectorAll('[aria-label]')) {
                const label = el.getAttribute('aria-label') || '';
                const dm = label.match(/(\\d+)\\s*(?:hr|hour)(?:\\s*(\\d+)\\s*min)?/i);
                if (dm) {
                    duration = dm[2] ? `${dm[1]}h ${dm[2]}m` : `${dm[1]}h`;
                    break;
                }
            }
            if (!duration) {
                const dm = text.match(/(\\d+)\\s*(?:hr|hour)(?:\\s*(\\d+)\\s*min)?/i);
                if (dm) duration = dm[2] ? `${dm[1]}h ${dm[2]}m` : `${dm[1]}h`;
            }

            flights.push({
                price, dep_time, arr_time,
                airline, num_stops: numStops, flight_numbers: flightNums,
                duration, domIndex: domIdx,
            });
        }
        return flights;
    }""")

    return [{
        "price": fd["price"],
        "dep_time": fd["dep_time"],
        "arr_time": fd["arr_time"],
        "airlines": [fd["airline"]] if fd["airline"] else [],
        "flight_numbers": fd["flight_numbers"],
        "num_stops": fd["num_stops"],
        "stop_category": "nonstop" if fd["num_stops"] == 0 else f"{fd['num_stops']}-stop",
        "duration": fd.get("duration", ""),
        "_dom_index": fd["domIndex"],
    } for fd in flights_data]
