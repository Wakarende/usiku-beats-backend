import hashlib
from .constants import XSOLLA_WEBHOOK_SECRET_KEY


def verify_xsolla_signature(request):
    """
    Verify Xsolla webhook signature.
    Signature = SHA1(request_body + secret_key)
    Authorization header format: "Signature <signature_value>"

    Returns: (is_valid: bool, error_message: str or None)
    """
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')

    if not auth_header.startswith('Signature '):
        return False, 'Invalid authorization header format'

    received_signature = auth_header[10:]  # Remove 'Signature ' prefix

    if not XSOLLA_WEBHOOK_SECRET_KEY:
        return False, 'Xsolla secret key not configured'

    # Get raw request body - must use exact bytes as received
    raw_body = request.body.decode('utf-8')

    # Generate signature: SHA1(body + secret_key)
    signature_string = raw_body + XSOLLA_WEBHOOK_SECRET_KEY
    computed_signature = hashlib.sha1(signature_string.encode('utf-8')).hexdigest()

    if computed_signature.lower() != received_signature.lower():
        return False, 'Signature mismatch'

    return True, None
