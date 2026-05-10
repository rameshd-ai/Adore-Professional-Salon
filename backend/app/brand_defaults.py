"""Public-facing defaults for `site_settings` (singleton id=1). Single source for seed, ORM defaults, and startup backfill."""

DEFAULT_SALON_NAME = "Adore Professional Salon"
DEFAULT_PHONE = "+91 98765 43210"
DEFAULT_EMAIL = "hello@adoreprofessionalsalon.com"
DEFAULT_HOURS_LINE = "Mon – Sat: 9AM – 8PM"
DEFAULT_ADDRESS = (
    "VIP Road, Police Line, Sri Vijaya Puram, 744103, "
    "Andaman and Nicobar Islands, India"
)
# Google Maps pin (WGS84); Contact page embed prefers lat,lng when set in Site settings.
DEFAULT_MAP_LAT = "11.659874"
DEFAULT_MAP_LNG = "92.736025"

# Normalize old demo / ambiguous names to DEFAULT_SALON_NAME on startup (see seed.ensure_site_settings_about_content).
_LEGACY_SALON_NAMES = frozenset({"glamr", "flamr"})

# Old frontend fallback / placeholder contact values → replace from DB defaults on startup.
_LEGACY_US_FAKE_PHONE = "+1 (555) 000-0000"
_LEGACY_SHORT_ADDRESS = "123 Beauty Street"
_LEGACY_FULL_ADDRESS_MUMBAI = "123 Beauty Street, Mumbai 400001"


def is_legacy_placeholder_address(address: str | None) -> bool:
    """True for empty/demo Mumbai lines — replaced with DEFAULT_ADDRESS on API startup."""
    t = (address or "").strip().lower()
    if not t:
        return True
    if t == _LEGACY_SHORT_ADDRESS.lower():
        return True
    if t == _LEGACY_FULL_ADDRESS_MUMBAI.lower():
        return True
    if "123 beauty street" in t and "mumbai" in t:
        return True
    return False
