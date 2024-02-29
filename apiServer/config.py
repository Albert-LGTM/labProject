import os

# Tailscale API URL to get Devices
TAILSCALE_API_URL = os.environ.get("TAILSCALE_API_URL", "https://api.tailscale.com/api/v2/tailnet/<org>/devices")

# Tailscale API Key
TAILSCALE_API_KEY = os.environ.get("TAILSCALE_API_KEY", "Bearer <key>")

