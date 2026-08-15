"""The web page an invite link opens.

Email clients only linkify http(s). A `bliss://accept-invite?token=…` in a mail
body renders as plain text in Gmail — the recipient sees the scheme, cannot tap
it, and has no obvious next step. That is what the invite email was sending.

So the email carries an https link to this view, and this view carries the
button that opens the app. One extra tap, and it works in every mail client.

It is deliberately not a redirect. An automatic `Location: bliss://…` fails
silently on a device without the app installed, and browsers increasingly block
scheme redirects that were not started by a user gesture. A page with a button
also gives us somewhere to say "install the app first", which is the actual
state of about half the people who will open this.

The token is not logged here. It is in the path, so it will appear in the
platform's access log — an accepted trade for the pilot, and the reason the
invite is single-use and expires in 72 hours.
"""

from __future__ import annotations

from django.http import HttpResponse
from django.views.decorators.clickjacking import xframe_options_deny
from django.views.decorators.http import require_GET

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Your Bliss invite</title>
<style>
  :root {{ color-scheme: light; }}
  body {{
    margin: 0; padding: 32px 20px;
    background: #FFF6ED;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #4A4A4A; -webkit-font-smoothing: antialiased;
  }}
  .card {{
    max-width: 420px; margin: 0 auto; background: #FFFDF9;
    border-radius: 20px; padding: 32px 28px; text-align: center;
    box-shadow: 0 2px 20px rgba(74,74,74,.06);
  }}
  h1 {{ font-size: 22px; margin: 0 0 12px; color: #3B2A24; }}
  p  {{ font-size: 16px; line-height: 1.55; margin: 0 0 20px; }}
  .btn {{
    display: block; background: #FF9B8A; color: #3B2A24;
    text-decoration: none; font-weight: 600; font-size: 17px;
    padding: 16px 20px; border-radius: 14px; margin: 24px 0 12px;
  }}
  .hint {{ font-size: 14px; color: #7a7a7a; margin-top: 20px; }}
  .mark {{ font-size: 34px; letter-spacing: -6px; }}
</style>
</head>
<body>
  <div class="card">
    <div class="mark">&#9711;&#9711;</div>
    <h1>Your partner invited you to Bliss</h1>
    <p>Tap below to link your accounts. You will need the Bliss app installed
       on this phone first.</p>
    <a class="btn" href="bliss://accept-invite?token={token}">Open in Bliss</a>
    <p class="hint">Nothing happened? Install Bliss, then tap the button again.
       This invite expires in 72 hours and can only be used once.</p>
  </div>
</body>
</html>
"""


@require_GET
@xframe_options_deny
def invite_landing(request, token: str) -> HttpResponse:
    # Escaped: the token is user-influenced only in the sense that anyone can
    # put anything in the path, and it is interpolated into an href.
    from django.utils.html import escape

    response = HttpResponse(_PAGE.format(token=escape(token)))
    # Not something to keep in a shared cache — it contains a single-use token.
    response["Cache-Control"] = "no-store, private"
    response["Referrer-Policy"] = "no-referrer"
    return response
