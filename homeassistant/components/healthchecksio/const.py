"""Constants for the healthchecksio integration."""
DOMAIN = "healthchecksio"

SCAN_INTERVAL = 300

ICON_MAPPING = {
    "new": "mdi:server-network",
    "started": "mdi:server-network",
    "up": "mdi:server-network",
    "grace": "mdi:server-network",
    "down": "mdi:server-network-off",
    "paused": "mdi:server-network",
}
