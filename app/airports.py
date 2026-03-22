"""US airport/airline database and shared constants."""

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Major US airports: (IATA code, city, name)
AIRPORTS = [
    ("ATL", "Atlanta", "Hartsfield-Jackson Atlanta International"),
    ("AUS", "Austin", "Austin-Bergstrom International"),
    ("BNA", "Nashville", "Nashville International"),
    ("BOS", "Boston", "Boston Logan International"),
    ("BUR", "Burbank", "Hollywood Burbank"),
    ("BWI", "Baltimore", "Baltimore/Washington International"),
    ("CLE", "Cleveland", "Cleveland Hopkins International"),
    ("CLT", "Charlotte", "Charlotte Douglas International"),
    ("CVG", "Cincinnati", "Cincinnati/Northern Kentucky International"),
    ("DAL", "Dallas", "Dallas Love Field"),
    ("DCA", "Washington", "Ronald Reagan Washington National"),
    ("DEN", "Denver", "Denver International"),
    ("DFW", "Dallas/Fort Worth", "Dallas/Fort Worth International"),
    ("DTW", "Detroit", "Detroit Metropolitan Wayne County"),
    ("EWR", "Newark", "Newark Liberty International"),
    ("FLL", "Fort Lauderdale", "Fort Lauderdale-Hollywood International"),
    ("HNL", "Honolulu", "Daniel K. Inouye International"),
    ("HOU", "Houston", "William P. Hobby"),
    ("IAD", "Washington", "Washington Dulles International"),
    ("IAH", "Houston", "George Bush Intercontinental"),
    ("IND", "Indianapolis", "Indianapolis International"),
    ("JAX", "Jacksonville", "Jacksonville International"),
    ("JFK", "New York", "John F. Kennedy International"),
    ("LAS", "Las Vegas", "Harry Reid International"),
    ("LAX", "Los Angeles", "Los Angeles International"),
    ("LGA", "New York", "LaGuardia"),
    ("MCI", "Kansas City", "Kansas City International"),
    ("MCO", "Orlando", "Orlando International"),
    ("MDW", "Chicago", "Chicago Midway International"),
    ("MIA", "Miami", "Miami International"),
    ("MKE", "Milwaukee", "Milwaukee Mitchell International"),
    ("MSP", "Minneapolis", "Minneapolis-Saint Paul International"),
    ("MSY", "New Orleans", "Louis Armstrong New Orleans International"),
    ("OAK", "Oakland", "Oakland International"),
    ("ONT", "Ontario", "Ontario International"),
    ("ORD", "Chicago", "O'Hare International"),
    ("PBI", "West Palm Beach", "Palm Beach International"),
    ("PDX", "Portland", "Portland International"),
    ("PHL", "Philadelphia", "Philadelphia International"),
    ("PHX", "Phoenix", "Phoenix Sky Harbor International"),
    ("PIT", "Pittsburgh", "Pittsburgh International"),
    ("RDU", "Raleigh/Durham", "Raleigh-Durham International"),
    ("RSW", "Fort Myers", "Southwest Florida International"),
    ("SAN", "San Diego", "San Diego International"),
    ("SAT", "San Antonio", "San Antonio International"),
    ("SEA", "Seattle", "Seattle-Tacoma International"),
    ("SFO", "San Francisco", "San Francisco International"),
    ("SJC", "San Jose", "San Jose International"),
    ("SLC", "Salt Lake City", "Salt Lake City International"),
    ("SMF", "Sacramento", "Sacramento International"),
    ("SNA", "Santa Ana", "John Wayne Airport"),
    ("STL", "St. Louis", "St. Louis Lambert International"),
    ("TPA", "Tampa", "Tampa International"),
]

# Major US airlines: (IATA code, name)
AIRLINES = [
    ("UA", "United Airlines"),
    ("DL", "Delta Air Lines"),
    ("AA", "American Airlines"),
    ("WN", "Southwest Airlines"),
    ("B6", "JetBlue Airways"),
    ("AS", "Alaska Airlines"),
    ("NK", "Spirit Airlines"),
    ("F9", "Frontier Airlines"),
    ("HA", "Hawaiian Airlines"),
    ("SY", "Sun Country Airlines"),
    ("G4", "Allegiant Air"),
]


def search_airports(query: str) -> list[dict]:
    """Search airports by code, city name, or airport name."""
    q = query.lower().strip()
    if not q:
        return []

    results = []
    for code, city, name in AIRPORTS:
        if (
            q in code.lower()
            or q in city.lower()
            or q in name.lower()
        ):
            results.append({"code": code, "city": city, "name": name})

    return results[:10]
