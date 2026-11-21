"""Curated destination features -- the seed data for Phase 8's two models.

CURATED, NOT OFFICIAL. Unlike `tourism.py`, nothing here is copied from a
published dataset; it was put together by hand from general travel knowledge
so the models have something sensible to learn from. Treat every number as a
reasonable estimate and correct it freely. The `destination_features` table is
seeded from this file (see `app.ml.features.ensure_seeded`) and is the copy the
app reads, so edits to rows in the database survive.

Per destination:
  lat, lng, altitude_m, coastal   where it is -- the season model's inputs
  daily_cost   typical mid-range ON-GROUND spend per person per day, INR
               (a share of a double room, three meals, local transport,
               entry tickets). Getting there is NOT included.
  styles       0-1 for each trip style the app uses:
               adventure, relax, culture, food, nature
  region       climate region, for the month-by-month labels below
  closed_months  months when the main draw (usually a national park's core
               safari zones) is normally shut. Dates shift a little each year.

REGION_MONTHS is the season model's training label: one word per month,
Jan..Dec, for each climate region --
  ideal     the best time to go
  pleasant  good, perhaps slightly warm, cool or showery
  hot       uncomfortably hot by day
  rainy     monsoon -- heavy or frequent rain
  cold      cold enough to limit plans (snow, closed passes, freezing nights)
"""
from __future__ import annotations

from dataclasses import dataclass

STYLES = ("adventure", "relax", "culture", "food", "nature")
SEASON_LABELS = ("ideal", "pleasant", "hot", "rainy", "cold")

# --- climate regions -------------------------------------------------------------

_I, _P, _H, _R, _C = SEASON_LABELS

REGION_MONTHS: dict[str, tuple[str, ...]] = {
    #                     Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec
    "himalaya_high":      (_C, _C, _C, _C, _P, _I, _I, _I, _I, _P, _C, _C),
    "himalaya_hills":     (_C, _C, _P, _I, _I, _I, _R, _R, _P, _I, _P, _C),
    "himalaya_foothills": (_P, _I, _I, _P, _H, _H, _R, _R, _R, _I, _I, _P),
    "northern_plains":    (_P, _I, _I, _H, _H, _H, _R, _R, _R, _I, _I, _P),
    "arid_west":          (_I, _I, _P, _H, _H, _H, _R, _R, _P, _P, _I, _I),
    "central":            (_P, _I, _I, _H, _H, _H, _R, _R, _R, _I, _I, _I),
    "west_coast":         (_I, _I, _P, _H, _H, _R, _R, _R, _R, _P, _I, _I),
    "ghats_hills":        (_I, _I, _P, _P, _P, _R, _R, _R, _R, _P, _P, _I),
    "deccan":             (_I, _I, _P, _H, _H, _R, _R, _R, _R, _P, _I, _I),
    # Tamil Nadu's coast gets most of its rain from the north-east monsoon.
    "tamil_coast":        (_I, _I, _P, _H, _H, _H, _H, _P, _P, _R, _R, _P),
    "east":               (_I, _I, _P, _H, _H, _R, _R, _R, _R, _P, _I, _I),
    "northeast":          (_P, _P, _I, _I, _R, _R, _R, _R, _R, _I, _I, _P),
    "islands":            (_I, _I, _I, _P, _R, _R, _R, _R, _R, _P, _I, _I),
}

REGION_NAMES = {
    "himalaya_high": "the high Himalaya",
    "himalaya_hills": "the Himalayan hill stations",
    "himalaya_foothills": "the Himalayan foothills",
    "northern_plains": "the northern plains",
    "arid_west": "Rajasthan and Gujarat",
    "central": "central India",
    "west_coast": "the west coast",
    "ghats_hills": "the Western Ghats hills",
    "deccan": "the Deccan plateau",
    "tamil_coast": "Tamil Nadu",
    "east": "eastern India",
    "northeast": "the Northeast",
    "islands": "the Andaman Islands",
}




def where(region: str) -> str:
    """'on the west coast', 'in the Northeast' -- for sentences."""
    name = REGION_NAMES.get(region, region)
    return ("on " if region == "west_coast" else "in ") + name


@dataclass(frozen=True)
class Destination:
    name: str
    state: str
    region: str
    lat: float
    lng: float
    altitude_m: int
    coastal: bool
    daily_cost: int
    styles: tuple[float, float, float, float, float]  # in STYLES order
    blurb: str
    aliases: tuple[str, ...] = ()
    closed_months: tuple[int, ...] = ()


D = Destination

DESTINATIONS: tuple[Destination, ...] = (
    # --- west coast
    D("Goa", "Goa", "west_coast", 15.30, 74.12, 10, True, 4000, (0.6, 0.9, 0.5, 0.8, 0.6),
      "Beaches, Portuguese-era churches and seafood shacks", ("panaji", "panjim", "calangute", "baga")),
    D("Gokarna", "Karnataka", "west_coast", 14.55, 74.32, 10, True, 2500, (0.5, 0.9, 0.5, 0.4, 0.7),
      "Quiet beaches beside an old temple town"),
    D("Mumbai", "Maharashtra", "west_coast", 19.08, 72.88, 14, True, 4500, (0.2, 0.3, 0.8, 1.0, 0.2),
      "Street food, colonial architecture and the sea face", ("bombay",)),
    D("Kochi", "Kerala", "west_coast", 9.93, 76.27, 5, True, 3200, (0.2, 0.6, 0.9, 0.8, 0.5),
      "Fort Kochi, Chinese fishing nets and spice markets", ("cochin", "fort kochi", "ernakulam")),
    D("Alleppey", "Kerala", "west_coast", 9.49, 76.33, 5, True, 4000, (0.2, 1.0, 0.4, 0.6, 0.9),
      "Backwater houseboats and paddy fields", ("alappuzha", "kumarakom")),
    D("Varkala", "Kerala", "west_coast", 8.73, 76.71, 30, True, 3000, (0.4, 0.9, 0.4, 0.6, 0.7),
      "A cliff-top beach town"),
    D("Kovalam", "Kerala", "west_coast", 8.40, 76.98, 10, True, 3200, (0.3, 0.9, 0.4, 0.6, 0.6),
      "Crescent beaches and Ayurveda retreats", ("thiruvananthapuram", "trivandrum")),
    # --- Western Ghats hills
    D("Munnar", "Kerala", "ghats_hills", 10.09, 77.06, 1600, False, 3500, (0.5, 0.8, 0.2, 0.4, 1.0),
      "Tea estates and misty hills"),
    D("Coorg", "Karnataka", "ghats_hills", 12.42, 75.74, 1150, False, 4000, (0.6, 0.8, 0.3, 0.6, 0.9),
      "Coffee estates, waterfalls and homestays", ("kodagu", "madikeri")),
    D("Ooty", "Tamil Nadu", "ghats_hills", 11.41, 76.70, 2240, False, 3000, (0.3, 0.8, 0.3, 0.4, 0.9),
      "The Nilgiri toy train, lakes and tea gardens", ("udhagamandalam", "coonoor")),
    D("Kodaikanal", "Tamil Nadu", "ghats_hills", 10.24, 77.49, 2130, False, 3000, (0.4, 0.8, 0.2, 0.3, 0.9),
      "A lake town among pine forests"),
    D("Wayanad", "Kerala", "ghats_hills", 11.69, 76.13, 900, False, 3200, (0.7, 0.7, 0.3, 0.4, 1.0),
      "Forests, caves and wildlife"),
    D("Chikmagalur", "Karnataka", "ghats_hills", 13.32, 75.77, 1090, False, 3200, (0.7, 0.7, 0.2, 0.4, 0.9),
      "Coffee hills and treks", ("chikkamagaluru",)),
    D("Mahabaleshwar", "Maharashtra", "ghats_hills", 17.92, 73.66, 1350, False, 3200, (0.3, 0.8, 0.3, 0.5, 0.8),
      "Valley viewpoints and strawberry farms", ("panchgani",)),
    D("Lonavala", "Maharashtra", "ghats_hills", 18.75, 73.41, 620, False, 3000, (0.5, 0.7, 0.3, 0.4, 0.8),
      "Hills, forts and caves near Mumbai and Pune", ("khandala",)),
    # --- Deccan
    D("Hampi", "Karnataka", "deccan", 15.33, 76.46, 467, False, 2000, (0.5, 0.5, 1.0, 0.3, 0.6),
      "Vijayanagara ruins among giant boulders"),
    D("Mysuru", "Karnataka", "deccan", 12.30, 76.64, 770, False, 2800, (0.2, 0.5, 0.9, 0.6, 0.4),
      "The palace, markets and Dasara", ("mysore",)),
    D("Bengaluru", "Karnataka", "deccan", 12.97, 77.59, 920, False, 3500, (0.2, 0.4, 0.5, 0.9, 0.3),
      "Cafes, gardens and food streets", ("bangalore",)),
    D("Hyderabad", "Telangana", "deccan", 17.39, 78.49, 540, False, 3200, (0.2, 0.4, 0.8, 1.0, 0.2),
      "Charminar, Golconda and biryani"),
    D("Aurangabad", "Maharashtra", "deccan", 19.88, 75.34, 570, False, 2800, (0.3, 0.3, 1.0, 0.4, 0.3),
      "Base for the Ajanta and Ellora caves", ("ajanta", "ellora", "chhatrapati sambhajinagar")),
    # --- Tamil Nadu
    D("Puducherry", "Puducherry", "tamil_coast", 11.94, 79.81, 5, True, 3000, (0.3, 0.8, 0.7, 0.8, 0.4),
      "The French quarter, cafes and beaches", ("pondicherry", "pondy", "auroville")),
    D("Mahabalipuram", "Tamil Nadu", "tamil_coast", 12.62, 80.19, 10, True, 2600, (0.3, 0.6, 0.9, 0.5, 0.4),
      "The Shore Temple and rock-cut monuments", ("mamallapuram",)),
    D("Chennai", "Tamil Nadu", "tamil_coast", 13.08, 80.27, 6, True, 3000, (0.1, 0.4, 0.7, 0.9, 0.2),
      "Temples, Marina Beach and filter coffee", ("madras",)),
    D("Madurai", "Tamil Nadu", "tamil_coast", 9.93, 78.12, 135, False, 2500, (0.1, 0.3, 1.0, 0.8, 0.2),
      "The Meenakshi temple and a night-time food scene"),
    D("Rameswaram", "Tamil Nadu", "tamil_coast", 9.29, 79.31, 10, True, 2300, (0.2, 0.5, 0.9, 0.4, 0.5),
      "A pilgrim island and Dhanushkodi's empty shore", ("dhanushkodi",)),
    D("Kanyakumari", "Tamil Nadu", "tamil_coast", 8.08, 77.54, 30, True, 2400, (0.2, 0.6, 0.7, 0.4, 0.6),
      "India's southern tip -- sunrise and sunset over the sea"),
    # --- east
    D("Kolkata", "West Bengal", "east", 22.57, 88.36, 9, False, 3000, (0.1, 0.4, 0.9, 1.0, 0.2),
      "Colonial streets, sweets and culture", ("calcutta",)),
    D("Puri", "Odisha", "east", 19.81, 85.83, 5, True, 2200, (0.2, 0.7, 0.8, 0.5, 0.5),
      "The Jagannath temple, a long beach and Konark nearby", ("konark",)),
    D("Bhubaneswar", "Odisha", "east", 20.30, 85.82, 45, False, 2500, (0.2, 0.4, 0.9, 0.5, 0.3),
      "The temple city"),
    D("Visakhapatnam", "Andhra Pradesh", "east", 17.69, 83.22, 45, True, 2800, (0.4, 0.7, 0.4, 0.6, 0.7),
      "Beaches, with the Araku valley inland", ("vizag", "araku")),
    # --- northern plains
    D("Delhi", "Delhi", "northern_plains", 28.61, 77.21, 216, False, 3500, (0.2, 0.3, 0.9, 1.0, 0.2),
      "Mughal monuments, markets and food", ("new delhi", "old delhi")),
    D("Agra", "Uttar Pradesh", "northern_plains", 27.18, 78.01, 170, False, 3000, (0.1, 0.3, 1.0, 0.6, 0.2),
      "The Taj Mahal, Agra Fort and Fatehpur Sikri", ("fatehpur sikri",)),
    D("Varanasi", "Uttar Pradesh", "northern_plains", 25.32, 83.01, 80, False, 2300, (0.2, 0.4, 1.0, 0.8, 0.3),
      "Ghats, the evening aarti and old lanes", ("banaras", "benares", "kashi", "sarnath")),
    D("Amritsar", "Punjab", "northern_plains", 31.63, 74.87, 234, False, 2600, (0.1, 0.4, 0.9, 1.0, 0.1),
      "The Golden Temple, Wagah and Punjabi food"),
    D("Lucknow", "Uttar Pradesh", "northern_plains", 26.85, 80.95, 123, False, 2800, (0.1, 0.3, 0.8, 1.0, 0.1),
      "Nawabi monuments and kebabs"),
    D("Bodh Gaya", "Bihar", "northern_plains", 24.70, 84.99, 111, False, 2200, (0.1, 0.5, 1.0, 0.3, 0.2),
      "Where the Buddha found enlightenment", ("gaya",)),
    # --- Rajasthan and Gujarat
    D("Jaipur", "Rajasthan", "arid_west", 26.91, 75.79, 430, False, 3200, (0.2, 0.4, 1.0, 0.8, 0.2),
      "Forts, palaces and bazaars of the Pink City", ("amer", "amber")),
    D("Udaipur", "Rajasthan", "arid_west", 24.59, 73.71, 600, False, 3800, (0.2, 0.8, 0.9, 0.6, 0.5),
      "Lakes, palaces and rooftop sunsets"),
    D("Jodhpur", "Rajasthan", "arid_west", 26.24, 73.02, 230, False, 3000, (0.3, 0.4, 0.9, 0.7, 0.2),
      "Mehrangarh fort above the Blue City"),
    D("Jaisalmer", "Rajasthan", "arid_west", 26.92, 70.91, 225, False, 3200, (0.6, 0.5, 0.9, 0.5, 0.6),
      "A golden sandstone fort and desert camps", ("sam sand dunes",)),
    D("Pushkar", "Rajasthan", "arid_west", 26.49, 74.55, 510, False, 2000, (0.3, 0.6, 0.8, 0.5, 0.3),
      "A small lake town of ghats and temples", ("ajmer",)),
    D("Ranthambore", "Rajasthan", "arid_west", 26.02, 76.50, 260, False, 5500, (0.6, 0.5, 0.3, 0.3, 1.0),
      "Tiger safaris among old fort ruins", ("sawai madhopur",), closed_months=(7, 8, 9)),
    D("Rann of Kutch", "Gujarat", "arid_west", 23.73, 69.86, 15, False, 3500, (0.5, 0.5, 0.7, 0.4, 0.8),
      "The white salt desert and craft villages", ("kutch", "bhuj", "dhordo")),
    D("Ahmedabad", "Gujarat", "arid_west", 23.02, 72.57, 53, False, 2600, (0.1, 0.3, 0.8, 0.9, 0.1),
      "Old pols, stepwells and street food"),
    D("Gir", "Gujarat", "arid_west", 21.12, 70.82, 200, False, 4000, (0.5, 0.5, 0.2, 0.3, 1.0),
      "The last home of the Asiatic lion", ("sasan gir", "somnath"), closed_months=(7, 8, 9)),
    # --- central India
    D("Khajuraho", "Madhya Pradesh", "central", 24.85, 79.93, 283, False, 2600, (0.1, 0.4, 1.0, 0.3, 0.3),
      "Carved Chandela temples", ("orchha",)),
    D("Bandhavgarh", "Madhya Pradesh", "central", 23.70, 81.03, 440, False, 6000, (0.7, 0.5, 0.2, 0.3, 1.0),
      "Dense tiger country", closed_months=(7, 8, 9)),
    D("Kanha", "Madhya Pradesh", "central", 22.33, 80.61, 600, False, 6000, (0.7, 0.5, 0.2, 0.3, 1.0),
      "Sal forests and meadows -- tigers and barasingha", closed_months=(7, 8, 9)),
    D("Pachmarhi", "Madhya Pradesh", "central", 22.47, 78.43, 1067, False, 2800, (0.6, 0.7, 0.3, 0.3, 0.9),
      "Central India's hill station -- waterfalls and caves"),
    # --- Himalayan foothills
    D("Rishikesh", "Uttarakhand", "himalaya_foothills", 30.09, 78.27, 372, False, 2200, (0.9, 0.7, 0.7, 0.4, 0.8),
      "Rafting, yoga and the Ganga"),
    D("Haridwar", "Uttarakhand", "himalaya_foothills", 29.95, 78.16, 314, False, 2000, (0.1, 0.5, 0.9, 0.5, 0.4),
      "Har Ki Pauri's evening aarti"),
    D("Jim Corbett", "Uttarakhand", "himalaya_foothills", 29.53, 78.77, 400, False, 4500, (0.6, 0.6, 0.1, 0.3, 1.0),
      "India's oldest national park", ("corbett", "ramnagar"), closed_months=(7, 8, 9)),
    # --- Himalayan hill stations
    D("Shimla", "Himachal Pradesh", "himalaya_hills", 31.10, 77.17, 2200, False, 3300, (0.3, 0.7, 0.5, 0.4, 0.8),
      "The Mall Road, the toy train and pine ridges", ("kufri",)),
    D("Manali", "Himachal Pradesh", "himalaya_hills", 32.24, 77.19, 2050, False, 3200, (0.9, 0.6, 0.3, 0.4, 1.0),
      "Adventure sports, orchards and mountain views", ("solang", "kullu")),
    D("Dharamshala", "Himachal Pradesh", "himalaya_hills", 32.24, 76.32, 1800, False, 2400, (0.7, 0.7, 0.7, 0.5, 0.9),
      "McLeod Ganj, Tibetan culture and the Triund trek", ("mcleod ganj", "mcleodganj", "bir")),
    D("Mussoorie", "Uttarakhand", "himalaya_hills", 30.46, 78.07, 2005, False, 3200, (0.3, 0.8, 0.3, 0.4, 0.8),
      "Ridge walks above the Doon valley", ("dehradun",)),
    D("Nainital", "Uttarakhand", "himalaya_hills", 29.39, 79.45, 2084, False, 3000, (0.3, 0.8, 0.3, 0.4, 0.8),
      "A lake ringed by hills", ("bhimtal",)),
    D("Darjeeling", "West Bengal", "himalaya_hills", 27.04, 88.26, 2045, False, 3000, (0.4, 0.7, 0.6, 0.5, 0.9),
      "Tea gardens, the toy train and Kanchenjunga views"),
    D("Gangtok", "Sikkim", "himalaya_hills", 27.33, 88.61, 1650, False, 3300, (0.6, 0.7, 0.6, 0.5, 0.9),
      "Monasteries and day trips to high lakes", ("tsomgo",)),
    D("Srinagar", "Jammu and Kashmir", "himalaya_hills", 34.08, 74.80, 1585, False, 3800, (0.4, 0.9, 0.7, 0.7, 0.9),
      "Dal Lake houseboats and Mughal gardens", ("kashmir", "gulmarg", "pahalgam")),
    D("Tawang", "Arunachal Pradesh", "himalaya_hills", 27.59, 91.87, 3048, False, 3500, (0.8, 0.5, 0.8, 0.3, 1.0),
      "A great monastery high in the eastern Himalaya"),
    # --- high Himalaya
    D("Leh", "Ladakh", "himalaya_high", 34.15, 77.58, 3500, False, 4500, (1.0, 0.5, 0.6, 0.3, 1.0),
      "High passes, monasteries and Pangong", ("ladakh", "nubra", "pangong")),
    D("Spiti", "Himachal Pradesh", "himalaya_high", 32.23, 78.07, 3800, False, 3500, (1.0, 0.4, 0.6, 0.2, 1.0),
      "A cold desert valley of cliff-top monasteries", ("kaza",)),
    # --- Northeast
    D("Shillong", "Meghalaya", "northeast", 25.58, 91.89, 1525, False, 3000, (0.6, 0.7, 0.5, 0.5, 0.9),
      "Pine hills, waterfalls and a music scene"),
    D("Cherrapunji", "Meghalaya", "northeast", 25.27, 91.73, 1430, False, 2800, (0.8, 0.6, 0.3, 0.3, 1.0),
      "Living root bridges and waterfalls", ("sohra", "mawlynnong")),
    D("Kaziranga", "Assam", "northeast", 26.58, 93.17, 70, False, 4500, (0.6, 0.5, 0.2, 0.3, 1.0),
      "One-horned rhinos on the Brahmaputra floodplain", closed_months=(5, 6, 7, 8, 9, 10)),
    # --- Andaman Islands
    D("Port Blair", "Andaman and Nicobar Islands", "islands", 11.62, 92.73, 16, True, 5000, (0.5, 0.8, 0.6, 0.5, 0.8),
      "The Cellular Jail and nearby islands", ("andaman", "andamans")),
    D("Havelock", "Andaman and Nicobar Islands", "islands", 11.97, 92.99, 5, True, 6000, (0.8, 1.0, 0.1, 0.5, 1.0),
      "Radhanagar beach, snorkelling and diving", ("swaraj dweep", "neil island")),
)
