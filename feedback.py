"""Send feedback: opens the project's GitHub "Feedback / feature request" form in the browser.

The form (``.github/ISSUE_TEMPLATE/feedback.yml``) is pre-filled with the installed version.
Nothing is sent from PhraseLock itself: you read, write and submit the issue on GitHub (a free
account is needed), so nothing about you leaves the computer without you seeing it.
"""

import urllib.parse
import webbrowser

from version import __version__

REPO = "nanana677777/phraselock"
NEW_ISSUE_URL = f"https://github.com/{REPO}/issues/new"
TEMPLATE = "feedback.yml"


def feedback_url(version=__version__):
    """The pre-filled GitHub issue form (the field ids of feedback.yml are the parameter names)."""
    query = urllib.parse.urlencode({
        "template": TEMPLATE,
        "title": "[Feedback] ",
        "version": f"v{str(version).lstrip('vV')}",
    })
    return f"{NEW_ISSUE_URL}?{query}"


def open_feedback(opener=webbrowser.open, version=__version__):
    """Open the form. Returns (ok, url); ok is False when no browser could be opened."""
    url = feedback_url(version)
    try:
        return bool(opener(url)), url
    except Exception:
        return False, url
