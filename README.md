# Usiku Beats: API (Backend)

**Play the game:** https://usikubeats.com/

This is the Django REST Framework backend for Usiku Beats, a browser-based rhythm game built by Usiku Games. It serves songs, artists, pricing, player accounts and payments to the web application. The frontend repository is [usiku-beats-frontend](https://github.com/Wakarende/usiku-beats-frontend).

> Published with Usiku Games' permission. The full commit history is kept. Hardcoded credentials and a committed development database were removed from the history before publishing.

## Stack

Python, Django, Django REST Framework, JWT authentication, Xsolla Store API, MaxMind GeoLite2.

## My contributions

**Artist detail API.** I built the full vertical slice: six new fields on the `Artist` model, five migrations, a serializer, an extended song serializer for nested artist fields, and a JWT-authenticated detail view.

**Xsolla price sync and public pricing endpoint.**
- A new module of about 240 lines that syncs admin-set country prices to Xsolla's store catalogue. It includes a retry loop that reads Xsolla's own error message, drops any currency the store isn't configured for and retries.
- A public endpoint that resolves the caller's country from their IP using MaxMind GeoLite2 and returns that country's price. If the GeoIP package or the address lookup fails, it falls back to USD instead of erroring.
- A fix for a URL-routing collision between two branches' admin routes.

I built this on the existing country-pricing model, with Claude Code as a pair programmer, and drove the diagnosis, the integration design and the iteration myself.

**Production fix: HTTP 500 on every pricing request.** A week after the pricing endpoint shipped, every call to it started returning HTTP 500. The cause was an exception class imported inside the `try` block it was meant to guard. That made it a local name inside the function, and Python could try to read it before it was ever assigned, raising `UnboundLocalError`. I fixed it by importing the module at module level, referencing the exception by its full name and adding an `ImportError` fallback. The diff is four lines.

## Running locally

Copy `.env.example` to `.env` and fill in your own values. Then install the dependencies and run:

```bash
python manage.py migrate
python manage.py runserver
```

Xsolla features need your own Xsolla project credentials.
