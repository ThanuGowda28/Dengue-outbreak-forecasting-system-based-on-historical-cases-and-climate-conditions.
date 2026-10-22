"""Approximate district-centre coordinates for Andhra Pradesh, India."""

_DISTRICT_CENTRES = (
    ("Alluri Sitharama Raju", 17.75, 82.70),
    ("Anakapalli", 17.69, 83.00),
    ("Anantapuramu", 14.68, 77.60),
    ("Annamayya", 14.06, 78.75),
    ("Bapatla", 15.90, 80.47),
    ("Chittoor", 13.22, 79.10),
    ("Dr. B.R. Ambedkar Konaseema", 16.57, 82.01),
    ("East Godavari", 17.00, 81.78),
    ("Eluru", 16.71, 81.10),
    ("Guntur", 16.30, 80.44),
    ("Kakinada", 16.99, 82.25),
    ("Krishna", 16.18, 81.13),
    ("Kurnool", 15.83, 78.04),
    ("Markapuram", 15.74, 79.27),
    ("Manyam", 18.78, 83.43),
    ("Nandyal", 15.48, 78.48),
    ("NTR", 16.51, 80.63),
    ("Palnadu", 16.25, 79.95),
    ("Polavaram", 17.45, 81.77),
    ("Prakasam", 15.50, 79.05),
    ("Sri Potti Sriramulu Nellore", 14.44, 79.99),
    ("Sri Sathya Sai", 14.17, 77.81),
    ("Srikakulam", 18.30, 83.90),
    ("Tirupati", 13.63, 79.42),
    ("Visakhapatnam", 17.72, 83.30),
    ("Vizianagaram", 18.11, 83.40),
    ("West Godavari", 16.54, 81.52),
    ("YSR Kadapa", 14.47, 78.82),
)

ANDHRA_PRADESH_DISTRICTS = tuple(
    {
        "state": "Andhra Pradesh",
        "name": name,
        "district": name,
        "latitude": latitude,
        "longitude": longitude,
        "lat": latitude,
        "lon": longitude,
    }
    for name, latitude, longitude in _DISTRICT_CENTRES
)
