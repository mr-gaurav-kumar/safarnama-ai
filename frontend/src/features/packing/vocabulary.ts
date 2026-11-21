import type { Category } from '@/features/packing/api'

/**
 * Things people pack for trips in India, with the category each belongs in.
 * Used for suggestions as you type ("Towe" -> Towel) and to fill in the
 * category for you when you pick one.
 */
export const PACKING_ITEMS: [string, Category][] = [
  // documents
  ['Aadhaar card', 'documents'], ['PAN card', 'documents'], ['Passport', 'documents'], ['Visa', 'documents'],
  ['Driving licence', 'documents'], ['Voter ID', 'documents'], ['Tickets', 'documents'], ['Hotel booking', 'documents'],
  ['Travel insurance', 'documents'], ['Passport-size photos', 'documents'], ['Cash', 'documents'],
  ['Debit card', 'documents'], ['Credit card', 'documents'], ['Permit (Inner Line)', 'documents'],
  ['Student ID', 'documents'], ['Emergency contacts list', 'documents'],
  // clothes
  ['T-shirts', 'clothes'], ['Half-sleeve shirts', 'clothes'], ['Full-sleeve shirts', 'clothes'], ['Jeans', 'clothes'],
  ['Trousers', 'clothes'], ['Shorts', 'clothes'], ['Track pants', 'clothes'], ['Kurta', 'clothes'],
  ['Saree', 'clothes'], ['Dress', 'clothes'], ['Innerwear', 'clothes'], ['Socks', 'clothes'],
  ['Woollen socks', 'clothes'], ['Thermal innerwear', 'clothes'], ['Sweater', 'clothes'], ['Hoodie', 'clothes'],
  ['Jacket', 'clothes'], ['Down jacket', 'clothes'], ['Fleece jacket', 'clothes'], ['Raincoat', 'clothes'],
  ['Rain jacket', 'clothes'], ['Windcheater', 'clothes'], ['Nightwear', 'clothes'], ['Swimwear', 'clothes'],
  ['Scarf', 'clothes'], ['Shawl', 'clothes'], ['Gloves', 'clothes'], ['Woollen cap', 'clothes'],
  ['Muffler', 'clothes'], ['Formal wear', 'clothes'],
  // footwear
  ['Sneakers', 'footwear'], ['Comfortable shoes', 'footwear'], ['Walking shoes', 'footwear'],
  ['Trekking shoes', 'footwear'], ['Hiking boots', 'footwear'], ['Snow boots', 'footwear'],
  ['Waterproof shoes', 'footwear'], ['Sandals', 'footwear'], ['Floaters', 'footwear'], ['Flip-flops', 'footwear'],
  ['Slippers', 'footwear'], ['Formal shoes', 'footwear'],
  // toiletries
  ['Towel', 'toiletries'], ['Quick-dry towel', 'toiletries'], ['Toothbrush', 'toiletries'], ['Toothpaste', 'toiletries'],
  ['Soap', 'toiletries'], ['Body wash', 'toiletries'], ['Shampoo', 'toiletries'], ['Conditioner', 'toiletries'],
  ['Face wash', 'toiletries'], ['Moisturiser', 'toiletries'], ['Cold cream', 'toiletries'], ['Lip balm', 'toiletries'],
  ['Sunscreen', 'toiletries'], ['Deodorant', 'toiletries'], ['Perfume', 'toiletries'], ['Comb', 'toiletries'],
  ['Hairbrush', 'toiletries'], ['Hair oil', 'toiletries'], ['Razor', 'toiletries'], ['Shaving cream', 'toiletries'],
  ['Trimmer', 'toiletries'], ['Wet wipes', 'toiletries'], ['Tissues', 'toiletries'], ['Hand sanitiser', 'toiletries'],
  ['Sanitary pads', 'toiletries'], ['Menstrual cup', 'toiletries'], ['Toilet paper', 'toiletries'],
  ['Laundry bag', 'toiletries'], ['Detergent sachets', 'toiletries'],
  // health
  ['Medicines', 'health'], ['First-aid kit', 'health'], ['Paracetamol', 'health'], ['ORS sachets', 'health'],
  ['Band-aids', 'health'], ['Antiseptic cream', 'health'], ['Motion sickness tablets', 'health'],
  ['Altitude sickness tablets', 'health'], ['Mosquito repellent', 'health'], ['Prescription medicines', 'health'],
  ['Pain relief spray', 'health'], ['Masks', 'health'], ['Glucose powder', 'health'], ['Eye drops', 'health'],
  ['Spectacles', 'health'], ['Contact lenses', 'health'],
  // electronics
  ['Phone charger', 'electronics'], ['Power bank', 'electronics'], ['Earphones', 'electronics'],
  ['Headphones', 'electronics'], ['Laptop', 'electronics'], ['Laptop charger', 'electronics'], ['Camera', 'electronics'],
  ['Camera charger', 'electronics'], ['Extra batteries', 'electronics'], ['Memory card', 'electronics'],
  ['Travel adapter', 'electronics'], ['Extension cord', 'electronics'], ['Torch', 'electronics'],
  ['Headlamp', 'electronics'], ['Smartwatch', 'electronics'], ['Tripod', 'electronics'], ['GoPro', 'electronics'],
  ['Kindle', 'electronics'], ['Bluetooth speaker', 'electronics'], ['USB cable', 'electronics'],
  // accessories
  ['Sunglasses', 'accessories'], ['Cap', 'accessories'], ['Hat', 'accessories'], ['Umbrella', 'accessories'],
  ['Water bottle', 'accessories'], ['Backpack', 'accessories'], ['Day bag', 'accessories'], ['Duffel bag', 'accessories'],
  ['Wallet', 'accessories'], ['Watch', 'accessories'], ['Neck pillow', 'accessories'], ['Eye mask', 'accessories'],
  ['Earplugs', 'accessories'], ['Lock and key', 'accessories'], ['Ziplock bags', 'accessories'],
  ['Trekking pole', 'accessories'], ['Snacks', 'accessories'], ['Dry fruits', 'accessories'], ['Thermos flask', 'accessories'],
  ['Book', 'accessories'], ['Notebook and pen', 'accessories'], ['Playing cards', 'accessories'],
  ['Sleeping bag', 'accessories'], ['Tent', 'accessories'], ['Rope', 'accessories'], ['Swiss knife', 'accessories'],
  ['Plastic bags', 'accessories'], ['Hand fan', 'accessories'],
]

/** Common things to write in a day plan, besides "Visit <sight>". */
export const ACTIVITIES: string[] = [
  'Check in at the hotel', 'Check out', 'Breakfast', 'Lunch', 'Dinner', 'Street food walk', 'Local market shopping',
  'Sightseeing', 'City walk', 'Heritage walk', 'Temple visit', 'Boat ride', 'Sunrise view', 'Sunset view',
  'Trek', 'River rafting', 'Paragliding', 'Camping', 'Bonfire', 'Jungle safari', 'Cafe hopping', 'Rest at the hotel',
  'Travel by train', 'Travel by bus', 'Travel by flight', 'Travel by cab', 'Reach the destination', 'Leave for home',
  'Photography', 'Spa and massage', 'Beach time', 'Snorkelling', 'Scuba diving', 'Cable car ride', 'Toy train ride',
  'Night market', 'Light and sound show', 'Museum visit', 'Fort visit', 'Lake walk', 'Waterfall visit',
]
