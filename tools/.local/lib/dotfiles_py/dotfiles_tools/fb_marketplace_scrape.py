#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "playwright",
# ]
# ///
import argparse
import csv
import re
import sys
import tomllib
import time
from collections import Counter
from dataclasses import dataclass, replace
from fnmatch import fnmatchcase
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


DEFAULT_PROFILE = Path.home() / ".local/share/fb-marketplace-profile"
DEFAULT_OUTPUT = Path("facebook_marketplace_listings.csv")
DEFAULT_MARKETPLACE_URL = "https://www.facebook.com/marketplace/?ref=app_tab"
DEFAULT_BROWSER_CHANNEL = "chrome"
COMMANDS = {"scrape", "enrich"}

FIELDS = [
    "id",
    "title",
    "price",
    "price_value",
    "price_converted",
    "location",
    "url",
    "image",
    "scraped_at",
    "description",
    "description_scraped_at",
    "description_error",
]

REJECTED_FIELDS = [
    "rejection_reason",
    "target",
    "id",
    "title",
    "price",
    "price_value",
    "price_converted",
    "location",
    "url",
    "image",
    "scraped_at",
    "raw_lines",
    "raw_text",
    "matched_pattern",
]

DESCRIPTION_FIELDS = [
    "description",
    "description_scraped_at",
    "description_error",
]

PRICE_MARKER_RE = re.compile(
    r"(৳|\$|£|€|\bfree\b|(?<![A-Za-z])(?:Tk|BDT|Rs)\s*\d|\b(?:Tk|BDT|Rs)\b)",
    re.I,
)
BARE_PRICE_RE = re.compile(
    r"^(?:free|0|[1-9]\d{0,2}(?:[.,]\d+)?\s*(?:k|thousand|lac|lakh)?)$",
    re.I,
)
CARD_NON_TITLE_RE = re.compile(
    r"^(?:just listed|new listing|listed\b.*|sponsored|marketplace|today's picks|"
    r"price reduced|pending|sold|sold out|available|not available|details|"
    r"seller information|seller details|location|map|message seller|see translation)$",
    re.I,
)
DETAIL_NON_TITLE_RE = re.compile(
    r"^(?:condition|used\s*[–-]\s*.*|send seller a message|"
    r"hello, is this still available\??|joined facebook\b.*)$",
    re.I,
)
FREE_RE = re.compile(r"\bfree\b", re.I)
NUMBER_RE = re.compile(r"\d+(?:[,.]\d+)*(?:\.\d+)?")
LOCATION_SPLIT_RE = re.compile(r"[|,]")
LOCATION_ALIASES = {
    "chittagong": ("chittagong", "chattogram", "chattagram"),
    "chattogram": ("chattogram", "chittagong", "chattagram"),
    "chattagram": ("chattagram", "chittagong", "chattogram"),
}
TITLE_PATTERN_SPLIT_RE = re.compile(r"[|,]")
GLOB_META_RE = re.compile(r"[*?\[]")
TITLE_PATTERN_ALIASES = {
    "iphone": ("iphone", "i phone", "i-phone"),
    "oneplus": ("oneplus", "one plus", "1+"),
    "pixel": ("pixel", "google pixel"),
    "redmi": ("redmi", "xiaomi redmi"),
    "poco": ("poco", "xiaomi poco"),
}

EXPAND_DESCRIPTION_SCRIPT = r"""
() => {
  const clean = text => (text || "").replace(/\s+/g, " ").trim();
  const buttons = [...document.querySelectorAll('[role="button"], span, div')]
    .filter(node => clean(node.innerText || node.textContent || "") === "See more");

  for (const button of buttons.slice(0, 5)) {
    try {
      button.click();
    } catch (_) {
    }
  }
}
"""

DESCRIPTION_SCRIPT = r"""
() => {
  const clean = text => (text || "").replace(/\s+/g, " ").trim();
  const linesOf = node => (node.innerText || node.textContent || "")
    .split("\n")
    .map(clean)
    .filter(Boolean);
  const nodes = [...document.querySelectorAll('div, span, h2, h3')];
  const labelRe = /^(details|description|seller's description|about this item)$/i;
  const stopRe = /^(seller information|seller details|location|map|message seller|listed|see translation|sponsored)$/i;
  const skipRe = /^(details|description|seller's description|about this item|message|save|share|report|send|copy link)$/i;

  const textAfterLabel = labelNode => {
    for (let node = labelNode, depth = 0; node && depth < 7; node = node.parentElement, depth++) {
      const lines = linesOf(node);
      const index = lines.findIndex(line => labelRe.test(line));
      if (index < 0) continue;

      const tail = [];
      for (const line of lines.slice(index + 1)) {
        if (stopRe.test(line)) break;
        if (!skipRe.test(line)) tail.push(line);
      }

      const text = clean(tail.join(" "));
      if (text.length >= 8) return text;
    }
    return "";
  };

  for (const node of nodes) {
    const lines = linesOf(node);
    const text = clean(node.innerText || node.textContent || "");
    if (labelRe.test(text) || (lines[0] && labelRe.test(lines[0]))) {
      const found = textAfterLabel(node);
      if (found) return found;
    }
  }

  return "";
}
"""

DETAIL_TITLE_SCRIPT = r"""
() => {
  const clean = text => (text || "").replace(/\s+/g, " ").trim();
  const badRe = /^(marketplace|browse all|notifications|inbox|buying|selling|details|condition|seller information|seller details|location|map|message|save|share|report|see translation|sponsored|send seller a message|hello, is this still available\?)$/i;
  const priceRe = /^(৳|BDT|Tk|Rs|\$|£|€|\bfree\b)/i;
  const candidates = [];

  const addText = text => {
    for (const line of (text || "").split("\n").map(clean).filter(Boolean)) {
      if (line.length > 160) continue;
      if (badRe.test(line) || priceRe.test(line)) continue;
      candidates.push(line);
    }
  };

  for (const selector of [
    '[role="main"] h1',
    'h1',
    '[role="main"] [role="heading"][aria-level="1"]',
    '[role="heading"][aria-level="1"]',
    '[role="main"] [role="heading"][aria-level="2"]',
    '[role="heading"][aria-level="2"]'
  ]) {
    for (const node of document.querySelectorAll(selector)) {
      addText(node.innerText || node.textContent || "");
    }
  }

  const main = document.querySelector('[role="main"]') || document.body;
  const lines = (main.innerText || "").split("\n").map(clean).filter(Boolean);
  for (const line of lines.slice(0, 100)) {
    if (/^details$/i.test(line)) break;
    addText(line);
  }

  return candidates[0] || "";
}
"""


@dataclass(frozen=True)
class Criteria:
    min_price: int | None = None
    max_price: int | None = None
    include_free: bool = True
    convert_small_prices: bool = True
    match_converted_price: bool = False
    small_price_threshold: int = 100
    small_price_multiplier: int = 1000
    locations: tuple[str, ...] = ()
    title_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class PriceInfo:
    raw: str
    value: int | None
    is_free: bool
    converted: bool


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def is_price_line(line: str) -> bool:
    line = clean_text(line)
    return bool(PRICE_MARKER_RE.search(line) or BARE_PRICE_RE.fullmatch(line))


def is_card_non_title_line(line: str) -> bool:
    return bool(CARD_NON_TITLE_RE.fullmatch(clean_text(line)))


def is_title_candidate(line: str, price: str) -> bool:
    line = clean_text(line)
    return bool(line) and line != price and not is_price_line(line) and not is_card_non_title_line(line)


def is_detail_title_candidate(line: str) -> bool:
    line = clean_text(line)
    return is_title_candidate(line, "") and not DETAIL_NON_TITLE_RE.fullmatch(line)


def is_repairable_bad_title(title: str) -> bool:
    title = clean_text(title)
    return not title or is_card_non_title_line(title) or is_price_line(title)


def should_replace_listing_field(field: str, old: str, new: str) -> bool:
    old = clean_text(old)
    new = clean_text(new)
    if not new:
        return False
    if field == "scraped_at":
        return True
    if field == "title":
        if not old:
            return is_detail_title_candidate(new)
        return is_repairable_bad_title(old) and is_detail_title_candidate(new)
    if not old:
        return True
    return False


def price_unit_multiplier(text: str) -> int:
    lower = text.lower()
    if re.search(r"\d\s*k\b|\bthousand\b", lower):
        return 1000
    if re.search(r"\b(?:lac|lakh)\b", lower):
        return 100000
    return 1


def parse_number_token(token: str) -> float:
    return float(token.replace(",", ""))


def parse_amount(value: object, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    if isinstance(value, int):
        amount = value
    elif isinstance(value, float):
        amount = int(value)
    elif isinstance(value, str):
        match = NUMBER_RE.search(value)
        if not match:
            raise ValueError(f"{name} must contain a number")
        amount = int(parse_number_token(match.group(0)) * price_unit_multiplier(value))
    else:
        raise ValueError(f"{name} must be a number")

    if amount < 0:
        raise ValueError(f"{name} must be greater than or equal to 0")
    return amount


def parse_cli_amount(value: str) -> int:
    try:
        amount = parse_amount(value, "price")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc

    if amount is None:
        raise argparse.ArgumentTypeError("price must contain a number")
    return amount


def parse_bool(value: object, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ValueError(f"{name} must be true or false")


def normalize_location(value: str) -> str:
    return clean_text(value).casefold()


def parse_locations(value: object, name: str = "locations") -> tuple[str, ...]:
    if value is None:
        return ()

    raw_locations: list[str] = []
    if isinstance(value, str):
        raw_locations.extend(LOCATION_SPLIT_RE.split(value))
    elif isinstance(value, (list, tuple)):
        for item in value:
            if not isinstance(item, str):
                raise ValueError(f"{name} entries must be strings")
            raw_locations.extend(LOCATION_SPLIT_RE.split(item))
    else:
        raise ValueError(f"{name} must be a string or list of strings")

    locations = []
    seen = set()
    for item in raw_locations:
        location = normalize_location(item)
        for candidate in LOCATION_ALIASES.get(location, (location,)):
            if candidate and candidate not in seen:
                locations.append(candidate)
                seen.add(candidate)

    return tuple(locations)


def parse_title_patterns(value: object, name: str = "title_patterns") -> tuple[str, ...]:
    if value is None:
        return ()

    raw_patterns: list[str] = []
    if isinstance(value, str):
        raw_patterns.extend(TITLE_PATTERN_SPLIT_RE.split(value))
    elif isinstance(value, (list, tuple)):
        for item in value:
            if not isinstance(item, str):
                raise ValueError(f"{name} entries must be strings")
            raw_patterns.extend(TITLE_PATTERN_SPLIT_RE.split(item))
    else:
        raise ValueError(f"{name} must be a string or list of strings")

    patterns = []
    seen = set()
    for raw_pattern in raw_patterns:
        pattern = clean_text(raw_pattern)
        if not pattern:
            continue

        negate = pattern.startswith("!")
        if negate:
            pattern = clean_text(pattern[1:])
            if not pattern:
                raise ValueError(f"{name} contains an empty negated pattern")

        aliases = TITLE_PATTERN_ALIASES.get(pattern.casefold(), (pattern,))
        for alias in aliases:
            glob = normalize_title_glob(alias)
            if negate:
                glob = f"!{glob}"
            key = glob.casefold()
            if key not in seen:
                patterns.append(glob)
                seen.add(key)

    return tuple(patterns)


def normalize_title_glob(pattern: str) -> str:
    pattern = clean_text(pattern).casefold()
    if not GLOB_META_RE.search(pattern):
        pattern = f"*{pattern}*"
    return pattern


def location_matches(location: str, criteria: Criteria) -> bool:
    if not criteria.locations:
        return True

    normalized = normalize_location(location)
    if not normalized:
        return False

    return any(allowed in normalized for allowed in criteria.locations)


def title_pattern_match(title: str, criteria: Criteria) -> tuple[bool, str, str]:
    if not criteria.title_patterns:
        return True, "accepted_title", ""

    normalized = clean_text(title).casefold()
    if not normalized:
        return False, "missing_title", ""

    include_patterns = []
    for pattern in criteria.title_patterns:
        negate = pattern.startswith("!")
        glob = pattern[1:] if negate else pattern
        if fnmatchcase(normalized, glob):
            if negate:
                return False, "excluded_title_pattern", pattern
            include_patterns.append(pattern)

    positive_patterns = tuple(
        pattern for pattern in criteria.title_patterns if not pattern.startswith("!")
    )
    if positive_patterns and not include_patterns:
        return False, "title_pattern_not_matched", "|".join(positive_patterns)

    return True, "accepted_title", include_patterns[0] if include_patterns else ""


def parse_price_info(price: str, criteria: Criteria) -> PriceInfo:
    raw = clean_text(price)
    if not raw:
        return PriceInfo(raw=raw, value=None, is_free=False, converted=False)
    if FREE_RE.search(raw):
        return PriceInfo(raw=raw, value=None, is_free=True, converted=False)

    match = NUMBER_RE.search(raw)
    if not match:
        return PriceInfo(raw=raw, value=None, is_free=False, converted=False)

    multiplier = price_unit_multiplier(raw)
    value = int(parse_number_token(match.group(0)) * multiplier)
    if value <= 0:
        return PriceInfo(raw=raw, value=value, is_free=True, converted=False)

    converted = False
    if (
        criteria.convert_small_prices
        and multiplier == 1
        and value < criteria.small_price_threshold
    ):
        value *= criteria.small_price_multiplier
        converted = True

    return PriceInfo(raw=raw, value=value, is_free=False, converted=converted)


def normalize_manifest_values(values: dict[str, object]) -> dict[str, object]:
    values = dict(values)
    normalized: dict[str, object] = {}

    price = values.pop("price", None)
    if price is not None:
        if not isinstance(price, dict):
            raise ValueError("criteria.price must be a table")
        price_values = dict(price)
        if "min" in price_values:
            normalized["min_price"] = price_values.pop("min")
        if "max" in price_values:
            normalized["max_price"] = price_values.pop("max")
        if "min_price" in price_values:
            normalized["min_price"] = price_values.pop("min_price")
        if "max_price" in price_values:
            normalized["max_price"] = price_values.pop("max_price")
        if price_values:
            unknown = ", ".join(sorted(price_values))
            raise ValueError(f"unknown criteria.price key(s): {unknown}")

    aliases = {
        "price-min": "min_price",
        "price_min": "min_price",
        "price-max": "max_price",
        "price_max": "max_price",
        "min-price": "min_price",
        "max-price": "max_price",
        "include-free": "include_free",
        "convert-small-prices": "convert_small_prices",
        "match-converted-price": "match_converted_price",
        "small-price-threshold": "small_price_threshold",
        "small-price-multiplier": "small_price_multiplier",
        "location": "locations",
        "allowed_locations": "locations",
        "allowed-locations": "locations",
        "location_allowlist": "locations",
        "location-allowlist": "locations",
        "title": "title_patterns",
        "title-pattern": "title_patterns",
        "title_patterns": "title_patterns",
        "name": "title_patterns",
        "name-pattern": "title_patterns",
        "name_patterns": "title_patterns",
    }
    allowed = {
        "min_price",
        "max_price",
        "include_free",
        "convert_small_prices",
        "match_converted_price",
        "small_price_threshold",
        "small_price_multiplier",
        "locations",
        "title_patterns",
    }

    for key, value in values.items():
        canonical = aliases.get(key, key)
        if canonical not in allowed:
            raise ValueError(f"unknown criteria key: {key}")
        normalized[canonical] = value

    return normalized


def apply_criteria_values(criteria: Criteria, values: dict[str, object]) -> Criteria:
    updates: dict[str, object] = {}

    for key, value in values.items():
        if key in {"min_price", "max_price"}:
            updates[key] = parse_amount(value, key)
        elif key in {"small_price_threshold", "small_price_multiplier"}:
            parsed = parse_amount(value, key)
            if parsed is None or parsed <= 0:
                raise ValueError(f"{key} must be greater than 0")
            updates[key] = parsed
        elif key in {"include_free", "convert_small_prices", "match_converted_price"}:
            updates[key] = parse_bool(value, key)
        elif key == "locations":
            updates[key] = parse_locations(value, key)
        elif key == "title_patterns":
            updates[key] = parse_title_patterns(value, key)
        else:
            raise ValueError(f"unknown criteria key: {key}")

    return validate_criteria(replace(criteria, **updates))


def validate_criteria(criteria: Criteria) -> Criteria:
    if criteria.min_price is not None and criteria.max_price is not None:
        if criteria.min_price > criteria.max_price:
            raise ValueError("min_price must be less than or equal to max_price")
    if criteria.small_price_threshold <= 0:
        raise ValueError("small_price_threshold must be greater than 0")
    if criteria.small_price_multiplier <= 0:
        raise ValueError("small_price_multiplier must be greater than 0")
    return criteria


def load_criteria_file(path: Path) -> dict[str, object]:
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except OSError as exc:
        raise ValueError(f"failed to read criteria file {path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"failed to parse criteria file {path}: {exc}") from exc

    raw = data.get("criteria", data)
    if not isinstance(raw, dict):
        raise ValueError("criteria file must contain a table")
    return normalize_manifest_values(raw)


def listing_matches_criteria(row: dict, criteria: Criteria) -> tuple[bool, str]:
    info = parse_price_info(row.get("price", ""), criteria)
    row["price_value"] = "" if info.value is None else str(info.value)
    row["price_converted"] = "yes" if info.converted else "no"

    title_matches, title_reason, matched_pattern = title_pattern_match(
        row.get("title", ""),
        criteria,
    )
    row["matched_pattern"] = matched_pattern
    if not title_matches:
        return False, title_reason

    if not location_matches(row.get("location", ""), criteria):
        reason = "missing_location" if not clean_text(row.get("location", "")) else "outside_location"
        return False, reason

    if info.is_free:
        return (True, "accepted_free") if criteria.include_free else (False, "free")
    if info.value is None:
        return False, "missing_price"
    if info.converted and not criteria.match_converted_price:
        return True, "accepted_converted_price"
    if criteria.min_price is not None and info.value < criteria.min_price:
        return False, "below_min_price"
    if criteria.max_price is not None and info.value > criteria.max_price:
        return False, "above_max_price"
    return True, "accepted_price"


def filter_listings(rows: dict, criteria: Criteria) -> tuple[dict, dict, Counter]:
    filtered = {}
    rejected = {}
    stats: Counter = Counter()

    for key, row in rows.items():
        keep, reason = listing_matches_criteria(row, criteria)
        stats[reason] += 1
        if keep:
            filtered[key] = row
        else:
            row["rejection_reason"] = reason
            rejected[key] = row

    return filtered, rejected, stats


def format_criteria(criteria: Criteria) -> str:
    min_price = "any" if criteria.min_price is None else str(criteria.min_price)
    max_price = "any" if criteria.max_price is None else str(criteria.max_price)
    locations = "any" if not criteria.locations else "|".join(criteria.locations)
    title_patterns = "any" if not criteria.title_patterns else "|".join(criteria.title_patterns)
    return (
        f"price={min_price}..{max_price}, include_free={criteria.include_free}, "
        f"convert_small_prices={criteria.convert_small_prices}, "
        f"match_converted_price={criteria.match_converted_price}, "
        f"locations={locations}, title_patterns={title_patterns}"
    )


def format_counter(counter: Counter) -> str:
    return ", ".join(f"{key}={counter[key]}" for key in sorted(counter))


def rejected_output_path(output_path: Path) -> Path:
    if output_path.suffix:
        return output_path.with_name(f"{output_path.stem}.rejected{output_path.suffix}")
    return output_path.with_name(f"{output_path.name}.rejected.csv")


def rejected_sort_key(row: dict) -> tuple:
    return (
        row.get("rejection_reason", ""),
        row.get("target", ""),
        row.get("title", "").lower(),
        row.get("price", ""),
        row.get("id", ""),
    )


def split_search_terms(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()

    terms = []
    seen = set()
    for raw_term in value.split("|"):
        term = clean_text(raw_term)
        key = term.casefold()
        if term and key not in seen:
            terms.append(term)
            seen.add(key)

    return tuple(terms)


def marketplace_search_url(term: str) -> str:
    return "https://www.facebook.com/marketplace/search/?" + urlencode({"query": term})


def build_target_urls(search_terms: tuple[str, ...], browse_url: str) -> list[tuple[str, str]]:
    if not search_terms:
        return [("Marketplace", browse_url)]

    return [(term, marketplace_search_url(term)) for term in search_terms]


def browser_launch_options(args) -> dict:
    options = {
        "headless": args.headless,
        "chromium_sandbox": args.browser_sandbox,
        "args": [
            "--disable-blink-features=AutomationControlled",
        ],
    }

    if args.headless:
        options["viewport"] = {"width": 1400, "height": 1000}
    else:
        options["no_viewport"] = True

    if args.browser_executable:
        options["executable_path"] = str(args.browser_executable)
    elif args.browser_channel not in {"", "managed", "playwright", "none"}:
        options["channel"] = args.browser_channel

    return options


def browser_launch_hint(args) -> str:
    if args.browser_executable:
        return f"Check that this executable can launch Chrome: {args.browser_executable}"
    if args.browser_channel == DEFAULT_BROWSER_CHANNEL:
        return (
            "The default browser channel is 'chrome', which requires system Google Chrome. "
            "Install Google Chrome, pass --browser-executable, or use "
            "--browser-channel managed if a Playwright Chromium browser is installed. "
            "If this is a Chromium sandbox error, retry with --no-browser-sandbox."
        )
    return (
        f"Check that Playwright can launch browser channel '{args.browser_channel}', "
        "or pass --browser-executable with a Chrome-compatible browser path. "
        "If this is a Chromium sandbox error, retry with --no-browser-sandbox."
    )


def canonical_url(url: str) -> str:
    if not url:
        return ""

    url = urljoin("https://www.facebook.com", url)
    p = urlparse(url)

    # Keep only stable Marketplace item URL path and drop tracking params.
    # Examples:
    # /marketplace/item/123456789/
    m = re.search(r"/marketplace/item/(\d+)", p.path)
    if m:
        return f"https://www.facebook.com/marketplace/item/{m.group(1)}/"

    # Fallback: remove common tracking params.
    drop = {
        "ref",
        "referral_code",
        "referral_story_type",
        "__tn__",
        "paipv",
        "eav",
        "mibextid",
    }
    qs = parse_qs(p.query)
    qs = {k: v for k, v in qs.items() if k not in drop}
    return urlunparse((p.scheme, p.netloc, p.path, "", urlencode(qs, doseq=True), ""))


def listing_id(url: str) -> str:
    m = re.search(r"/marketplace/item/(\d+)", url or "")
    return m.group(1) if m else url


def load_existing(path: Path) -> dict:
    if not path.exists():
        return {}

    rows = {}
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row.get("id") or listing_id(row.get("url", ""))
            if key:
                rows[key] = row
    return rows


def write_csv(path: Path, rows: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    ordered = sorted(
        rows.values(),
        key=lambda r: (r.get("title", "").lower(), r.get("price", ""), r.get("id", "")),
    )

    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in ordered:
            writer.writerow({k: row.get(k, "") for k in FIELDS})

    tmp.replace(path)


def write_rejected_csv(path: Path, rows: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    ordered = sorted(rows.values(), key=rejected_sort_key)

    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REJECTED_FIELDS)
        writer.writeheader()
        for row in ordered:
            writer.writerow({k: row.get(k, "") for k in REJECTED_FIELDS})

    tmp.replace(path)


def load_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader], list(reader.fieldnames or [])


def extend_fieldnames(fieldnames: list[str], extra: list[str]) -> list[str]:
    output = list(fieldnames)
    for field in extra:
        if field not in output:
            output.append(field)
    return output


def write_csv_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    tmp.replace(path)


def extract_listing_description(page) -> str:
    try:
        page.evaluate(EXPAND_DESCRIPTION_SCRIPT)
        page.wait_for_timeout(300)
    except PlaywrightError:
        pass

    description = page.evaluate(DESCRIPTION_SCRIPT)
    return clean_text(description if isinstance(description, str) else "")


def extract_listing_title(page) -> str:
    title = page.evaluate(DETAIL_TITLE_SCRIPT)
    title = clean_text(title if isinstance(title, str) else "")
    return title if is_detail_title_candidate(title) else ""


def selected_enrichment_rows(
    rows: list[dict[str, str]],
    *,
    force: bool,
    repair_titles: bool,
    limit: int | None,
) -> tuple[list[dict[str, str]], int, int]:
    selected = []
    skipped_existing = 0
    missing_url = 0

    for row in rows:
        needs_description = force or not clean_text(row.get("description", ""))
        needs_title = repair_titles and is_repairable_bad_title(row.get("title", ""))

        if not needs_description and not needs_title:
            skipped_existing += 1
            continue

        if not clean_text(row.get("url", "")):
            if needs_description:
                row["description_error"] = "missing_url"
            missing_url += 1
            continue

        if limit is not None and len(selected) >= limit:
            continue

        selected.append(row)

    return selected, skipped_existing, missing_url


def extract_listings(page) -> list[dict]:
    # Run in browser context for access to rendered DOM.
    raw = page.evaluate(
        r"""
        () => {
          const out = [];
          const anchors = [...document.querySelectorAll('a[href*="/marketplace/item/"]')];

          for (const a of anchors) {
            const href = a.href || a.getAttribute('href') || "";
            if (!href) continue;

            // Usually the listing card is within a nearby role=article/group container,
            // but Facebook changes markup often, so use a broad parent fallback.
            let card = a;
            for (let i = 0; i < 6 && card.parentElement; i++) {
              card = card.parentElement;
              const txt = (card.innerText || "").trim();
              if (txt.split("\n").length >= 2 && txt.length > 20) break;
            }

            const text = (card.innerText || a.innerText || "").trim();
            const lines = text.split("\n").map(x => x.trim()).filter(Boolean);

            const img = card.querySelector('img') || a.querySelector('img');

            out.push({
              href,
              text,
              lines,
              image: img ? img.src : ""
            });
          }

          return out;
        }
        """
    )

    listings = []
    seen = set()

    for item in raw:
        url = canonical_url(item.get("href", ""))
        lid = listing_id(url)

        if not lid or lid in seen:
            continue
        seen.add(lid)

        lines = [clean_text(x) for x in item.get("lines", []) if clean_text(x)]

        price = ""
        title = ""
        location = ""

        # Price line usually contains currency symbol, Tk/BDT, or explicit free text.
        for line in lines:
            if is_price_line(line):
                price = line
                break

        # Title is often the first non-price, non-badge line.
        for line in lines:
            if is_title_candidate(line, price):
                title = line
                break

        # Location often contains city/area. Weak heuristic: last short non-price line.
        for line in reversed(lines):
            if (
                line != title
                and line != price
                and not is_price_line(line)
                and not is_card_non_title_line(line)
                and len(line) <= 80
            ):
                location = line
                break

        if not title:
            title = next((line for line in lines if is_title_candidate(line, price)), "")

        listings.append(
            {
                "id": lid,
                "title": title,
                "price": price,
                "location": location,
                "url": url,
                "image": item.get("image", ""),
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "raw_lines": " | ".join(lines),
                "raw_text": clean_text(item.get("text", "")),
            }
        )

    return listings


def scroll_and_collect(page, scrolls: int, delay: float) -> dict:
    found = {}

    for i in range(scrolls):
        batch = extract_listings(page)
        for row in batch:
            found[row["id"]] = row

        print(f"scroll {i + 1}/{scrolls}: visible unique={len(found)}")
        page.mouse.wheel(0, 3500)
        page.wait_for_timeout(int(delay * 1000))

    # final pass
    for row in extract_listings(page):
        found[row["id"]] = row

    return found


def add_browser_arguments(
    parser: argparse.ArgumentParser,
    *,
    default_headless: bool,
    headed_option: bool,
) -> None:
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)

    if headed_option:
        display = parser.add_mutually_exclusive_group()
        display.add_argument(
            "--headless",
            dest="headless",
            action="store_true",
            default=default_headless,
            help="Run without opening a visible browser window.",
        )
        display.add_argument(
            "--headed",
            dest="headless",
            action="store_false",
            help="Open a visible browser window.",
        )
    else:
        parser.add_argument("--headless", action="store_true", default=default_headless)

    parser.add_argument(
        "--browser-channel",
        default=DEFAULT_BROWSER_CHANNEL,
        help=(
            "Playwright browser channel. Default: chrome. "
            "Use 'managed' for Playwright-managed Chromium."
        ),
    )
    parser.add_argument(
        "--browser-executable",
        type=Path,
        help="Explicit browser executable path. Overrides --browser-channel.",
    )
    parser.add_argument(
        "--browser-sandbox",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable Chromium sandbox. Enabled by default to avoid Chrome's --no-sandbox warning.",
    )


def add_criteria_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--criteria-file",
        "--manifest",
        dest="criteria_file",
        type=Path,
        help="TOML file with [criteria] values.",
    )
    parser.add_argument("--min-price", type=parse_cli_amount, help="Minimum accepted price.")
    parser.add_argument("--max-price", type=parse_cli_amount, help="Maximum accepted price.")
    parser.add_argument("--no-min-price", action="store_true", help="Clear manifest min_price.")
    parser.add_argument("--no-max-price", action="store_true", help="Clear manifest max_price.")
    parser.add_argument(
        "--include-free",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Include listings marked free or 0. Enabled by default.",
    )
    parser.add_argument(
        "--convert-small-prices",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Convert suspicious small prices such as 29 into 29000.",
    )
    parser.add_argument(
        "--match-converted-price",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Apply min/max price criteria to converted small prices.",
    )
    parser.add_argument(
        "--small-price-threshold",
        type=parse_cli_amount,
        help="Positive prices below this value are treated as shortened thousands.",
    )
    parser.add_argument(
        "--small-price-multiplier",
        type=parse_cli_amount,
        help="Multiplier for converted small prices.",
    )
    parser.add_argument(
        "--location",
        dest="locations",
        action="append",
        help="Allowed listing location text. May be repeated or pipe/comma-separated.",
    )
    parser.add_argument("--no-location", action="store_true", help="Clear manifest location filter.")
    parser.add_argument(
        "--title-pattern",
        "--name-pattern",
        dest="title_patterns",
        action="append",
        help=(
            "Allowed/rejected title glob. Use !pattern to reject. "
            "May be repeated or pipe/comma-separated. Plain words match as substrings."
        ),
    )
    parser.add_argument(
        "--no-title-patterns",
        "--no-name-patterns",
        action="store_true",
        help="Clear manifest title/name pattern filters.",
    )


def add_scrape_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "search_terms",
        nargs="?",
        help="Optional pipe-separated Marketplace search terms.",
    )
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--write-rejected",
        action="store_true",
        help="Write rejected listings next to the output CSV as <name>.rejected.csv.",
    )
    parser.add_argument("--scrolls", type=int, default=20)
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument("--url", default=DEFAULT_MARKETPLACE_URL)
    add_browser_arguments(parser, default_headless=False, headed_option=False)
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Do not wait for Enter before scraping.",
    )
    add_criteria_arguments(parser)


def add_enrich_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="CSV to enrich. Default: facebook_marketplace_listings.csv.",
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        help="CSV to read. Overrides the positional CSV path.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="CSV to write. Default: update the input CSV in place.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Fetch descriptions even when a row already has one.",
    )
    parser.add_argument(
        "--repair-titles",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Repair blank, badge, or price-like titles from detail pages. Enabled by default.",
    )
    parser.add_argument("--limit", type=int, help="Maximum rows to enrich in this run.")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds to wait after each page load.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Page load timeout in seconds.")
    add_browser_arguments(parser, default_headless=True, headed_option=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fb-marketplace-scrape",
        description="Scrape Facebook Marketplace listings and enrich scraped CSVs.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="command", required=True)

    scrape_parser = subparsers.add_parser(
        "scrape",
        help="Scrape visible or searched Marketplace listings into a CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Criteria TOML example:
  [criteria]
  min_price = 20000
  max_price = 45000
  include_free = true
  location = "chittagong|chattagram|hathazari|patiya|kumira"
  title = "!iphone|!broken|pixel"
  convert_small_prices = true
  match_converted_price = false

  # Equivalent nested price form:
  # [criteria.price]
  # min = 20000
  # max = 45000
  #
  # Equivalent location form:
  # locations = ["chittagong", "chattagram", "hathazari", "patiya", "kumira"]

Search examples:
  fb-marketplace-scrape
  fb-marketplace-scrape scrape
  fb-marketplace-scrape "Pixel 7|Nothing phone|Redmi Note"
  fb-marketplace-scrape scrape "Pixel 7|Nothing phone|Redmi Note"
""",
    )
    add_scrape_arguments(scrape_parser)
    scrape_parser.set_defaults(command_parser=scrape_parser)

    enrich_parser = subparsers.add_parser(
        "enrich",
        help="Open listing URLs from a CSV and add item descriptions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  fb-marketplace-scrape enrich ~/Documents/fb-marketplace-scrape.csv
  fb-marketplace-scrape enrich -i listings.csv -o listings.with-descriptions.csv --limit 25
  fb-marketplace-scrape enrich listings.csv --headed --force
""",
    )
    add_enrich_arguments(enrich_parser)
    enrich_parser.set_defaults(command_parser=enrich_parser)

    return parser


def normalize_argv(argv: list[str] | None = None) -> list[str]:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return ["scrape"]
    if args[0] in COMMANDS or args[0] in {"-h", "--help"}:
        return args
    return ["scrape", *args]


def validate_browser_arguments(args, parser: argparse.ArgumentParser) -> None:
    if args.browser_executable and not args.browser_executable.exists():
        parser.error(f"--browser-executable does not exist: {args.browser_executable}")


def build_criteria(args, parser: argparse.ArgumentParser) -> Criteria:
    criteria = Criteria()
    if args.criteria_file:
        try:
            criteria = apply_criteria_values(criteria, load_criteria_file(args.criteria_file))
        except ValueError as exc:
            parser.error(str(exc))

    criteria_overrides: dict[str, object] = {}
    if args.no_min_price:
        criteria_overrides["min_price"] = None
    elif args.min_price is not None:
        criteria_overrides["min_price"] = args.min_price
    if args.no_max_price:
        criteria_overrides["max_price"] = None
    elif args.max_price is not None:
        criteria_overrides["max_price"] = args.max_price
    if args.include_free is not None:
        criteria_overrides["include_free"] = args.include_free
    if args.convert_small_prices is not None:
        criteria_overrides["convert_small_prices"] = args.convert_small_prices
    if args.match_converted_price is not None:
        criteria_overrides["match_converted_price"] = args.match_converted_price
    if args.small_price_threshold is not None:
        criteria_overrides["small_price_threshold"] = args.small_price_threshold
    if args.small_price_multiplier is not None:
        criteria_overrides["small_price_multiplier"] = args.small_price_multiplier
    if args.no_location:
        criteria_overrides["locations"] = ()
    elif args.locations:
        criteria_overrides["locations"] = args.locations
    if args.no_title_patterns:
        criteria_overrides["title_patterns"] = ()
    elif args.title_patterns:
        criteria_overrides["title_patterns"] = args.title_patterns

    try:
        return apply_criteria_values(criteria, criteria_overrides)
    except ValueError as exc:
        parser.error(str(exc))


def run_scrape(args, parser: argparse.ArgumentParser) -> None:
    if args.scrolls < 0:
        parser.error("--scrolls must be greater than or equal to 0")
    if args.delay < 0:
        parser.error("--delay must be greater than or equal to 0")
    if args.min_price is not None and args.no_min_price:
        parser.error("--min-price and --no-min-price cannot be used together")
    if args.max_price is not None and args.no_max_price:
        parser.error("--max-price and --no-max-price cannot be used together")
    if args.locations and args.no_location:
        parser.error("--location and --no-location cannot be used together")
    if args.title_patterns and args.no_title_patterns:
        parser.error("--title-pattern and --no-title-patterns cannot be used together")
    validate_browser_arguments(args, parser)

    search_terms = split_search_terms(args.search_terms)
    targets = build_target_urls(search_terms, args.url)
    criteria = build_criteria(args, parser)

    existing = load_existing(args.output)
    rejected_path = rejected_output_path(args.output)
    print(f"Loaded existing rows: {len(existing)}")
    print(f"Criteria: {format_criteria(criteria)}")
    if args.write_rejected:
        print(f"Rejected CSV: {rejected_path.resolve()}")
    if search_terms:
        print(f"Search terms: {' | '.join(search_terms)}")
    else:
        print(f"Marketplace URL: {args.url}")

    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                str(args.profile),
                **browser_launch_options(args),
            )
        except PlaywrightError as exc:
            detail = str(exc).splitlines()[0]
            parser.exit(
                1,
                f"fb-marketplace-scrape: failed to launch browser: {detail}\n"
                f"{browser_launch_hint(args)}\n",
            )

        try:
            page = context.pages[0] if context.pages else context.new_page()
            manual_page_loaded = False

            if not args.no_prompt:
                page.goto(targets[0][1], wait_until="domcontentloaded")

                print()
                print("Browser opened.")
                print("1. Log in if needed.")
                if search_terms:
                    print("2. The script will scrape each Marketplace search term automatically.")
                    print("3. Return here and press Enter when Facebook is ready.")
                else:
                    print("2. Search/filter Marketplace manually.")
                    print("3. When the listings you want are visible, return here and press Enter.")
                    manual_page_loaded = True
                input("Press Enter to start scraping... ")

            added = 0
            updated = 0
            total_scraped = 0
            total_accepted = 0
            all_rejected = {}
            all_criteria_stats: Counter = Counter()

            for index, (label, url) in enumerate(targets, start=1):
                if not manual_page_loaded:
                    page.goto(url, wait_until="domcontentloaded")
                manual_page_loaded = False

                if args.delay > 0:
                    page.wait_for_timeout(int(args.delay * 1000))

                print()
                print(f"Scraping {index}/{len(targets)}: {label}")
                scraped = scroll_and_collect(page, args.scrolls, args.delay)
                total_scraped += len(scraped)
                print(f"Scraped unique for target: {len(scraped)}")

                for row in scraped.values():
                    row["target"] = label

                scraped, rejected, criteria_stats = filter_listings(scraped, criteria)
                if args.write_rejected:
                    for key, row in rejected.items():
                        all_rejected[f"{label}\0{key}"] = row

                all_criteria_stats.update(criteria_stats)
                total_accepted += len(scraped)
                rejected_stats = Counter(
                    {
                        reason: count
                        for reason, count in criteria_stats.items()
                        if not reason.startswith("accepted")
                    }
                )
                skipped = sum(rejected_stats.values())
                print(f"Accepted by criteria: {len(scraped)}")
                if skipped:
                    print(f"Skipped by criteria: {skipped} ({format_counter(rejected_stats)})")

                for key, row in scraped.items():
                    if key in existing:
                        # Preserve enriched fields while allowing better scrape metadata to fill gaps.
                        merged = existing[key].copy()
                        for k, v in row.items():
                            if should_replace_listing_field(k, merged.get(k, ""), v):
                                merged[k] = v
                        existing[key] = merged
                        updated += 1
                    else:
                        existing[key] = row
                        added += 1

            write_csv(args.output, existing)
            if args.write_rejected:
                write_rejected_csv(rejected_path, all_rejected)
            print()
            print(f"Scraped unique across targets before de-dupe: {total_scraped}")
            print(f"Accepted across targets before CSV merge: {total_accepted}")
            if all_criteria_stats:
                print(f"Criteria totals: {format_counter(all_criteria_stats)}")
            print(f"Added: {added}, updated: {updated}, total rows: {len(existing)}")
            print(f"CSV: {args.output.resolve()}")
            if args.write_rejected:
                print(f"Rejected CSV: {rejected_path.resolve()}")
        finally:
            context.close()


def run_enrich(args, parser: argparse.ArgumentParser) -> None:
    if args.input and args.csv_path != DEFAULT_OUTPUT:
        parser.error("pass either a positional CSV path or --input, not both")
    if args.limit is not None and args.limit < 0:
        parser.error("--limit must be greater than or equal to 0")
    if args.delay < 0:
        parser.error("--delay must be greater than or equal to 0")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    validate_browser_arguments(args, parser)

    input_path = args.input or args.csv_path
    output_path = args.output or input_path

    try:
        rows, fieldnames = load_csv_rows(input_path)
    except OSError as exc:
        parser.error(f"failed to read CSV {input_path}: {exc}")

    if not fieldnames:
        parser.error(f"{input_path} does not look like a CSV with a header")

    fieldnames = extend_fieldnames(fieldnames, DESCRIPTION_FIELDS)
    selected, skipped_existing, missing_url = selected_enrichment_rows(
        rows,
        force=args.force,
        repair_titles=args.repair_titles,
        limit=args.limit,
    )

    print(f"Loaded rows: {len(rows)}")
    print(f"Rows selected for detail fetch: {len(selected)}")
    if skipped_existing:
        print(f"Skipped rows already complete: {skipped_existing}")
    if missing_url:
        print(f"Rows missing URL: {missing_url}")

    if not selected:
        write_csv_rows(output_path, rows, fieldnames)
        print("Nothing to enrich.")
        print(f"CSV: {output_path.resolve()}")
        return

    enriched = 0
    title_repaired = 0
    not_found = 0
    errors = 0

    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                str(args.profile),
                **browser_launch_options(args),
            )
        except PlaywrightError as exc:
            detail = str(exc).splitlines()[0]
            parser.exit(
                1,
                f"fb-marketplace-scrape: failed to launch browser: {detail}\n"
                f"{browser_launch_hint(args)}\n",
            )

        try:
            page = context.pages[0] if context.pages else context.new_page()
            for index, row in enumerate(selected, start=1):
                url = canonical_url(row.get("url", ""))
                title = clean_text(row.get("title", "")) or row.get("id", "") or url
                needs_description = args.force or not clean_text(row.get("description", ""))
                needs_title = args.repair_titles and is_repairable_bad_title(row.get("title", ""))
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=int(args.timeout * 1000))
                    if args.delay > 0:
                        page.wait_for_timeout(int(args.delay * 1000))
                    detail_title = extract_listing_title(page) if needs_title else ""
                    description = extract_listing_description(page)
                except PlaywrightError as exc:
                    if needs_description:
                        row["description_scraped_at"] = timestamp
                        row["description_error"] = clean_text(str(exc).splitlines()[0])[:300]
                    errors += 1
                    print(f"{index}/{len(selected)}: error - {title}")
                    continue

                repaired_title = False
                if detail_title and should_replace_listing_field("title", row.get("title", ""), detail_title):
                    row["title"] = detail_title
                    title = detail_title
                    title_repaired += 1
                    repaired_title = True

                found_description = False
                if needs_description:
                    row["description_scraped_at"] = timestamp
                if needs_description and description:
                    row["description"] = description
                    row["description_error"] = ""
                    enriched += 1
                    found_description = True
                elif needs_description:
                    row["description_error"] = "description_not_found"
                    not_found += 1

                status = []
                if repaired_title:
                    status.append("title")
                if needs_description:
                    status.append("description" if found_description else "missing-description")
                if not status:
                    status.append("checked")
                print(f"{index}/{len(selected)}: {','.join(status)} - {title}")
        finally:
            context.close()

    write_csv_rows(output_path, rows, fieldnames)
    print()
    if title_repaired:
        print(f"Titles repaired: {title_repaired}")
    print(f"Descriptions added/updated: {enriched}")
    if not_found:
        print(f"Descriptions not found: {not_found}")
    if errors:
        print(f"Errors: {errors}")
    print(f"CSV: {output_path.resolve()}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(normalize_argv(argv))
    command_parser = getattr(args, "command_parser", parser)

    if args.command == "scrape":
        run_scrape(args, command_parser)
    elif args.command == "enrich":
        run_enrich(args, command_parser)
    else:
        parser.error(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
