"""Constants for the ARRIS SurfBoard integration."""

DOMAIN = "arris_cablemodems"
DEFAULT_HOST = "192.168.100.1"
DEFAULT_NAME = "ARRIS Cable Modem"

# Known ARRIS modem models that work with this integration
SUPPORTED_MODELS = ["SB6183", "SB6190", "TG1682G", "TG3482G"]

# Discovery scan range - common modem IPs
DISCOVERY_HOSTS = [
    "192.168.100.1",  # Most common ARRIS default
    "192.168.0.1",    # Alternative default
    "10.0.0.1",       # Some configurations
]
