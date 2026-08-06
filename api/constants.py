import os

# Xsolla configuration
# Secrets are read from the environment (see .env.example). Do NOT hardcode them.
# Get secret key from Xsolla Publisher Account > Project settings > Webhooks
XSOLLA_WEBHOOK_SECRET_KEY = os.environ.get("XSOLLA_WEBHOOK_SECRET_KEY", "")

# Xsolla API credentials (from Publisher Account > Company settings > API keys)
# PROJECT_ID / MERCHANT_ID are non-secret identifiers; the API key is a secret.
XSOLLA_PROJECT_ID = os.environ.get("XSOLLA_PROJECT_ID", "292524")
XSOLLA_MERCHANT_ID = os.environ.get("XSOLLA_MERCHANT_ID", "836727")
XSOLLA_API_KEY = os.environ.get("XSOLLA_API_KEY", "")

# The SKU of the purchasable item in Xsolla's catalog
XSOLLA_ITEM_SKU = 'bundle_starter'

# SKU to rewards mapping
# Maps Xsolla product SKUs to the virtual currency rewards
XSOLLA_SKU_REWARDS = {
    'bundle_starter': {'discs': 100, 'gems': 100},
}
