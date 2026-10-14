"""Static approximate district-centre coordinates for Karnataka, India."""

_DISTRICT_CENTRES = (
    ("Bagalkote", 16.18, 75.69),
    ("Ballari", 15.14, 76.92),
    ("Belagavi", 15.85, 74.50),
    ("Bengaluru Rural", 13.29, 77.53),
    ("Bengaluru Urban", 12.97, 77.59),
    ("Bidar", 17.91, 77.52),
    ("Chamarajanagar", 11.92, 76.94),
    ("Chikkaballapur", 13.43, 77.73),
    ("Chikkamagaluru", 13.32, 75.77),
    ("Chitradurga", 14.23, 76.40),
    ("Dakshina Kannada", 12.84, 75.25),
    ("Davanagere", 14.47, 75.92),
    ("Dharwad", 15.46, 75.01),
    ("Gadag", 15.43, 75.63),
    ("Hassan", 13.01, 76.10),
    ("Haveri", 14.80, 75.40),
    ("Kalaburagi", 17.33, 76.83),
    ("Kodagu", 12.42, 75.74),
    ("Kolar", 13.14, 78.13),
    ("Koppal", 15.35, 76.15),
    ("Mandya", 12.52, 76.90),
    ("Mysuru", 12.30, 76.65),
    ("Raichur", 16.21, 77.36),
    ("Ramanagara", 12.72, 77.28),
    ("Shivamogga", 13.93, 75.57),
    ("Tumakuru", 13.34, 77.10),
    ("Udupi", 13.34, 74.74),
    ("Uttara Kannada", 14.80, 74.13),
    ("Vijayanagara", 15.33, 76.46),
    ("Vijayapura", 16.83, 75.71),
    ("Yadgir", 16.77, 77.14),
)

KARNATAKA_DISTRICTS = tuple(
    {
        "state": "Karnataka",
        "name": name,
        "district": name,
        "latitude": latitude,
        "longitude": longitude,
        "lat": latitude,
        "lon": longitude,
    }
    for name, latitude, longitude in _DISTRICT_CENTRES
)
