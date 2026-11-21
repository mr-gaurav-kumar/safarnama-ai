/**
 * Airports the flight search knows by name, plus the nearest airport for
 * popular destinations that have none of their own (Manali -> Bhuntar KUU).
 *
 * To add one: append a row. `aliases` are other names a trip's destination
 * might use; matching is case-insensitive on the city part ("Manali, HP").
 */
export interface Airport {
  code: string
  city: string
  name: string
  country?: string // unset = India
  aliases?: string[]
}

export const AIRPORTS: Airport[] = [
  // ---- metros ----
  { code: 'DEL', city: 'Delhi', name: 'Indira Gandhi International', aliases: ['New Delhi', 'Noida', 'Ghaziabad', 'Gurugram', 'Gurgaon', 'Faridabad', 'Mathura', 'Vrindavan'] },
  { code: 'BOM', city: 'Mumbai', name: 'Chhatrapati Shivaji Maharaj International', aliases: ['Bombay', 'Thane'] },
  { code: 'NMI', city: 'Navi Mumbai', name: 'Navi Mumbai International' },
  { code: 'BLR', city: 'Bengaluru', name: 'Kempegowda International', aliases: ['Bangalore', 'Nandi Hills'] },
  { code: 'MAA', city: 'Chennai', name: 'Chennai International', aliases: ['Madras', 'Pondicherry', 'Puducherry', 'Mahabalipuram', 'Mamallapuram'] },
  { code: 'CCU', city: 'Kolkata', name: 'Netaji Subhas Chandra Bose International', aliases: ['Calcutta', 'Sundarbans'] },
  { code: 'HYD', city: 'Hyderabad', name: 'Rajiv Gandhi International', aliases: ['Secunderabad'] },
  // ---- north ----
  { code: 'IXC', city: 'Chandigarh', name: 'Chandigarh International', aliases: ['Mohali', 'Panchkula', 'Shimla', 'Kasauli'] },
  { code: 'KUU', city: 'Kullu', name: 'Kullu–Manali (Bhuntar)', aliases: ['Manali', 'Kasol', 'Spiti', 'Bhuntar', 'Tosh', 'Jibhi'] },
  { code: 'DHM', city: 'Dharamshala', name: 'Kangra (Gaggal)', aliases: ['McLeod Ganj', 'Mcleodganj', 'Bir', 'Bir Billing', 'Kangra', 'Dalhousie'] },
  { code: 'DED', city: 'Dehradun', name: 'Jolly Grant', aliases: ['Rishikesh', 'Haridwar', 'Mussoorie', 'Auli', 'Kedarnath', 'Badrinath', 'Chopta'] },
  { code: 'PGH', city: 'Pantnagar', name: 'Pantnagar', aliases: ['Nainital', 'Jim Corbett', 'Corbett', 'Ranikhet', 'Almora', 'Mukteshwar'] },
  { code: 'SXR', city: 'Srinagar', name: 'Sheikh ul-Alam International', aliases: ['Gulmarg', 'Pahalgam', 'Sonmarg', 'Kashmir'] },
  { code: 'IXJ', city: 'Jammu', name: 'Jammu', aliases: ['Katra', 'Vaishno Devi', 'Patnitop'] },
  { code: 'IXL', city: 'Leh', name: 'Kushok Bakula Rimpochee', aliases: ['Ladakh', 'Nubra', 'Pangong'] },
  { code: 'ATQ', city: 'Amritsar', name: 'Sri Guru Ram Dass Jee International' },
  { code: 'JAI', city: 'Jaipur', name: 'Jaipur International', aliases: ['Pushkar', 'Ajmer', 'Ranthambore', 'Sawai Madhopur'] },
  { code: 'UDR', city: 'Udaipur', name: 'Maharana Pratap', aliases: ['Mount Abu', 'Kumbhalgarh', 'Chittorgarh'] },
  { code: 'JDH', city: 'Jodhpur', name: 'Jodhpur' },
  { code: 'JSA', city: 'Jaisalmer', name: 'Jaisalmer' },
  { code: 'LKO', city: 'Lucknow', name: 'Chaudhary Charan Singh International' },
  { code: 'VNS', city: 'Varanasi', name: 'Lal Bahadur Shastri International', aliases: ['Benares', 'Banaras', 'Kashi', 'Sarnath'] },
  { code: 'AYJ', city: 'Ayodhya', name: 'Maharishi Valmiki International' },
  { code: 'IXD', city: 'Prayagraj', name: 'Prayagraj', aliases: ['Allahabad'] },
  { code: 'GOP', city: 'Gorakhpur', name: 'Gorakhpur' },
  { code: 'KNU', city: 'Kanpur', name: 'Kanpur' },
  { code: 'AGR', city: 'Agra', name: 'Agra (Kheria)' },
  { code: 'GWL', city: 'Gwalior', name: 'Rajmata Vijaya Raje Scindia' },
  // ---- west ----
  { code: 'GOI', city: 'Goa', name: 'Goa (Dabolim)', aliases: ['Panaji', 'Panjim', 'Vasco', 'Margao', 'Palolem', 'Gokarna', 'South Goa'] },
  { code: 'GOX', city: 'North Goa', name: 'Manohar International (Mopa)', aliases: ['Mopa', 'Calangute', 'Baga', 'Anjuna', 'Arambol'] },
  { code: 'PNQ', city: 'Pune', name: 'Pune', aliases: ['Lonavala', 'Mahabaleshwar', 'Panchgani', 'Khandala'] },
  { code: 'AMD', city: 'Ahmedabad', name: 'Sardar Vallabhbhai Patel International', aliases: ['Gandhinagar', 'Statue of Unity', 'Kevadia'] },
  { code: 'BDQ', city: 'Vadodara', name: 'Vadodara', aliases: ['Baroda'] },
  { code: 'STV', city: 'Surat', name: 'Surat' },
  { code: 'BHJ', city: 'Bhuj', name: 'Bhuj', aliases: ['Rann of Kutch', 'Kutch', 'Dholavira'] },
  { code: 'IXU', city: 'Chhatrapati Sambhajinagar', name: 'Aurangabad', aliases: ['Aurangabad', 'Ajanta', 'Ellora'] },
  { code: 'SAG', city: 'Shirdi', name: 'Shirdi' },
  { code: 'NAG', city: 'Nagpur', name: 'Dr. Babasaheb Ambedkar International', aliases: ['Tadoba', 'Pench'] },
  { code: 'KLH', city: 'Kolhapur', name: 'Kolhapur' },
  // ---- central ----
  { code: 'IDR', city: 'Indore', name: 'Devi Ahilya Bai Holkar', aliases: ['Ujjain', 'Mandu', 'Omkareshwar', 'Maheshwar'] },
  { code: 'BHO', city: 'Bhopal', name: 'Raja Bhoj', aliases: ['Sanchi', 'Bhimbetka', 'Pachmarhi'] },
  { code: 'JLR', city: 'Jabalpur', name: 'Jabalpur', aliases: ['Bhedaghat', 'Kanha', 'Bandhavgarh'] },
  { code: 'HJR', city: 'Khajuraho', name: 'Khajuraho', aliases: ['Panna', 'Orchha'] },
  { code: 'RPR', city: 'Raipur', name: 'Swami Vivekananda' },
  // ---- south ----
  { code: 'COK', city: 'Kochi', name: 'Cochin International', aliases: ['Cochin', 'Ernakulam', 'Munnar', 'Alleppey', 'Alappuzha', 'Kumarakom', 'Thekkady', 'Fort Kochi'] },
  { code: 'TRV', city: 'Thiruvananthapuram', name: 'Trivandrum International', aliases: ['Trivandrum', 'Kovalam', 'Varkala', 'Kanyakumari'] },
  { code: 'CCJ', city: 'Kozhikode', name: 'Calicut International', aliases: ['Calicut', 'Wayanad'] },
  { code: 'CNN', city: 'Kannur', name: 'Kannur International' },
  { code: 'IXE', city: 'Mangaluru', name: 'Mangalore International', aliases: ['Mangalore', 'Udupi', 'Coorg', 'Kodagu', 'Madikeri', 'Chikmagalur', 'Murudeshwar'] },
  { code: 'MYQ', city: 'Mysuru', name: 'Mysore', aliases: ['Mysore'] },
  { code: 'HBX', city: 'Hubballi', name: 'Hubli', aliases: ['Hubli', 'Hampi', 'Dharwad'] },
  { code: 'IXG', city: 'Belagavi', name: 'Belgaum', aliases: ['Belgaum'] },
  { code: 'CJB', city: 'Coimbatore', name: 'Coimbatore International', aliases: ['Ooty', 'Udhagamandalam', 'Coonoor', 'Valparai'] },
  { code: 'IXM', city: 'Madurai', name: 'Madurai', aliases: ['Kodaikanal', 'Rameswaram'] },
  { code: 'TRZ', city: 'Tiruchirappalli', name: 'Tiruchirappalli International', aliases: ['Trichy', 'Thanjavur', 'Tanjore'] },
  { code: 'TIR', city: 'Tirupati', name: 'Tirupati', aliases: ['Tirumala'] },
  { code: 'VTZ', city: 'Visakhapatnam', name: 'Visakhapatnam', aliases: ['Vizag', 'Araku', 'Araku Valley'] },
  { code: 'VGA', city: 'Vijayawada', name: 'Vijayawada', aliases: ['Amaravati'] },
  { code: 'RJA', city: 'Rajahmundry', name: 'Rajahmundry', aliases: ['Rajamahendravaram'] },
  { code: 'IXZ', city: 'Port Blair', name: 'Veer Savarkar International', aliases: ['Andaman', 'Havelock', 'Swaraj Dweep', 'Neil Island', 'Sri Vijaya Puram'] },
  { code: 'AGX', city: 'Agatti', name: 'Agatti', aliases: ['Lakshadweep'] },
  // ---- east & north-east ----
  { code: 'BBI', city: 'Bhubaneswar', name: 'Biju Patnaik International', aliases: ['Puri', 'Konark', 'Chilika'] },
  { code: 'PAT', city: 'Patna', name: 'Jay Prakash Narayan International' },
  { code: 'GAY', city: 'Gaya', name: 'Gaya', aliases: ['Bodh Gaya', 'Bodhgaya'] },
  { code: 'DBR', city: 'Darbhanga', name: 'Darbhanga' },
  { code: 'IXR', city: 'Ranchi', name: 'Birsa Munda' },
  { code: 'DGH', city: 'Deoghar', name: 'Deoghar' },
  { code: 'IXB', city: 'Bagdogra', name: 'Bagdogra', aliases: ['Siliguri', 'Darjeeling', 'Gangtok', 'Sikkim', 'Kalimpong', 'Pelling', 'Mirik'] },
  { code: 'GAU', city: 'Guwahati', name: 'Lokpriya Gopinath Bordoloi International', aliases: ['Shillong', 'Meghalaya', 'Cherrapunji', 'Sohra', 'Kamakhya', 'Tawang'] },
  { code: 'JRH', city: 'Jorhat', name: 'Jorhat', aliases: ['Kaziranga', 'Majuli'] },
  { code: 'DIB', city: 'Dibrugarh', name: 'Dibrugarh' },
  { code: 'IXS', city: 'Silchar', name: 'Silchar' },
  { code: 'IXA', city: 'Agartala', name: 'Maharaja Bir Bikram' },
  { code: 'IMF', city: 'Imphal', name: 'Imphal' },
  { code: 'DMU', city: 'Dimapur', name: 'Dimapur', aliases: ['Kohima', 'Nagaland'] },
  { code: 'AJL', city: 'Aizawl', name: 'Lengpui', aliases: ['Mizoram'] },
  { code: 'HGI', city: 'Itanagar', name: 'Donyi Polo (Hollongi)', aliases: ['Ziro'] },
  // ---- popular international ----
  { code: 'DXB', city: 'Dubai', name: 'Dubai International', country: 'UAE' },
  { code: 'AUH', city: 'Abu Dhabi', name: 'Zayed International', country: 'UAE' },
  { code: 'DOH', city: 'Doha', name: 'Hamad International', country: 'Qatar' },
  { code: 'SIN', city: 'Singapore', name: 'Changi', country: 'Singapore' },
  { code: 'BKK', city: 'Bangkok', name: 'Suvarnabhumi', country: 'Thailand' },
  { code: 'HKT', city: 'Phuket', name: 'Phuket International', country: 'Thailand' },
  { code: 'KUL', city: 'Kuala Lumpur', name: 'Kuala Lumpur International', country: 'Malaysia' },
  { code: 'DPS', city: 'Bali', name: 'Ngurah Rai International', country: 'Indonesia', aliases: ['Denpasar'] },
  { code: 'MLE', city: 'Malé', name: 'Velana International', country: 'Maldives', aliases: ['Male', 'Maldives'] },
  { code: 'CMB', city: 'Colombo', name: 'Bandaranaike International', country: 'Sri Lanka', aliases: ['Sri Lanka'] },
  { code: 'KTM', city: 'Kathmandu', name: 'Tribhuvan International', country: 'Nepal', aliases: ['Nepal', 'Pokhara'] },
  { code: 'IST', city: 'Istanbul', name: 'Istanbul', country: 'Türkiye' },
  { code: 'LHR', city: 'London', name: 'Heathrow', country: 'UK' },
  { code: 'CDG', city: 'Paris', name: 'Charles de Gaulle', country: 'France' },
  { code: 'FRA', city: 'Frankfurt', name: 'Frankfurt', country: 'Germany' },
  { code: 'JFK', city: 'New York', name: 'John F. Kennedy International', country: 'USA' },
  { code: 'SFO', city: 'San Francisco', name: 'San Francisco International', country: 'USA' },
  { code: 'YYZ', city: 'Toronto', name: 'Pearson International', country: 'Canada' },
  { code: 'SYD', city: 'Sydney', name: 'Sydney Kingsford Smith', country: 'Australia' },
  { code: 'NRT', city: 'Tokyo', name: 'Narita International', country: 'Japan' },
]

const norm = (s: string) => s.toLowerCase().normalize('NFKD').replace(/[^a-z0-9 ]/g, '').trim()

export const airportByCode = (code: string): Airport | undefined =>
  AIRPORTS.find((a) => a.code === code.toUpperCase())

export const isIndian = (a: Airport | undefined) => !!a && !a.country

export const airportLabel = (a: Airport) => `${a.city} (${a.code})`

/** "Manali, Himachal Pradesh" -> KUU. Code, then exact city/alias, then a prefix match. */
export function airportForPlace(place: string): Airport | undefined {
  const q = norm(place.split(',')[0] ?? '')
  if (q.length < 2) return undefined
  const names = (a: Airport) => [a.city, ...(a.aliases ?? [])].map(norm)
  return (
    AIRPORTS.find((a) => a.code.toLowerCase() === q) ??
    AIRPORTS.find((a) => names(a).includes(q)) ??
    AIRPORTS.find((a) => names(a).some((n) => n.startsWith(q) || q.startsWith(n)))
  )
}

/** Suggestions for the airport picker: code, city, alias or airport name. */
export function searchAirports(text: string, limit = 8): Airport[] {
  const q = norm(text.replace(/\(.*\)/, ''))
  if (q.length < 2) return []
  const score = (a: Airport) => {
    if (a.code.toLowerCase() === q) return 0
    if (norm(a.city).startsWith(q)) return 1
    if ((a.aliases ?? []).some((x) => norm(x).startsWith(q))) return 2
    if (norm(a.name).includes(q) || norm(a.city).includes(q)) return 3
    return 9
  }
  return AIRPORTS.map((a) => [a, score(a)] as const)
    .filter(([, s]) => s < 9)
    .sort((x, y) => x[1] - y[1])
    .slice(0, limit)
    .map(([a]) => a)
}
