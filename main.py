"""CareJobs.Now for Ulauncher (extension API v2).

Type "cj icu nurse tx" to search free US healthcare job listings, with the pay
employers post. Only what you type is sent, to https://carejobs.now/api/mcp.
No account, no tracking. Standard library only.
"""

from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.client.Extension import Extension
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem

USER_AGENT = "CareJobs-Ulauncher-Plugin/1.0"

# ---------------------------------------------------------------------------
# CareJobs.Now core: query parsing, API call, result items. Standard library
# only. Everything above the launcher glue is plain functions so it can be
# tested without a launcher. Expects USER_AGENT to be defined before it.
# ---------------------------------------------------------------------------
import json
import re
import urllib.parse
import urllib.request

SITE_URL = "https://carejobs.now"
API_URL = SITE_URL + "/api/mcp"
TIMEOUT_SECONDS = 8
MAX_JOBS = 10
MAX_QUERY_CHARS = 200
MAX_BODY_BYTES = 2000000
HINT_TITLE = "Type a job and a state, e.g. icu nurse tx"
POPULAR_SEARCHES = ("registered nurse", "CNA", "LPN", "medical assistant", "travel nurse")

# The 50 states and DC: what the CareJobs.Now API accepts.
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}
STATE_CODES_BY_NAME = {name.lower(): code for code, name in US_STATES.items()}
# Two-letter job words that are also state codes: a lone "pa" or "ma" means
# physician assistant or medical assistant, not Pennsylvania or Massachusetts.
JOB_WORDS_THAT_LOOK_LIKE_STATES = ("PA", "MA")


def parse_query(text):
    """Split what the user typed into {"query", "state", "remote"}.

    "icu nurse tx" -> icu nurse / TX; "rn new york" -> rn / NY;
    "remote coding" -> coding / remote; a leading or trailing "in" is dropped.
    A two-letter word is a state only when it is the last word and a valid
    USPS code ("in" is never read as Indiana: it is the connector word, so type
    "indiana" for Indiana).
    """
    words = re.sub(r"[,;]+", " ", (text or "")[:MAX_QUERY_CHARS]).split()
    state = ""
    for size in (3, 2, 1):  # full state name at the end, longest first
        if len(words) >= size:
            code = STATE_CODES_BY_NAME.get(" ".join(words[-size:]).lower())
            if code:
                state = code
                del words[-size:]
                break
    if not state and words:
        last = words[-1].upper()
        lone_job_word = len(words) == 1 and last in JOB_WORDS_THAT_LOOK_LIKE_STATES
        if len(last) == 2 and last in US_STATES and last != "IN" and not lone_job_word:
            state = last
            words.pop()
    remote = any(word.lower() == "remote" for word in words)
    words = [word for word in words if word.lower() != "remote"]
    while words and words[0].lower() == "in":
        words.pop(0)
    while words and words[-1].lower() == "in":
        words.pop()
    return {"query": " ".join(words), "state": state, "remote": remote}


def board_url(parsed):
    """The CareJobs.Now board URL for the same search."""
    params = []
    if parsed["query"]:
        params.append(("q", parsed["query"]))
    if parsed["state"]:
        params.append(("state", parsed["state"]))
    if parsed["remote"]:
        params.append(("remote", "1"))
    if not params:
        return SITE_URL + "/"
    return SITE_URL + "/?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)


def short_pay(pay, employer=""):
    """One-line pay: keep the part before " (", and say "typical at <employer>"
    when the parenthesis says the figure is a typical range, not the posting's."""
    if not isinstance(pay, str) or not pay.strip():
        return ""
    head, separator, rest = pay.strip().partition(" (")
    head = head.strip()
    if separator and rest.lstrip().lower().startswith("typical"):
        return head + " typical at " + employer if employer else head + " typical"
    return head


def _text(value):
    return value.strip() if isinstance(value, str) else ""


def _web_url(value, fallback):
    """Only ever hand http(s) addresses to the browser."""
    value = _text(value)
    return value if urllib.parse.urlparse(value).scheme in ("http", "https") else fallback


def job_item(job):
    employer = _text(job.get("employer"))
    title = _text(job.get("title")) or "Healthcare job"
    listed = _text(job.get("listed"))
    parts = [short_pay(job.get("pay"), employer), _text(job.get("location")), "listed " + listed if listed else ""]
    url = _web_url(job.get("url"), SITE_URL + "/")
    employer_page = _web_url(job.get("employer_page"), "")
    return {
        "kind": "job",
        "title": title + " at " + employer if employer else title,
        "subtitle": " | ".join(part for part in parts if part),
        "url": url,
        "employer_page": employer_page,
    }


def hint_items():
    items = [{
        "kind": "hint",
        "title": HINT_TITLE,
        "subtitle": "Free US healthcare jobs with the pay employers post. Press Enter to open CareJobs.Now",
        "url": SITE_URL + "/",
        "employer_page": "",
    }]
    for term in POPULAR_SEARCHES:
        items.append({
            "kind": "popular",
            "title": "Search " + term,
            "subtitle": "Popular search on CareJobs.Now",
            "url": SITE_URL + "/?q=" + urllib.parse.quote(term),
            "employer_page": "",
        })
    return items


def error_item(parsed):
    return {
        "kind": "error",
        "title": "CareJobs.Now could not be reached",
        "subtitle": "Press Enter to search on CareJobs.Now in your browser",
        "url": board_url(parsed),
        "employer_page": "",
    }


def _structured_content(body):
    """The tool's structuredContent from a JSON (or event-stream) answer."""
    body = body.strip()
    if not body.startswith("{"):  # server-sent events: take the last data line
        data_lines = [line[5:].strip() for line in body.splitlines() if line.startswith("data:")]
        body = data_lines[-1] if data_lines else ""
    result = json.loads(body).get("result")
    if not isinstance(result, dict) or result.get("isError"):
        raise ValueError("the search was refused")
    content = result.get("structuredContent")
    if not isinstance(content, dict):
        raise ValueError("the answer has no structuredContent")
    return content


def search_jobs(parsed, limit=MAX_JOBS):
    """Call search_healthcare_jobs on the live API. Raises on any failure."""
    arguments = {"limit": limit}
    if parsed["query"]:
        arguments["query"] = parsed["query"]
    if parsed["state"]:
        arguments["state"] = parsed["state"]
    if parsed["remote"]:
        arguments["remote"] = True
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "search_healthcare_jobs", "arguments": arguments},
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return _structured_content(response.read(MAX_BODY_BYTES).decode("utf-8", "replace"))


def build_items(text, fetch=search_jobs):
    """What to show for the typed text: a list of plain item dicts. Never raises."""
    parsed = parse_query(text)
    if not (parsed["query"] or parsed["state"] or parsed["remote"]):
        return hint_items()
    try:
        content = fetch(parsed)
        jobs = [job for job in (content.get("jobs") or []) if isinstance(job, dict)][:MAX_JOBS]
        items = [job_item(job) for job in jobs]
        more = _web_url(content.get("more"), board_url(parsed))
        total = content.get("total")
        total = total if isinstance(total, int) and total >= len(items) else len(items)
    except Exception:
        return [error_item(parsed)]
    if not items:
        return [{
            "kind": "empty",
            "title": "No open jobs match this search yet",
            "subtitle": "Press Enter to try fewer words on CareJobs.Now",
            "url": more,
            "employer_page": "",
        }]
    items.append({
        "kind": "more",
        "title": "See all {:,} {} on CareJobs.Now".format(total, "job" if total == 1 else "jobs"),
        "subtitle": "Opens the same search on the board, with filters",
        "url": more,
        "employer_page": "",
    })
    return items
# ---------------------------------------------------------------------------
# End of core.
# ---------------------------------------------------------------------------


ICON = "images/icon.png"


def to_result_item(item):
    """Map a core item to an Ulauncher row. Enter opens it; Alt+Enter opens the
    employer's page on CareJobs.Now (jobs only)."""
    return ExtensionResultItem(
        icon=ICON,
        name=item["title"],
        description=item["subtitle"],
        highlightable=False,  # the search is done by the board, not fuzzy-matched here
        on_enter=OpenUrlAction(item["url"]),
        on_alt_enter=OpenUrlAction(item["employer_page"]) if item["employer_page"] else None,
    )


class CareJobsExtension(Extension):

    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):
        text = event.get_argument() or ""
        try:
            items = build_items(text)
        except Exception:  # never crash the extension
            items = [error_item(parse_query(text))]
        return RenderResultListAction([to_result_item(item) for item in items])


if __name__ == "__main__":
    CareJobsExtension().run()
