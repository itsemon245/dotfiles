#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "playwright",
# ]
# ///
"""Scrape all visible Marketplace listing gallery images for CSV rows.

Temporary helper for a narrow Facebook Marketplace candidate list. It reuses the
same persistent Playwright profile as the maintained fb-marketplace-scrape tool.
"""

from __future__ import annotations

import argparse
import csv
import mimetypes
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse


DEFAULT_INPUT = Path.home() / "Documents/fb-marketplace/trimmed-candidates.csv"
DEFAULT_PROFILE = Path.home() / ".local/share/fb-marketplace-profile"
DEFAULT_BROWSER_CHANNEL = "chrome"
IMAGE_URL_SEPARATOR = "|"


MAIN_IMAGE_SCRIPT = r"""
() => {
  const mediaRe = /(scontent|fbcdn|fbsbx|lookaside)/i;
  const badAltRe = /(profile picture|avatar|map|emoji|sticker|icon)/i;
  const clean = value => (value || "").replace(/\s+/g, " ").trim();
  const srcsetBest = srcset => {
    if (!srcset) return "";
    const parsed = srcset.split(",")
      .map(item => {
        const parts = item.trim().split(/\s+/);
        const url = parts[0] || "";
        const descriptor = parts[1] || "";
        const width = descriptor.endsWith("w") ? Number.parseInt(descriptor, 10) : 0;
        const scale = descriptor.endsWith("x") ? Number.parseFloat(descriptor) * 1000 : 0;
        return { url, score: width || scale || 1 };
      })
      .filter(item => item.url);
    parsed.sort((a, b) => b.score - a.score);
    return parsed[0]?.url || "";
  };
  const absolutize = value => {
    try {
      return new URL(value, document.location.href).href;
    } catch (_) {
      return "";
    }
  };
  const visible = rect => (
    rect.width >= 80 &&
    rect.height >= 80 &&
    rect.bottom > 90 &&
    rect.right > 0 &&
    rect.top < window.innerHeight &&
    rect.left < window.innerWidth
  );
  const candidates = [];

  for (const img of document.querySelectorAll("img")) {
    const rect = img.getBoundingClientRect();
    if (!visible(rect)) continue;
    const alt = clean(img.alt || img.getAttribute("aria-label") || "");
    if (badAltRe.test(alt)) continue;

    const src = absolutize(srcsetBest(img.srcset) || img.currentSrc || img.src || "");
    if (!src || !mediaRe.test(src) || src.startsWith("blob:") || src.startsWith("data:")) continue;

    const area = rect.width * rect.height;
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const naturalArea = (img.naturalWidth || 0) * (img.naturalHeight || 0);
    const leftMediaBonus = centerX < window.innerWidth * 0.78 ? 2 : 0.65;
    const upperPageBonus = centerY < window.innerHeight * 0.85 ? 1.4 : 0.4;
    const score = area * leftMediaBonus * upperPageBonus + naturalArea / 100;

    candidates.push({
      url: src,
      alt,
      width: Math.round(rect.width),
      height: Math.round(rect.height),
      naturalWidth: img.naturalWidth || 0,
      naturalHeight: img.naturalHeight || 0,
      x: Math.round(rect.left),
      y: Math.round(rect.top),
      source: "main_carousel",
      score,
    });
  }

  candidates.sort((a, b) => b.score - a.score);
  return candidates[0] || null;
}
"""


DOM_FALLBACK_IMAGES_SCRIPT = r"""
() => {
  const mediaRe = /(scontent|fbcdn|fbsbx|lookaside)/i;
  const badAltRe = /(profile picture|avatar|map|emoji|sticker|icon)/i;
  const clean = value => (value || "").replace(/\s+/g, " ").trim();
  const srcsetBest = srcset => {
    if (!srcset) return "";
    const parsed = srcset.split(",")
      .map(item => {
        const parts = item.trim().split(/\s+/);
        const url = parts[0] || "";
        const descriptor = parts[1] || "";
        const width = descriptor.endsWith("w") ? Number.parseInt(descriptor, 10) : 0;
        const scale = descriptor.endsWith("x") ? Number.parseFloat(descriptor) * 1000 : 0;
        return { url, score: width || scale || 1 };
      })
      .filter(item => item.url);
    parsed.sort((a, b) => b.score - a.score);
    return parsed[0]?.url || "";
  };
  const absolutize = value => {
    try {
      return new URL(value, document.location.href).href;
    } catch (_) {
      return "";
    }
  };
  const images = [];

  for (const img of document.querySelectorAll("img")) {
    const rect = img.getBoundingClientRect();
    if (rect.width < 70 || rect.height < 70) continue;
    if (rect.bottom < 90 || rect.top > window.innerHeight * 0.94) continue;
    if (rect.left > window.innerWidth * 0.82) continue;

    const alt = clean(img.alt || img.getAttribute("aria-label") || "");
    if (badAltRe.test(alt)) continue;

    const src = absolutize(srcsetBest(img.srcset) || img.currentSrc || img.src || "");
    if (!src || !mediaRe.test(src) || src.startsWith("blob:") || src.startsWith("data:")) continue;

    images.push({
      url: src,
      alt,
      width: Math.round(rect.width),
      height: Math.round(rect.height),
      naturalWidth: img.naturalWidth || 0,
      naturalHeight: img.naturalHeight || 0,
      x: Math.round(rect.left),
      y: Math.round(rect.top),
      source: "dom_fallback",
    });
  }

  return images;
}
"""


CLICK_NEXT_SCRIPT = r"""
() => {
  const labelRe = /(next|next photo|পরবর্তী|আগামী|ডান)/i;
  const visible = rect => (
    rect.width >= 20 &&
    rect.height >= 20 &&
    rect.bottom > 90 &&
    rect.top < window.innerHeight * 0.92 &&
    rect.right > 0 &&
    rect.left < window.innerWidth
  );
  const textOf = node => [
    node.getAttribute("aria-label") || "",
    node.getAttribute("title") || "",
    node.innerText || "",
    node.textContent || "",
  ].join(" ").replace(/\s+/g, " ").trim();

  const controls = [...document.querySelectorAll('button, [role="button"], [aria-label]')]
    .map(node => ({ node, rect: node.getBoundingClientRect(), text: textOf(node) }))
    .filter(item => visible(item.rect));

  let candidates = controls.filter(item => labelRe.test(item.text));

  if (!candidates.length) {
    const images = [...document.querySelectorAll("img")]
      .map(node => ({ node, rect: node.getBoundingClientRect() }))
      .filter(item => item.rect.width >= 180 && item.rect.height >= 180)
      .sort((a, b) => (b.rect.width * b.rect.height) - (a.rect.width * a.rect.height));
    const main = images[0]?.rect;
    if (main) {
      candidates = controls.filter(item => {
        const centerX = item.rect.left + item.rect.width / 2;
        const centerY = item.rect.top + item.rect.height / 2;
        return (
          centerX >= main.left + main.width * 0.62 &&
          centerX <= main.right + 90 &&
          centerY >= main.top &&
          centerY <= main.bottom
        );
      });
    }
  }

  candidates.sort((a, b) => b.rect.left - a.rect.left);
  const next = candidates[0];
  if (!next) return { clicked: false, label: "" };

  next.node.click();
  return { clicked: true, label: next.text };
}
"""


@dataclass
class ImageCandidate:
    url: str
    alt: str = ""
    width: int = 0
    height: int = 0
    natural_width: int = 0
    natural_height: int = 0
    source: str = ""
    local_path: str = ""


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}.images.csv")


def default_image_rows_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}.image-rows.csv")


def canonical_url(url: str) -> str:
    if not url:
        return ""

    url = urljoin("https://www.facebook.com", url)
    parsed = urlparse(url)
    match = re.search(r"/marketplace/item/(\d+)", parsed.path)
    if match:
        return f"https://www.facebook.com/marketplace/item/{match.group(1)}/"

    drop = {"ref", "referral_code", "referral_story_type", "__tn__", "paipv", "eav", "mibextid"}
    query = parse_qs(parsed.query)
    query = {key: value for key, value in query.items() if key not in drop}
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query, doseq=True), ""))


def listing_id_from_row(row: dict[str, str], fallback_index: int) -> str:
    row_id = clean_text(row.get("id"))
    if row_id:
        return re.sub(r"\W+", "_", row_id).strip("_")

    match = re.search(r"/marketplace/item/(\d+)", row.get("url", ""))
    if match:
        return match.group(1)

    return f"row_{fallback_index:03d}"


def image_fingerprint(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.netloc}{parsed.path}"


def image_extension(content_type: str, url: str) -> str:
    guessed = mimetypes.guess_extension((content_type or "").split(";", 1)[0].strip())
    if guessed:
        return ".jpg" if guessed == ".jpe" else guessed

    path_suffix = Path(urlparse(url).path).suffix.lower()
    if path_suffix in {".jpg", ".jpeg", ".png", ".webp", ".avif"}:
        return path_suffix

    return ".jpg"


def row_label(row: dict[str, str], fallback: str) -> str:
    return clean_text(row.get("title")) or clean_text(row.get("id")) or fallback


def load_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = list(reader.fieldnames or [])
        return [dict(row) for row in reader], fieldnames


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def append_fields(fieldnames: list[str], extra: list[str]) -> list[str]:
    merged = list(fieldnames)
    for field in extra:
        if field not in merged:
            merged.append(field)
    return merged


def candidate_from_js(value: dict | None) -> ImageCandidate | None:
    if not value or not value.get("url"):
        return None

    return ImageCandidate(
        url=value["url"],
        alt=clean_text(value.get("alt", "")),
        width=int(value.get("width") or 0),
        height=int(value.get("height") or 0),
        natural_width=int(value.get("naturalWidth") or 0),
        natural_height=int(value.get("naturalHeight") or 0),
        source=clean_text(value.get("source", "")),
    )


def add_candidate(
    images: dict[str, ImageCandidate],
    candidate: ImageCandidate | None,
) -> bool:
    if not candidate:
        return False

    fingerprint = image_fingerprint(candidate.url)
    existing = images.get(fingerprint)
    if not existing:
        images[fingerprint] = candidate
        return True

    existing_area = max(existing.width * existing.height, existing.natural_width * existing.natural_height)
    candidate_area = max(candidate.width * candidate.height, candidate.natural_width * candidate.natural_height)
    if candidate_area > existing_area:
        images[fingerprint] = candidate
        return True

    return False


def scrape_gallery_images(page, *, max_images: int, step_delay: float) -> list[ImageCandidate]:
    images: dict[str, ImageCandidate] = {}
    first_seen = ""
    unchanged_clicks = 0

    for step in range(max_images):
        candidate = candidate_from_js(page.evaluate(MAIN_IMAGE_SCRIPT))
        added = add_candidate(images, candidate)

        if step == 0 and candidate:
            first_seen = image_fingerprint(candidate.url)

        clicked = page.evaluate(CLICK_NEXT_SCRIPT)
        if not clicked.get("clicked"):
            break

        page.wait_for_timeout(int(step_delay * 1000))
        next_candidate = candidate_from_js(page.evaluate(MAIN_IMAGE_SCRIPT))
        next_fingerprint = image_fingerprint(next_candidate.url) if next_candidate else ""
        if next_fingerprint == first_seen and len(images) > 1:
            break

        if not next_fingerprint or (candidate and next_fingerprint == image_fingerprint(candidate.url)):
            unchanged_clicks += 1
        else:
            unchanged_clicks = 0

        if unchanged_clicks >= 2 and not added:
            break

    for value in page.evaluate(DOM_FALLBACK_IMAGES_SCRIPT):
        add_candidate(images, candidate_from_js(value))

    return list(images.values())


def download_image(context, image: ImageCandidate, destination: Path) -> str:
    response = context.request.get(image.url, timeout=30_000)
    if not response.ok:
        raise RuntimeError(f"HTTP {response.status}")

    extension = image_extension(response.headers.get("content-type", ""), image.url)
    final_destination = destination.with_suffix(extension)
    final_destination.parent.mkdir(parents=True, exist_ok=True)
    final_destination.write_bytes(response.body())
    return str(final_destination)


def browser_launch_options(args: argparse.Namespace) -> dict:
    options = {
        "headless": args.headless,
        "chromium_sandbox": args.browser_sandbox,
        "args": ["--disable-blink-features=AutomationControlled"],
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


def browser_launch_hint(args: argparse.Namespace) -> str:
    if args.browser_executable:
        return f"Check that this executable can launch Chrome: {args.browser_executable}"
    if args.browser_channel == DEFAULT_BROWSER_CHANNEL:
        return (
            "The default browser channel is 'chrome', which requires system Google Chrome. "
            "Install Google Chrome, pass --browser-executable, or use "
            "--browser-channel managed if a Playwright Chromium browser is installed. "
            "If this is a profile-lock issue, close the existing scraper browser first."
        )
    return (
        f"Check that Playwright can launch browser channel '{args.browser_channel}', "
        "or pass --browser-executable with a Chrome-compatible browser path."
    )


def add_browser_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)

    display = parser.add_mutually_exclusive_group()
    display.add_argument(
        "--headed",
        dest="headless",
        action="store_false",
        default=False,
        help="Open a visible browser window. Default.",
    )
    display.add_argument(
        "--headless",
        dest="headless",
        action="store_true",
        help="Run without opening a visible browser window.",
    )

    parser.add_argument(
        "--browser-channel",
        default=DEFAULT_BROWSER_CHANNEL,
        help="Playwright browser channel. Default: chrome. Use 'managed' for Playwright-managed Chromium.",
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
        help="Enable Chromium sandbox. Enabled by default.",
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape every Marketplace gallery image URL for rows in a candidate CSV.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Candidate CSV. Default: {DEFAULT_INPUT}",
    )
    parser.add_argument("-o", "--output", type=Path, help="Output CSV. Default: <input>.images.csv")
    parser.add_argument(
        "--image-rows-output",
        type=Path,
        help="One-row-per-image CSV. Default: <input>.image-rows.csv",
    )
    parser.add_argument("--download-dir", type=Path, help="Optional directory to save image files.")
    parser.add_argument("--limit", type=int, help="Only scrape the first N rows.")
    parser.add_argument("--force", action="store_true", help="Rescrape rows that already have image_urls.")
    parser.add_argument("--pause-first", action="store_true", help="Open the first listing and wait for Enter before scraping.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Navigation timeout in seconds. Default: 30.")
    parser.add_argument("--delay", type=float, default=0.8, help="Delay after page load/clicks in seconds. Default: 0.8.")
    parser.add_argument("--max-images", type=int, default=20, help="Maximum carousel clicks per listing. Default: 20.")
    add_browser_arguments(parser)

    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 0:
        parser.error("--limit must be greater than or equal to 0")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    if args.delay < 0:
        parser.error("--delay must be greater than or equal to 0")
    if args.max_images <= 0:
        parser.error("--max-images must be greater than 0")
    if args.browser_executable and not args.browser_executable.exists():
        parser.error(f"--browser-executable does not exist: {args.browser_executable}")

    args.input = args.input.expanduser()
    args.output = (args.output.expanduser() if args.output else default_output_path(args.input))
    args.image_rows_output = (
        args.image_rows_output.expanduser()
        if args.image_rows_output
        else default_image_rows_path(args.input)
    )
    if args.download_dir:
        args.download_dir = args.download_dir.expanduser()

    return args


def run(args: argparse.Namespace) -> int:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        print(
            "fb-marketplace-scrape-images: missing Python dependency: playwright\n"
            "Run this script directly so uv can install inline dependencies:\n"
            f"  {Path(__file__)}",
            file=sys.stderr,
        )
        return 127

    try:
        rows, input_fields = load_csv(args.input)
    except OSError as exc:
        print(f"fb-marketplace-scrape-images: failed to read CSV {args.input}: {exc}", file=sys.stderr)
        return 1

    if not input_fields:
        print(f"fb-marketplace-scrape-images: CSV has no header: {args.input}", file=sys.stderr)
        return 1
    if "url" not in input_fields:
        print(f"fb-marketplace-scrape-images: CSV is missing required column: url", file=sys.stderr)
        return 1

    candidates = rows[: args.limit] if args.limit is not None else rows
    selected = [
        (index, row)
        for index, row in enumerate(candidates, start=1)
        if args.force or not clean_text(row.get("image_urls"))
    ]

    output_fields = append_fields(
        input_fields,
        ["image_count", "image_urls", "image_local_paths", "images_scraped_at", "image_scrape_error"],
    )
    image_row_fields = [
        "listing_row",
        "id",
        "title",
        "price",
        "location",
        "url",
        "image_index",
        "image_url",
        "local_path",
        "source",
        "width",
        "height",
        "natural_width",
        "natural_height",
        "alt",
        "scraped_at",
        "error",
    ]
    image_rows: list[dict[str, str]] = []

    print(f"Loaded rows: {len(rows)}")
    print(f"Rows selected for image scrape: {len(selected)}")
    print(f"Profile: {args.profile}")

    if not selected:
        write_csv(args.output, rows, output_fields)
        write_csv(args.image_rows_output, image_rows, image_row_fields)
        print("Nothing to scrape.")
        print(f"CSV: {args.output.resolve()}")
        print(f"Image rows CSV: {args.image_rows_output.resolve()}")
        return 0

    with sync_playwright() as playwright:
        try:
            context = playwright.chromium.launch_persistent_context(
                str(args.profile),
                **browser_launch_options(args),
            )
        except PlaywrightError as exc:
            detail = str(exc).splitlines()[0]
            print(
                f"fb-marketplace-scrape-images: failed to launch browser: {detail}\n"
                f"{browser_launch_hint(args)}",
                file=sys.stderr,
            )
            return 1

        try:
            page = context.pages[0] if context.pages else context.new_page()

            if args.pause_first and selected:
                first_url = canonical_url(selected[0][1].get("url", ""))
                if first_url:
                    page.goto(first_url, wait_until="domcontentloaded", timeout=int(args.timeout * 1000))
                input("Browser opened. Log in if needed, then press Enter to start scraping... ")

            for selected_index, (row_number, row) in enumerate(selected, start=1):
                url = canonical_url(row.get("url", ""))
                title = row_label(row, url)
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

                if not url:
                    row["image_count"] = "0"
                    row["image_urls"] = ""
                    row["image_local_paths"] = ""
                    row["images_scraped_at"] = timestamp
                    row["image_scrape_error"] = "missing_url"
                    print(f"{selected_index}/{len(selected)}: missing-url - {title}")
                    continue

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=int(args.timeout * 1000))
                    if args.delay > 0:
                        page.wait_for_timeout(int(args.delay * 1000))
                    page.wait_for_selector("img", timeout=int(args.timeout * 1000))
                    images = scrape_gallery_images(page, max_images=args.max_images, step_delay=args.delay)
                except PlaywrightError as exc:
                    row["image_count"] = "0"
                    row["image_urls"] = ""
                    row["image_local_paths"] = ""
                    row["images_scraped_at"] = timestamp
                    row["image_scrape_error"] = clean_text(str(exc).splitlines()[0])[:300]
                    print(f"{selected_index}/{len(selected)}: error - {title}")
                    continue

                local_paths: list[str] = []
                listing_id = listing_id_from_row(row, row_number)
                for image_index, image in enumerate(images, start=1):
                    error = ""
                    if args.download_dir:
                        destination = args.download_dir / listing_id / f"{image_index:02d}"
                        try:
                            image.local_path = download_image(context, image, destination)
                            local_paths.append(image.local_path)
                        except Exception as exc:  # noqa: BLE001 - keep per-image download failures in CSV.
                            error = clean_text(str(exc))[:300]

                    image_rows.append(
                        {
                            "listing_row": str(row_number),
                            "id": row.get("id", ""),
                            "title": row.get("title", ""),
                            "price": row.get("price", ""),
                            "location": row.get("location", ""),
                            "url": url,
                            "image_index": str(image_index),
                            "image_url": image.url,
                            "local_path": image.local_path,
                            "source": image.source,
                            "width": str(image.width),
                            "height": str(image.height),
                            "natural_width": str(image.natural_width),
                            "natural_height": str(image.natural_height),
                            "alt": image.alt,
                            "scraped_at": timestamp,
                            "error": error,
                        }
                    )

                row["image_count"] = str(len(images))
                row["image_urls"] = IMAGE_URL_SEPARATOR.join(image.url for image in images)
                row["image_local_paths"] = IMAGE_URL_SEPARATOR.join(local_paths)
                row["images_scraped_at"] = timestamp
                row["image_scrape_error"] = "" if images else "images_not_found"

                print(f"{selected_index}/{len(selected)}: {len(images)} images - {title}")
        finally:
            context.close()

    write_csv(args.output, rows, output_fields)
    write_csv(args.image_rows_output, image_rows, image_row_fields)

    print()
    print(f"CSV: {args.output.resolve()}")
    print(f"Image rows CSV: {args.image_rows_output.resolve()}")
    if args.download_dir:
        print(f"Downloaded images: {args.download_dir.resolve()}")

    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
