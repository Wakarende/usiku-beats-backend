import os

# Xsolla configuration
# Get secret key from Xsolla Publisher Account > Project settings > Webhooks
XSOLLA_WEBHOOK_SECRET_KEY = "REMOVED_SECRET"

# SKU to rewards mapping
# Maps Xsolla product SKUs to the virtual currency rewards
XSOLLA_SKU_REWARDS = {
    'bundle_starter': {'discs': 100, 'gems': 100},
}
