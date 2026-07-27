#!/usr/bin/env python3
"""Validate monthly YouTube watch-history Markdown drafts."""

from __future__ import annotations

import argparse
import calendar
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


DAILY_FILE_RE = re.compile(r"(?P<date>\d{8})\.md\Z")
README_LINE_RE = re.compile(r"- \[(?P<label>\d{4}-\d{2}-\d{2})\]\((?P<file>\d{8})\.md\)\Z")
NAV_RE = re.compile(
    r"^(?:(?:\[← Previous\]\((?P<previous>[^)]+)\))(?: \| )?)?"
    r"(?:\[Next →\]\((?P<next>[^)]+)\))?\Z"
)
ENTRY_RE = re.compile(
    r"^1\. \[(?P<title>.*)\]\(https://www\.youtube\.com/watch\?v=(?P<video_id>[A-Za-z0-9_-]{11})\)\Z"
)
NUMBERED_LINE_RE = re.compile(r"^\d+\.\s")
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}\Z")
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def add_error(errors: list[str], message: str) -> None:
    errors.append(message)


def add_warning(warnings: list[str], message: str) -> None:
    warnings.append(message)


def read_utf8(path: Path, errors: list[str]) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        add_error(errors, f"{path}: invalid UTF-8 ({exc})")
    except OSError as exc:
        add_error(errors, f"{path}: cannot read file ({exc})")
    return None


def parse_target(month_dir: Path, errors: list[str]) -> tuple[int, int] | None:
    month_text = month_dir.name
    year_text = month_dir.parent.name
    if not re.fullmatch(r"\d{2}", month_text) or not re.fullmatch(r"\d{4}", year_text):
        add_error(errors, f"target must end in YYYY/MM, got {month_dir}")
        return None

    year = int(year_text)
    month = int(month_text)
    if not 1 <= month <= 12:
        add_error(errors, f"invalid month directory: {month_dir}")
        return None
    return year, month


def expected_heading(day: date) -> str:
    return f"# {WEEKDAYS[day.weekday()]}, {MONTHS[day.month - 1]} {day.day}, {day.year}"


def daily_path(output_root: Path, day: date) -> Path:
    return output_root / f"{day.year:04d}" / f"{day.month:02d}" / f"{day:%Y%m%d}.md"


def relative_daily_link(month_dir: Path, output_root: Path, day: date) -> str:
    return Path(os.path.relpath(daily_path(output_root, day), month_dir)).as_posix()


def validate_url(url: str, path: Path, line_number: int, errors: list[str]) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "www.youtube.com" or parsed.path != "/watch":
        add_error(errors, f"{path}:{line_number}: non-canonical YouTube URL: {url}")
        return

    query = parse_qs(parsed.query, keep_blank_values=True)
    video_ids = query.get("v", [])
    if set(query) != {"v"} or len(video_ids) != 1 or not VIDEO_ID_RE.fullmatch(video_ids[0]):
        add_error(errors, f"{path}:{line_number}: URL must contain only a valid v parameter: {url}")


def validate_readme(
    month_dir: Path,
    year: int,
    month: int,
    daily_files: dict[date, Path],
    errors: list[str],
) -> None:
    readme = month_dir / "README.md"
    text = read_utf8(readme, errors)
    if text is None:
        return

    linked_dates: list[date] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = README_LINE_RE.fullmatch(line)
        if not match:
            add_error(errors, f"{readme}:{line_number}: README must contain only date links")
            continue

        try:
            linked_date = date.fromisoformat(match.group("label"))
        except ValueError:
            add_error(errors, f"{readme}:{line_number}: invalid date label")
            continue

        filename_date = match.group("file")
        if linked_date.strftime("%Y%m%d") != filename_date:
            add_error(errors, f"{readme}:{line_number}: date label and filename disagree")
        if (linked_date.year, linked_date.month) != (year, month):
            add_error(errors, f"{readme}:{line_number}: README link is outside the requested month")
        linked_dates.append(linked_date)

    if linked_dates != sorted(linked_dates):
        add_error(errors, f"{readme}: date links are not chronological")
    if len(linked_dates) != len(set(linked_dates)):
        add_error(errors, f"{readme}: duplicate date links")

    expected_dates = sorted(daily_files)
    if linked_dates != expected_dates:
        add_error(errors, f"{readme}: links do not exactly match the daily files")


def validate_daily_file(
    path: Path,
    day: date,
    month_dir: Path,
    output_root: Path,
    repository_root: Path | None,
    errors: list[str],
) -> int:
    text = read_utf8(path, errors)
    if text is None:
        return 0

    lines = text.splitlines()
    if not lines or lines[0] != expected_heading(day):
        add_error(errors, f"{path}: first line must be '{expected_heading(day)}'")

    youtube_positions = [index for index, line in enumerate(lines) if line == "## YouTube"]
    if len(youtube_positions) != 1:
        add_error(errors, f"{path}: must contain exactly one '## YouTube' heading")
        return 0

    youtube_position = youtube_positions[0]
    expected_navigation: list[str] = []
    previous_day = day - timedelta(days=1)
    next_day = day + timedelta(days=1)
    previous_path = daily_path(output_root, previous_day)
    next_path = daily_path(output_root, next_day)
    previous_repository_path = (
        daily_path(repository_root, previous_day) if repository_root is not None else None
    )
    next_repository_path = (
        daily_path(repository_root, next_day) if repository_root is not None else None
    )
    if previous_path.exists() or (
        previous_repository_path is not None and previous_repository_path.exists()
    ):
        expected_navigation.append(
            f"[← Previous]({relative_daily_link(month_dir, output_root, previous_day)})"
        )
    if next_path.exists() or (
        next_repository_path is not None and next_repository_path.exists()
    ):
        expected_navigation.append(f"[Next →]({relative_daily_link(month_dir, output_root, next_day)})")
    expected_navigation_line = " | ".join(expected_navigation)

    navigation_lines = []
    for index, line in enumerate(lines[:youtube_position]):
        navigation_match = NAV_RE.fullmatch(line)
        if navigation_match and (navigation_match.group("previous") or navigation_match.group("next")):
            navigation_lines.append((index, line))
    if len(navigation_lines) > 1:
        add_error(errors, f"{path}: multiple navigation lines")
    elif expected_navigation_line:
        if not navigation_lines or navigation_lines[0][1] != expected_navigation_line:
            add_error(errors, f"{path}: navigation links do not match adjacent files")
    elif navigation_lines:
        add_error(errors, f"{path}: navigation links point to missing adjacent files")

    for index, line in enumerate(lines[1:youtube_position], start=2):
        if not line.strip():
            continue
        if line != expected_navigation_line:
            add_error(errors, f"{path}:{index}: unexpected content before YouTube heading")

    entries = 0
    seen_video_ids: set[str] = set()
    for index, line in enumerate(lines[youtube_position + 1 :], start=youtube_position + 2):
        if not line.strip():
            continue
        match = ENTRY_RE.fullmatch(line)
        if not match:
            if NUMBERED_LINE_RE.match(line):
                add_error(errors, f"{path}:{index}: every video marker must be exactly '1.'")
            else:
                add_error(errors, f"{path}:{index}: expected a title and canonical YouTube URL")
            continue

        title = match.group("title")
        video_id = match.group("video_id")
        if not title:
            add_error(errors, f"{path}:{index}: title must not be empty")
        if video_id in seen_video_ids:
            add_error(errors, f"{path}:{index}: duplicate video ID within date: {video_id}")
        seen_video_ids.add(video_id)
        validate_url(
            f"https://www.youtube.com/watch?v={video_id}", path, index, errors
        )
        entries += 1

    return entries


def validate(month_dir: Path, mode: str, repository_root: Path | None = None) -> int:
    errors: list[str] = []
    warnings: list[str] = []
    month_dir = month_dir.resolve()
    if repository_root is not None:
        repository_root = repository_root.resolve()
    target = parse_target(month_dir, errors)
    if target is None:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    year, month = target
    output_root = month_dir.parents[1]
    all_dates = [date(year, month, day) for day in range(1, calendar.monthrange(year, month)[1] + 1)]

    daily_files: dict[date, Path] = {}
    for path in sorted(month_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        match = DAILY_FILE_RE.fullmatch(path.name)
        if not match:
            add_error(errors, f"{path}: unexpected Markdown filename")
            continue
        try:
            file_date = date(
                int(match.group("date")[:4]),
                int(match.group("date")[4:6]),
                int(match.group("date")[6:]),
            )
        except ValueError:
            add_error(errors, f"{path}: filename is not a valid calendar date")
            continue
        if (file_date.year, file_date.month) != (year, month):
            add_error(errors, f"{path}: filename is outside target month")
            continue
        daily_files[file_date] = path

    missing_files = [day for day in all_dates if day not in daily_files]
    if missing_files:
        message = "missing daily files: " + ", ".join(day.isoformat() for day in missing_files)
        if mode == "draft":
            add_error(errors, message)
        else:
            add_warning(warnings, message)

    validate_readme(month_dir, year, month, daily_files, errors)

    entry_counts: dict[date, int] = {}
    for day, path in sorted(daily_files.items()):
        entry_counts[day] = validate_daily_file(
            path,
            day,
            month_dir,
            output_root,
            repository_root,
            errors,
        )

    no_entry_dates = [day for day in all_dates if day in daily_files and entry_counts.get(day, 0) == 0]
    total_entries = sum(entry_counts.values())

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    print(f"Folder: {month_dir}")
    print(f"Daily files: {len(daily_files)}")
    print(f"Entries: {total_entries}")
    print(
        "No-entry dates: "
        + (", ".join(day.isoformat() for day in no_entry_dates) if no_entry_dates else "none")
    )
    print("Result: " + ("FAIL" if errors else "PASS"))
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("month_dir", type=Path, help="directory ending in YYYY/MM")
    parser.add_argument(
        "--mode",
        choices=("draft", "reviewed"),
        default="draft",
        help="require every calendar-date file in draft mode; allow reviewed deletions in reviewed mode",
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        help="repository root used to validate navigation across draft-month boundaries",
    )
    args = parser.parse_args()
    return validate(args.month_dir, args.mode, args.repository_root)


if __name__ == "__main__":
    raise SystemExit(main())
