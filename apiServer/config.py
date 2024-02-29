import os

# Tailscale API URL to get Devices
TAILSCALE_API_URL = os.environ.get("TAILSCALE_API_URL", "https://api.tailscale.com/api/v2/tailnet/cyberpartners.dk/devices")

# Tailscale API Key
TAILSCALE_API_KEY = os.environ.get("TAILSCALE_API_KEY", "Bearer tskey-api-k2WDqr5CNTRL-5hS1AisPfDLnsgLsoTTQELEhTtZGfAvg")
