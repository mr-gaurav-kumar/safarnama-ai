"""Starter packages published by the platform (admin). Loaded with
`python -m app.cli seed-packages`; running it again skips titles that exist,
so edits made in the admin panel are never overwritten.

Prices are indicative per-person rates (twin sharing) for planning; the admin
edits them in the panel.
"""

PACKAGES: list[dict] = [
    {
        "title": "Manali Snow & Solang Escape",
        "destination": "Manali, Himachal Pradesh",
        "duration_days": 5,
        "price_per_person": 18999,
        "summary": "Pine forests, Old Manali cafés, Solang Valley and a day across the Atal Tunnel to Sissu.",
        "description": (
            "A relaxed five-day loop from Delhi into the Kullu valley. Days are paced for first-time mountain "
            "travellers: one active day at Solang Valley (paragliding and ropeway, weather permitting), one day "
            "through the Atal Tunnel into Lahaul, and unhurried time in Old Manali and Naggar.\n\n"
            "Best from October to June. In peak snow months (December–February) the Lahaul day depends on road "
            "conditions and is swapped for Kullu and Naggar if the tunnel road is closed. Rohtang Pass needs a "
            "separate government permit and is not included."
        ),
        "inclusions": [
            "Overnight Volvo from Delhi and back",
            "4 nights hotel stay (twin sharing)",
            "Daily breakfast and dinner",
            "Private cab for all local sightseeing",
            "Solang Valley and Atal Tunnel–Sissu day trip",
            "Driver allowance, tolls and parking",
        ],
        "highlights": [
            "Day 1: Arrive Manali by morning, check in, Mall Road and Hadimba Devi Temple in the evening",
            "Day 2: Solang Valley — ropeway, snow play or paragliding (at your own cost)",
            "Day 3: Through the Atal Tunnel to Sissu waterfall and Lahaul valley viewpoints",
            "Day 4: Old Manali cafés, Vashisht hot springs, afternoon at Naggar Castle",
            "Day 5: Check out, local market, overnight Volvo back to Delhi",
        ],
        "style_tags": ["adventure", "nature"],
        "seats": 30,
    },
    {
        "title": "Goa Beaches & Old Goa Heritage",
        "destination": "North & South Goa",
        "duration_days": 4,
        "price_per_person": 16499,
        "summary": "Sunset forts, beach shacks, Portuguese churches and a slow day in quieter South Goa.",
        "description": (
            "Four days that split Goa in two: the lively north with Fort Aguada, Baga and Anjuna, and the calmer "
            "south with Colva and Palolem. One morning goes to Old Goa's UNESCO-listed churches and the Latin "
            "quarter of Fontainhas in Panaji.\n\n"
            "Great from November to February. In the monsoon (June–September) beaches are rough but the "
            "countryside is green, and a Dudhsagar Falls trip can be added on request."
        ),
        "inclusions": [
            "3 nights beach-side resort (twin sharing)",
            "Daily breakfast",
            "Airport / railway station pick-up and drop",
            "North Goa and South Goa sightseeing by private cab",
            "Mandovi river sunset cruise",
        ],
        "highlights": [
            "Day 1: Arrive, check in near Candolim, sunset at Fort Aguada",
            "Day 2: North Goa — Calangute, Baga, Anjuna flea market (Wednesdays), Chapora Fort",
            "Day 3: Old Goa — Basilica of Bom Jesus, Se Cathedral; Fontainhas walk; evening river cruise",
            "Day 4: South Goa — Colva and Palolem beaches, then departure",
        ],
        "style_tags": ["relax", "food", "nightlife"],
        "seats": 40,
    },
    {
        "title": "Tawang Monastery & Sela Pass Expedition",
        "destination": "Tawang, Arunachal Pradesh",
        "duration_days": 7,
        "price_per_person": 32999,
        "summary": "Over the 13,700 ft Sela Pass to Tawang — India's largest monastery, high-altitude lakes and Dirang.",
        "description": (
            "A seven-day road journey from Guwahati into western Arunachal Pradesh. The route climbs gradually "
            "through Bhalukpong and Dirang before crossing Sela Pass, which helps with acclimatisation. In Tawang "
            "you visit the 17th-century Tawang Monastery, the War Memorial and the high-altitude lakes.\n\n"
            "Indian citizens need an Inner Line Permit (ILP) for Arunachal Pradesh — we apply for it with your ID. "
            "Bum La Pass needs an additional army permit, issued on the spot subject to conditions, and is optional. "
            "Best from October to April; roads can close briefly after heavy snow at Sela."
        ),
        "inclusions": [
            "Inner Line Permit processing",
            "6 nights hotels and homestays (twin sharing)",
            "Daily breakfast and dinner",
            "Dedicated SUV with an experienced mountain driver",
            "Guwahati pick-up and drop",
        ],
        "highlights": [
            "Day 1: Guwahati to Bhalukpong along the Kameng river",
            "Day 2: Bhalukpong to Dirang via Bomdila monastery",
            "Day 3: Dirang — hot springs, Dirang Dzong, sheep-breeding farm",
            "Day 4: Cross Sela Pass (13,700 ft) and Sela Lake into Tawang",
            "Day 5: Tawang Monastery, War Memorial, Urgelling Gompa",
            "Day 6: Shungatser (Madhuri) Lake; Bum La Pass if permits allow",
            "Day 7: Drive back towards Guwahati (overnight stop at Bhalukpong or Tezpur on request)",
        ],
        "style_tags": ["adventure", "culture", "nature"],
        "seats": 16,
    },
    {
        "title": "Bodh Gaya, Rajgir & Nalanda Buddhist Trail",
        "destination": "Bodh Gaya, Bihar",
        "duration_days": 4,
        "price_per_person": 14999,
        "summary": "Where the Buddha attained enlightenment — the Mahabodhi Temple, Rajgir's Vulture Peak and ancient Nalanda.",
        "description": (
            "A calm, meaningful four-day trail through the heart of Buddhist India. Start at the Mahabodhi Temple "
            "in Bodh Gaya — a UNESCO World Heritage Site built around the Bodhi Tree — and the international "
            "monasteries around it. Then Rajgir, where the Buddha taught at Griddhakuta (Vulture Peak), and the "
            "ruins of Nalanda Mahavihara, one of the world's oldest universities and also a UNESCO site.\n\n"
            "Best from October to March. Gaya has the nearest airport; Gaya Junction is well connected by train."
        ),
        "inclusions": [
            "3 nights hotel stay near the Mahabodhi Temple (twin sharing)",
            "Daily breakfast",
            "Gaya airport / station pick-up and drop",
            "Private cab for Bodh Gaya, Rajgir and Nalanda",
            "Rajgir Vishwa Shanti Stupa ropeway tickets",
            "Local guide at Nalanda",
        ],
        "highlights": [
            "Day 1: Arrive Gaya, evening at the Mahabodhi Temple and Bodhi Tree",
            "Day 2: Great Buddha Statue, Thai, Japanese and Bhutanese monasteries, Sujata Stupa",
            "Day 3: Rajgir — Griddhakuta (Vulture Peak), Vishwa Shanti Stupa; Nalanda ruins and museum",
            "Day 4: Morning meditation at Bodh Gaya, then departure",
        ],
        "style_tags": ["culture", "spiritual"],
        "seats": 30,
    },
    {
        "title": "Royal Rajasthan: Jaipur, Jodhpur & Udaipur",
        "destination": "Jaipur, Jodhpur, Udaipur",
        "duration_days": 7,
        "price_per_person": 34999,
        "summary": "Three royal cities — the Pink City's forts, the blue lanes under Mehrangarh, and Udaipur's lakes.",
        "description": (
            "A classic week in Rajasthan at a comfortable pace, with two nights in each of the three great "
            "cities and a scenic drive via the Ranakpur Jain temple. Stays are heritage-style hotels where "
            "possible.\n\nBest from October to March."
        ),
        "inclusions": [
            "6 nights heritage-style hotels (twin sharing)",
            "Daily breakfast",
            "AC car with driver for the whole trip",
            "Evening boat ride on Lake Pichola",
            "Local guides in Jaipur and Udaipur",
        ],
        "highlights": [
            "Day 1: Arrive Jaipur, Hawa Mahal and City Palace",
            "Day 2: Amber Fort in the morning, Jantar Mantar, sunset at Nahargarh",
            "Day 3: Drive to Jodhpur, evening in the old blue city",
            "Day 4: Mehrangarh Fort and Jaswant Thada",
            "Day 5: Drive to Udaipur via the Ranakpur Jain temple",
            "Day 6: City Palace, Saheliyon-ki-Bari, boat ride on Lake Pichola",
            "Day 7: Departure from Udaipur",
        ],
        "style_tags": ["culture", "food"],
        "seats": 24,
    },
    {
        "title": "Kerala: Munnar Tea Hills & Alleppey Houseboat",
        "destination": "Kochi, Munnar, Alleppey",
        "duration_days": 6,
        "price_per_person": 27999,
        "summary": "Fort Kochi, misty tea estates in Munnar, and a night on a private houseboat in the backwaters.",
        "description": (
            "Six days from the spice port of Kochi up into the Munnar hills and down to the Alleppey backwaters, "
            "ending with an overnight stay on a private houseboat with meals cooked on board.\n\n"
            "Lovely from September to March; the monsoon (June–August) is lush and quiet with lower prices."
        ),
        "inclusions": [
            "4 nights hotels + 1 night private houseboat (twin sharing)",
            "Daily breakfast; all meals on the houseboat",
            "AC car with driver throughout",
            "Kathakali performance tickets in Kochi",
            "Tea museum entry in Munnar",
        ],
        "highlights": [
            "Day 1: Arrive Kochi — Chinese fishing nets, Fort Kochi walk, Kathakali show",
            "Day 2: Drive to Munnar via Cheeyappara waterfalls",
            "Day 3: Munnar — Eravikulam National Park, tea museum, Mattupetty Dam",
            "Day 4: Drive to Thekkady — spice plantation walk",
            "Day 5: Board the houseboat in Alleppey, cruise the backwaters overnight",
            "Day 6: Disembark and transfer to Kochi for departure",
        ],
        "style_tags": ["relax", "nature", "food"],
        "seats": 20,
    },
]
