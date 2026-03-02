import os

# Xsolla configuration
# Get secret key from Xsolla Publisher Account > Project settings > Webhooks
XSOLLA_WEBHOOK_SECRET_KEY = "REMOVED_SECRET"

# Xsolla API credentials (from Publisher Account > Company settings > API keys)
XSOLLA_PROJECT_ID = "292524"
XSOLLA_MERCHANT_ID = "836727"
XSOLLA_API_KEY = "REMOVED_SECRET"

# The SKU of the purchasable item in Xsolla's catalog
XSOLLA_ITEM_SKU = 'bundle_starter'

# SKU to rewards mapping
# Maps Xsolla product SKUs to the virtual currency rewards
XSOLLA_SKU_REWARDS = {
    'bundle_starter': {'discs': 100, 'gems': 100},
}
