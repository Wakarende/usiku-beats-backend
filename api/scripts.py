from django.contrib.auth.models import User



def generate_unique_username(email):
    # Use the part before the @ symbol as the username
    username = email.split('@')[0]
    base_username = username
    counter = 1

    while User.objects.filter(username=username).exists():
        # If a user with the generated username already exists, append a counter
        username = f"{base_username}{counter}"
        counter += 1

    return username


def get_ip_address_from_request(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get('REMOTE_ADDR')

    return ip
