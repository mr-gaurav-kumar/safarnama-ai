"""Official Indian tourism statistics, as a dated snapshot.

Every figure below was copied from a Ministry of Tourism publication (or a page
reproducing one), and each series names its source and reference period. It is
a snapshot, not a live feed: update the numbers and the `as_of` fields together
when a new edition is published.

Used in two places:
  * GET /insights -- the Insights dashboard
  * the itinerary prompt -- a line of real context about the destination's
    state and the travel month (see `context_for_trip`)
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


@dataclass(frozen=True)
class Source:
    title: str
    url: str


SNAPSHOT_2025 = Source(
    "Annual Tourism Snapshot 2025, Ministry of Tourism",
    "https://tourism.gov.in/sites/default/files/2026-02/Annual%20Tourism%20Snapshot%202025.pdf",
)
COMPENDIUM_2025 = Source(
    "India Tourism Data Compendium 2025, Ministry of Tourism",
    "https://tourism.gov.in/sites/default/files/2025-09/India%20Tourism%20Data%20Compendium%202025_1.pdf",
)
DH_DTV_2024 = Source(
    "Deccan Herald, reporting the India Tourism Data Compendium 2025",
    "https://www.deccanherald.com/india/indias-go-to-holiday-destinations-top-10-most-visited-states-in-2024-25-by-domestic-tourists-3818090",
)
WIKI_FTV_2024 = Source(
    "Wikipedia, 'Tourism in India' (state-wise foreign visits, from the Compendium)",
    "https://en.wikipedia.org/wiki/Tourism_in_India",
)


# --- foreign tourist ARRIVALS into India, by month, 2025 (lakh) -------------
# Source: Annual Tourism Snapshot 2025. Sums to the published total of 90.2 lakh.
FTA_MONTHLY_2025_LAKH: tuple[float, ...] = (
    9.56, 9.16, 7.42, 6.26, 4.74, 5.48, 6.69, 6.28, 6.24, 7.98, 9.54, 10.82,
)
FTA_TOTAL_2025_LAKH = 90.2

# --- state-wise VISITS, 2024 (million) ----------------------------------------
# Visits, not arrivals: one traveller seeing three states counts three times.
# Top two of each list are quoted directly in the Compendium; the rest come
# from the reproductions cited alongside.
DTV_BY_STATE_2024_M: tuple[tuple[str, float], ...] = (
    ("Uttar Pradesh", 646.81),
    ("Tamil Nadu", 306.84),
    ("Karnataka", 304.6),
    ("Andhra Pradesh", 290.3),
    ("Rajasthan", 230.1),
    ("Maharashtra", 189.4),
    ("West Bengal", 184.5),
    ("Gujarat", 184.0),
    ("Madhya Pradesh", 133.0),
)
DTV_TOTAL_2024_M = 2948.19

FTV_BY_STATE_2024_M: tuple[tuple[str, float], ...] = (
    ("Maharashtra", 3.71),
    ("West Bengal", 3.12),
    ("Gujarat", 2.27),
    ("Uttar Pradesh", 2.26),
    ("Rajasthan", 2.07),
    ("Delhi", 1.99),
    ("Tamil Nadu", 1.16),
    ("Kerala", 0.73),
    ("Bihar", 0.73),
    ("Punjab", 0.54),
)
FTV_TOTAL_2024_M = 20.94

# --- most-visited ticketed ASI monuments, FY 2024-25 (million visitors) ------
MONUMENTS_FY2425: tuple[dict, ...] = (
    {"name": "Taj Mahal", "place": "Agra, Uttar Pradesh", "domestic_m": 6.26, "foreign_m": 0.645},
    {"name": "Sun Temple", "place": "Konark, Odisha", "domestic_m": 3.57, "foreign_m": None},
    {"name": "Qutub Minar", "place": "Delhi", "domestic_m": 3.20, "foreign_m": 0.22},
)


# ---------------------------------------------------------------------------
# More official series (India Tourism Data Compendium 2025 = 2024 data;
# Annual Tourism Snapshot 2025 = 2025 data)
# ---------------------------------------------------------------------------

COMPENDIUM_2024 = Source(
    "India Tourism Data Compendium 2024, Ministry of Tourism",
    "https://tourism.gov.in/sites/default/files/2025-03/India%20Tourism%20Data%20Compendium%202024.pdf",
)
COMPENDIUM_2025_PORTAL = Source(
    "India Tourism Data Compendium 2025 (India Tourism Data Portal copy)",
    "https://data.tourism.gov.in/mrd/Uploads/tourism_data/India%20Tourism%20Data%20Compendium%202025_1.pdf",
)
POLICYEDGE_2025 = Source(
    "The Policy Edge, reporting Ministry of Tourism figures for 2025",
    "https://www.policyedge.in/p/domestic-tourism-surges-in-2025-but-foreign-arrivals-and-earnings-fall",
)

# Foreign tourist arrivals into India, by year (million). 2014-2024 from the
# Compendium 2025 (revised series); 2025 from the Annual Tourism Snapshot 2025.
FTA_BY_YEAR_M: tuple[tuple[int, float], ...] = (
    (2014, 7.68), (2015, 8.03), (2016, 8.80), (2017, 10.04), (2018, 10.56),
    (2019, 10.93), (2020, 2.74), (2021, 1.52), (2022, 6.44), (2023, 9.51),
    (2024, 9.95), (2025, 9.02),
)

# Foreign exchange earnings from tourism (US$ billion), same sources.
FEE_BY_YEAR_USD_BN: tuple[tuple[int, float], ...] = (
    (2014, 19.70), (2015, 21.01), (2016, 22.43), (2017, 27.37), (2018, 28.57),
    (2019, 30.72), (2020, 13.04), (2021, 8.65), (2022, 21.36), (2023, 32.19),
    (2024, 35.02), (2025, 31.33),
)

# Indian nationals' departures abroad (million).
DEPARTURES_BY_YEAR_M: tuple[tuple[int, float], ...] = (
    (2019, 26.92), (2020, 7.20), (2022, 18.21), (2023, 27.88), (2024, 30.89), (2025, 32.71),
)

# Top source countries for foreign tourist arrivals (number of arrivals).
SOURCE_COUNTRIES_2024: tuple[tuple[str, int], ...] = (
    ("United States", 1_804_586), ("Bangladesh", 1_750_165), ("United Kingdom", 1_022_587),
    ("Australia", 518_205), ("Canada", 476_273), ("Malaysia", 307_526),
    ("Sri Lanka", 281_827), ("Germany", 256_348), ("France", 206_855), ("Singapore", 205_383),
)
SOURCE_COUNTRIES_2025_M: tuple[tuple[str, float], ...] = (
    ("United States", 1.80), ("United Kingdom", 1.07), ("Australia", 0.54), ("Canada", 0.53),
    ("Bangladesh", 0.47), ("Malaysia", 0.33), ("Sri Lanka", 0.30), ("Germany", 0.27),
    ("Nepal", 0.22), ("Japan", 0.22),
)

# Why foreign tourists came, 2024 (% of FTAs).
PURPOSE_2024_PCT: tuple[tuple[str, float], ...] = (
    ("Leisure, holiday & recreation", 45.00), ("Indian diaspora", 28.49),
    ("Business & professional", 10.52), ("Medical", 6.48), ("Education", 0.59),
)

# Busiest ports of entry for foreign tourists, 2025 (% of FTAs).
PORTS_2025_PCT: tuple[tuple[str, float], ...] = (
    ("Delhi airport", 35.0), ("Mumbai airport", 18.0), ("Bengaluru airport", 9.1),
    ("Chennai airport", 8.9), ("Hyderabad airport", 4.8),
)

KEY_FACTS_2024: tuple[dict, ...] = (
    {"label": "International tourist arrivals", "value": "20.57 million", "note": "9.95 M foreigners + 10.62 M NRIs"},
    {"label": "Tourism forex earnings", "value": "₹2,93,033 crore", "note": "US$ 35.02 billion"},
    {"label": "Share of world tourism receipts", "value": "2.02%", "note": "India ranked 15th"},
    {"label": "Jobs supported by tourism", "value": "84.6 million", "note": "direct and indirect"},
    {"label": "Tourism share of GDP", "value": "5.22%", "note": "Tourism Satellite Account"},
    {"label": "Average stay of a foreign tourist", "value": "18.1 days", "note": ""},
    {"label": "Foreign tourists arriving by air", "value": "83.4%", "note": "land 16.1%, sea 0.6%"},
    {"label": "Gender split of foreign tourists", "value": "57% men · 43% women", "note": ""},
)

YEAR_ON_YEAR_2025: tuple[dict, ...] = (
    {"indicator": "Foreign tourist arrivals", "y2024": "99.5 lakh", "y2025": "90.2 lakh", "change": -9.4},
    {"indicator": "Forex earnings (US$)", "y2024": "35.02 bn", "y2025": "31.33 bn", "change": -10.5},
    {"indicator": "Indian nationals going abroad", "y2024": "308.9 lakh", "y2025": "327.1 lakh", "change": 5.9},
    {"indicator": "Domestic tourist visits", "y2024": "294.6 crore", "y2025": "428.6 crore", "change": 45.5},
)

REPORTS: tuple[dict, ...] = (
    {"title": "Annual Tourism Snapshot 2025", "kind": "PDF", "year": 2026,
     "about": "Arrivals, earnings, source countries and ports for calendar 2025.",
     "url": SNAPSHOT_2025.url},
    {"title": "India Tourism Data Compendium 2025", "kind": "PDF", "year": 2025,
     "about": "The main yearly statistics book — every table for 2024.",
     "url": COMPENDIUM_2025.url},
    {"title": "India Tourism Data Compendium 2024", "kind": "PDF", "year": 2025,
     "about": "Previous edition — full tables for 2023.",
     "url": COMPENDIUM_2024.url},
    {"title": "Data Compendium Key Highlights 2024", "kind": "PDF", "year": 2025,
     "about": "A short summary of the headline numbers.",
     "url": "https://tourism.gov.in/sites/default/files/2025-03/India%20Tourism%20Data%20Compendium%20Key%20Highlights%202024%20(1).pdf"},
    {"title": "India Tourism Statistics 2023", "kind": "PDF", "year": 2023,
     "about": "Detailed statistics for 2022, state by state.",
     "url": "https://www.data.tourism.gov.in/mrd/Uploads/tourism_data/India%20Tourism%20Statistics%202023-English%20(1).pdf"},
    {"title": "India Tourism Statistics 2022", "kind": "PDF", "year": 2022,
     "about": "Detailed statistics for 2021 (revised edition).",
     "url": "https://tourism.gov.in/sites/default/files/2023-01/India%20Tourism%20Statistics%20English%202022%20(Revised).pdf"},
    {"title": "India Tourism Statistics at a Glance 2023", "kind": "Page", "year": 2023,
     "about": "Pocket summary of the key numbers.",
     "url": "https://www.tourism.gov.in/annual-reports/india-tourism-statistics-glance-2023"},
    {"title": "India Tourism Data Portal", "kind": "Portal", "year": None,
     "about": "Ministry of Tourism's data portal and live dashboard.",
     "url": "https://data.tourism.gov.in/"},
    {"title": "Research & Analytics", "kind": "Page", "year": None,
     "about": "All market research and statistics publications.",
     "url": "https://tourism.gov.in/index.php/market-research-and-statistics"},
    {"title": "Annual Reports", "kind": "Page", "year": None,
     "about": "Ministry of Tourism annual reports.",
     "url": "https://www.tourism.gov.in/media/annual-reports"},
    {"title": "Tourism datasets on data.gov.in", "kind": "Open data", "year": None,
     "about": "Downloadable CSV datasets from the Open Government Data platform.",
     "url": "https://www.data.gov.in/catalog/india-tourism-statistics"},
)


# --- destination -> state ------------------------------------------------------
# Enough to recognise common trip destinations; a state or UT typed directly is
# matched too. Unmatched destinations simply get no state line.
STATES_AND_UTS = (
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Jammu and Kashmir",
    "Ladakh", "Puducherry", "Chandigarh", "Andaman and Nicobar Islands",
    "Lakshadweep",
)

CITY_TO_STATE = {
    # Rajasthan
    "jaipur": "Rajasthan", "udaipur": "Rajasthan", "jodhpur": "Rajasthan",
    "jaisalmer": "Rajasthan", "pushkar": "Rajasthan", "ajmer": "Rajasthan",
    "mount abu": "Rajasthan", "bikaner": "Rajasthan", "ranthambore": "Rajasthan",
    # Uttar Pradesh
    "agra": "Uttar Pradesh", "varanasi": "Uttar Pradesh", "ayodhya": "Uttar Pradesh",
    "mathura": "Uttar Pradesh", "vrindavan": "Uttar Pradesh", "lucknow": "Uttar Pradesh",
    "prayagraj": "Uttar Pradesh",
    # Maharashtra
    "mumbai": "Maharashtra", "pune": "Maharashtra", "lonavala": "Maharashtra",
    "mahabaleshwar": "Maharashtra", "aurangabad": "Maharashtra", "nashik": "Maharashtra",
    # Karnataka
    "bengaluru": "Karnataka", "bangalore": "Karnataka", "mysuru": "Karnataka",
    "mysore": "Karnataka", "coorg": "Karnataka", "hampi": "Karnataka", "gokarna": "Karnataka",
    # Tamil Nadu
    "chennai": "Tamil Nadu", "ooty": "Tamil Nadu", "kodaikanal": "Tamil Nadu",
    "madurai": "Tamil Nadu", "mahabalipuram": "Tamil Nadu", "rameswaram": "Tamil Nadu",
    "kanyakumari": "Tamil Nadu",
    # Kerala
    "kochi": "Kerala", "munnar": "Kerala", "alleppey": "Kerala", "alappuzha": "Kerala",
    "varkala": "Kerala", "thiruvananthapuram": "Kerala", "wayanad": "Kerala",
    # Himachal Pradesh
    "manali": "Himachal Pradesh", "shimla": "Himachal Pradesh",
    "dharamshala": "Himachal Pradesh", "kasol": "Himachal Pradesh",
    "spiti": "Himachal Pradesh", "dalhousie": "Himachal Pradesh",
    # Uttarakhand
    "rishikesh": "Uttarakhand", "haridwar": "Uttarakhand", "nainital": "Uttarakhand",
    "mussoorie": "Uttarakhand", "auli": "Uttarakhand",
    # others
    "leh": "Ladakh", "srinagar": "Jammu and Kashmir", "gulmarg": "Jammu and Kashmir",
    "pahalgam": "Jammu and Kashmir", "darjeeling": "West Bengal", "kolkata": "West Bengal",
    "gangtok": "Sikkim", "shillong": "Meghalaya", "hyderabad": "Telangana",
    "tirupati": "Andhra Pradesh", "visakhapatnam": "Andhra Pradesh",
    "ahmedabad": "Gujarat", "kutch": "Gujarat", "rann of kutch": "Gujarat",
    "dwarka": "Gujarat", "puri": "Odisha", "konark": "Odisha", "bhubaneswar": "Odisha",
    "khajuraho": "Madhya Pradesh", "ujjain": "Madhya Pradesh", "indore": "Madhya Pradesh",
    "bhopal": "Madhya Pradesh", "pachmarhi": "Madhya Pradesh", "amritsar": "Punjab",
    "bodh gaya": "Bihar", "new delhi": "Delhi", "pondicherry": "Puducherry",
    "port blair": "Andaman and Nicobar Islands", "havelock": "Andaman and Nicobar Islands",
    "andaman": "Andaman and Nicobar Islands",
}


def _words(s: str) -> str:
    return " " + re.sub(r"[^a-z]+", " ", s.lower()).strip() + " "


def state_for(destination: str) -> str | None:
    text = _words(destination)
    # Longest names first, so "Madhya Pradesh" beats "Pradesh"-ish partials and
    # "rann of kutch" beats "kutch".
    for state in sorted(STATES_AND_UTS, key=len, reverse=True):
        if _words(state) in text:
            return state
    for city in sorted(CITY_TO_STATE, key=len, reverse=True):
        if _words(city) in text:
            return CITY_TO_STATE[city]
    return None


def _rank(rows: tuple[tuple[str, float], ...], state: str) -> tuple[int, float] | None:
    for i, (name, value) in enumerate(rows, start=1):
        if name == state:
            return i, value
    return None


def context_for_trip(destination: str, month: int) -> str:
    """One short paragraph of official figures for the planner's prompt.

    Crowd levels are the practical use: a state near the top of these lists, in
    a peak month, means booking ahead and starting early.
    """
    lines: list[str] = []

    state = state_for(destination)
    if state:
        dtv = _rank(DTV_BY_STATE_2024_M, state)
        ftv = _rank(FTV_BY_STATE_2024_M, state)
        parts = []
        if dtv:
            parts.append(f"{dtv[1]:,.1f} million domestic tourist visits (#{dtv[0]} among states)")
        if ftv:
            parts.append(f"{ftv[1]:,.2f} million foreign tourist visits (#{ftv[0]})")
        if parts:
            lines.append(f"{state} in 2024: " + " and ".join(parts) + ".")

    fta = FTA_MONTHLY_2025_LAKH[month - 1]
    busiest = sorted(range(12), key=lambda i: -FTA_MONTHLY_2025_LAKH[i])
    rank = busiest.index(month - 1) + 1
    season = "peak season" if rank <= 4 else "off season" if rank >= 9 else "shoulder season"
    lines.append(
        f"Nationally, {MONTHS[month - 1]} saw {fta:.2f} lakh foreign tourist arrivals in 2025 "
        f"(#{rank} of 12 months, {season})."
    )
    return " ".join(lines)


def insights_payload() -> dict:
    peak = max(range(12), key=lambda i: FTA_MONTHLY_2025_LAKH[i])
    low = min(range(12), key=lambda i: FTA_MONTHLY_2025_LAKH[i])
    return {
        "headline": {
            "domestic_visits_2024_million": DTV_TOTAL_2024_M,
            "foreign_visits_2024_million": FTV_TOTAL_2024_M,
            "foreign_arrivals_2025_lakh": FTA_TOTAL_2025_LAKH,
            "peak_month": MONTHS[peak],
            "quietest_month": MONTHS[low],
        },
        "foreign_arrivals_by_month": {
            "year": 2025,
            "unit": "lakh",
            "rows": [{"month": m, "arrivals": v} for m, v in zip(MONTHS, FTA_MONTHLY_2025_LAKH)],
            "sources": [asdict(SNAPSHOT_2025)],
        },
        "domestic_visits_by_state": {
            "year": 2024,
            "unit": "million",
            "rows": [{"state": s, "visits": v} for s, v in DTV_BY_STATE_2024_M],
            "sources": [asdict(COMPENDIUM_2025), asdict(DH_DTV_2024)],
        },
        "foreign_visits_by_state": {
            "year": 2024,
            "unit": "million",
            "rows": [{"state": s, "visits": v} for s, v in FTV_BY_STATE_2024_M],
            "sources": [asdict(COMPENDIUM_2025), asdict(WIKI_FTV_2024)],
        },
        "top_monuments": {
            "period": "FY 2024-25",
            "unit": "million visitors",
            "rows": list(MONUMENTS_FY2425),
            "sources": [asdict(COMPENDIUM_2025)],
        },
        "foreign_arrivals_by_year": {
            "unit": "million",
            "rows": [{"year": y, "value": v} for y, v in FTA_BY_YEAR_M],
            "sources": [asdict(COMPENDIUM_2025_PORTAL), asdict(SNAPSHOT_2025)],
        },
        "forex_earnings_by_year": {
            "unit": "US$ billion",
            "rows": [{"year": y, "value": v} for y, v in FEE_BY_YEAR_USD_BN],
            "sources": [asdict(COMPENDIUM_2025_PORTAL), asdict(SNAPSHOT_2025)],
        },
        "departures_by_year": {
            "unit": "million",
            "rows": [{"year": y, "value": v} for y, v in DEPARTURES_BY_YEAR_M],
            "sources": [asdict(COMPENDIUM_2025_PORTAL), asdict(SNAPSHOT_2025)],
        },
        "source_countries_2024": {
            "year": 2024,
            "unit": "arrivals",
            "rows": [{"country": c, "value": v} for c, v in SOURCE_COUNTRIES_2024],
            "sources": [asdict(COMPENDIUM_2025_PORTAL)],
        },
        "source_countries_2025": {
            "year": 2025,
            "unit": "million",
            "rows": [{"country": c, "value": v} for c, v in SOURCE_COUNTRIES_2025_M],
            "sources": [asdict(SNAPSHOT_2025)],
        },
        "purpose_of_visit": {
            "year": 2024,
            "unit": "%",
            "rows": [{"label": l, "value": v} for l, v in PURPOSE_2024_PCT],
            "sources": [asdict(COMPENDIUM_2025_PORTAL)],
        },
        "ports_of_entry": {
            "year": 2025,
            "unit": "%",
            "rows": [{"label": l, "value": v} for l, v in PORTS_2025_PCT],
            "sources": [asdict(SNAPSHOT_2025)],
        },
        "key_facts": {
            "year": 2024,
            "rows": list(KEY_FACTS_2024),
            "sources": [asdict(COMPENDIUM_2025_PORTAL)],
        },
        "year_on_year": {
            "rows": list(YEAR_ON_YEAR_2025),
            "sources": [asdict(SNAPSHOT_2025), asdict(POLICYEDGE_2025)],
        },
        "reports": list(REPORTS),
    }
