from rest_framework import throttling
from .models import Profile


class GlobalBurstRateThrottle(throttling.UserRateThrottle):
    scope = 'burst'

class GlobalSustainedRateThrottle(throttling.UserRateThrottle):
    scope = 'sustained'
    
    

class FreeSubscriptionThrottle(throttling.UserRateThrottle):
    rate = '10/hour'

class PremiumSubscriptionThrottle(throttling.UserRateThrottle):
    rate = '100/hour'

class EnterpriseSubscriptionThrottle(throttling.UserRateThrottle):
    rate = '100/hour'

