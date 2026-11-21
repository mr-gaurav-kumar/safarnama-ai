"""Freely licensed photos for the starter packages, from Wikimedia Commons.

Each entry keeps the author and licence so the credit line on the package is
correct (CC BY / CC BY-SA require attribution). Images load straight from
Wikimedia via Special:FilePath, which always resolves to a resized copy.
"""
from urllib.parse import quote

# title -> [(commons file name, author, licence)], cover first
PHOTOS: dict[str, list[tuple[str, str, str]]] = {
    "Manali Snow & Solang Escape": [
        ("Snow Rohtang Range Manali May24 A7CR 00128.jpg", "Timothy A. Gonsalves", "CC BY-SA 4.0"),
        ("A view of solang valley on the way to rohtang pass.jpg", "Shubhanshu at English Wikipedia", "Public domain"),
        ("Kullu Valley, Vashisht, Manali, Apples, India.jpg", "Vyacheslav Argenberg", "CC BY 4.0"),
    ],
    "Goa Beaches & Old Goa Heritage": [
        ("Anjuna Beach, Goa, India, Legendary Curlies beach shack.jpg", "Vyacheslav Argenberg", "CC BY 4.0"),
        ("Front Elevation of Basilica of Bom Jesus.jpg", "iMahesh", "CC BY-SA 4.0"),
        ("Mandrem Beach and Mandrem River, Mandrem, Goa, India.jpg", "Vyacheslav Argenberg", "CC BY 4.0"),
    ],
    "Tawang Monastery & Sela Pass Expedition": [
        ("The majestic Tawang Monastery.jpg", "Chandrasen31", "CC BY-SA 4.0"),
        ("Sela Pass, Arunachal Pradesh.jpg", "Dhurba Jyoti Baruah (Zaan)", "CC BY-SA 4.0"),
        ("Main temple (Dukhang) of Tawang monastery with Buddha image in a lotus position.jpg", "Rohit Sharma", "CC BY-SA 4.0"),
    ],
    "Bodh Gaya, Rajgir & Nalanda Buddhist Trail": [
        ("Mahabodhi temple complex, Bodhgaya 23.jpg", "Rohit Sharma", "CC BY-SA 4.0"),
        ("Monastery 5 - Nalanda Mahavihara (1).jpg", "Sumitsurai", "CC BY-SA 4.0"),
        ("Mahabodhi Temple DSCN8010 1.jpg", "Sumita Roy Dutta", "CC BY-SA 4.0"),
    ],
    "Royal Rajasthan: Jaipur, Jodhpur & Udaipur": [
        ("Amber Fort, Jaipur, 20191219 1011 9509.jpg", "Jakub Hałun", "CC BY-SA 4.0"),
        ("20191207 Lake Pichola, City Palace, Udaipur, 1516 7254.jpg", "Jakub Hałun", "CC BY-SA 4.0"),
        ("20191218 Amber Fort seen from Jaigarh Fort 1617 9427.jpg", "Jakub Hałun", "CC BY-SA 4.0"),
    ],
    "Kerala: Munnar Tea Hills & Alleppey Houseboat": [
        ("Alleppey Boat houses.jpg", "Mohanrangaphotography", "CC BY-SA 4.0"),
        ("Munnar - Tea Plantations.jpg", "Ingo Mehling", "CC BY-SA 4.0"),
        ("Houseboat on Alleppey backwaters (Kerala, India 2023) (52703799587).jpg", "Paul Arps", "CC BY 2.0"),
    ],
}

CREDIT_MARK = "Photos via Wikimedia Commons:"


def url(file_name: str, width: int = 1600) -> str:
    return (
        "https://commons.wikimedia.org/wiki/Special:FilePath/"
        + quote(file_name.replace(" ", "_"))
        + f"?width={width}"
    )


def images_for(title: str) -> list[str]:
    return [url(f) for f, _, _ in PHOTOS.get(title, [])]


def credit_line(title: str) -> str:
    people = []
    for _, author, lic in PHOTOS.get(title, []):
        entry = f"{author} ({lic})"
        if entry not in people:
            people.append(entry)
    return f"{CREDIT_MARK} " + "; ".join(people) + "." if people else ""
