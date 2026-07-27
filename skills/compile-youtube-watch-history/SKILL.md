---
name: compile-youtube-watch-history
description: Compile a requested month of YouTube watch history from a signed-in Chrome session into dated UTF-8 Markdown drafts under outputs/YYYY/MM, excluding YouTube Music, deduplicating repeated views, validating links and formatting, and reporting extraction limits. Use when asked to collect, review, or later confirmation-gate the upload of a monthly YouTube watch-history archive for the lestrrat/watch-history repository.
---

# Compile YouTube Watch History

## Overview

Collect a requested calendar month from the signed-in Chrome session, normalize it into one Markdown draft per date, and validate the local result. Keep drafting, upload preparation, and committing as separate phases with explicit user approval between them.

Use the bundled validator at [scripts/validate_watch_history.py](scripts/validate_watch_history.py) after drafting and again after review.

## Phase selection

- Enter **draft phase** for a request naming a month and year or asking to compile watch history.
- Enter **upload-preparation phase** only when the user says the local files are ready and explicitly asks to upload them.
- Enter **commit phase** only after the user replies exactly `proceed` to the upload-preparation confirmation.
- Stop after each phase's required report or confirmation request.
- Never infer approval from a scheduled run, an earlier request, or an informal acknowledgement.

## Draft phase

### Set the target

1. Require an explicit month and four-digit year. Resolve `[MONTH] [YEAR]` placeholders before browsing.
2. Use the browser or system local time zone for date grouping. Do not convert displayed local dates through UTC.
3. Write drafts only below `outputs/YYYY/MM/` in the current repository.
4. Check whether target files already exist. Do not overwrite existing drafts or possible user edits without explicit direction.

### Collect history

1. Use the user's signed-in Chrome session. Do not request, copy, or persist cookies, tokens, or passwords.
2. Open YouTube watch history at `https://www.youtube.com/feed/history`.
3. Load history until activity older than the first day of the requested month is visible. This proves that the month boundary was reached.
4. If the standard history page does not expose the complete requested month, open Google My Activity's YouTube history and load activity until both month boundaries are available.
5. Capture, for each candidate, the exact displayed title, source URL, watched timestamp or date, service label, and source order.
6. Exclude YouTube Music entries. Exclude `music.youtube.com`, YouTube Music service labels, and records that cannot be confirmed as YouTube video activity.
7. Keep records whose watched timestamp falls in the requested month after conversion to the browser's local time zone. If only a date is available, use that date and report the missing time precision.
8. Continue loading until the requested range is complete or the source stops yielding older activity. Report any unverified boundary or extraction limit.

If the signed-in browser session or a usable browser control is unavailable, stop and report that limitation. Do not substitute unauthenticated scraping, guessed data, or exported credentials.

### Normalize and deduplicate

1. Normalize each video to `https://www.youtube.com/watch?v=VIDEO_ID`.
2. Extract `VIDEO_ID` from YouTube watch, shorts, live, or `youtu.be` source URLs. Remove timestamps, tracking parameters, playlist parameters, and other query parameters.
3. Preserve the exact title text. Escape Markdown syntax only when needed to render that exact title safely.
4. Group records by local calendar date.
5. Within each date, deduplicate by video ID and keep the newest occurrence. Keep the retained entries in newest-to-oldest watch order. If exact times are unavailable, preserve source order and report that limitation.

### Write drafts

Create one UTF-8 file for every calendar date in the requested month, including dates with no qualifying entries. Use `outputs/YYYY/MM/YYYYMMDD.md` and write this structure:

```markdown
# Monday, June 1, 2026

[← Previous](YYYYMMDD.md) | [Next →](YYYYMMDD.md)

## YouTube

1. [Exact video title](https://www.youtube.com/watch?v=VIDEO_ID)
1. [Another exact title](https://www.youtube.com/watch?v=VIDEO_ID)
```

Apply these rules:

- Render the heading with the English weekday and month name, with no zero-padded day.
- Include `[← Previous](relative-link)` only when the previous calendar date's daily file exists.
- Include `[Next →](relative-link)` only when the next calendar date's daily file exists.
- Use links relative to the current daily file. Cross-month links use paths such as `../06/20260630.md`.
- Keep `## YouTube` even when that date has no entries.
- Make every video marker exactly `1.`.
- Include only the title and canonical URL in each entry. Do not include uploader, channel, runtime, view count, watch time, or extra labels.

Create `outputs/YYYY/MM/README.md` containing only chronological date links, one per line:

```markdown
- [2026-06-01](20260601.md)
- [2026-06-02](20260602.md)
```

Do not add a title, prose, summary, or blank separator to the monthly README.

### Validate and report

Run the draft validator from the repository root:

```bash
python3 skills/compile-youtube-watch-history/scripts/validate_watch_history.py outputs/YYYY/MM --mode draft
```

Fix every validation error and rerun it. Then manually confirm that the browser source was fully loaded, YouTube Music was excluded, titles were copied exactly, and the local-time date boundaries are supported.

Report all of the following, then stop:

- Draft folder.
- Daily file count, including empty-date files.
- Total retained video-entry count after per-date deduplication.
- Dates with no qualifying entries.
- Missing or unverified date ranges.
- Extraction limitations, including unavailable timestamps or incomplete browser history.

Do not upload, commit, or alter remote state during draft phase.

## Upload-preparation phase

Start this phase only after the user says the files are ready and asks to upload them.

1. Re-read every file under the local `outputs/YYYY/MM/` folder. Treat the current files as authoritative.
2. Preserve every user edit and deletion. Do not regenerate entries, restore deleted files, normalize titles again, or recreate missing dates.
3. Run the reviewed-file validator:

   ```bash
   python3 skills/compile-youtube-watch-history/scripts/validate_watch_history.py outputs/YYYY/MM --mode reviewed
   ```

4. Report validation errors and stop if any exist. Missing daily files are reported as intentional review differences and are not restored.
5. Confirm the target is the `lestrrat/watch-history` GitHub repository, the `main` branch, and directory `YYYY/MM`. Keep `main` selected.
6. Use the signed-in GitHub web interface to upload or stage only the reviewed daily files that still exist and the reviewed `README.md`. Do not stage the local `outputs/` directory itself.
7. Fill an appropriate commit message describing the month, for example `Add June 2026 YouTube watch history`.
8. Show the staged file count and the exact target filenames.
9. Stop and ask for final confirmation using the exact command word `proceed`.

Do not click **Commit changes**, create a commit, or push during this phase.

## Commit phase

Enter this phase only when the user explicitly replies `proceed`.

1. Re-read the staged filenames and commit message.
2. Verify that only the reviewed daily files and monthly README are staged under `YYYY/MM`.
3. Commit through the same GitHub workflow used for staging.
4. Wait for GitHub processing to complete.
5. Verify the resulting commit and report its link.

Never delete remote files, rewrite Git history, force-push, or treat a scheduled run as commit approval.

## Validation helper

Use `scripts/validate_watch_history.py` as the mechanical check for:

- `YYYY/MM/YYYYMMDD.md` filenames and valid calendar dates.
- Exact English date headings.
- Previous and next links when adjacent daily files exist.
- Strict UTF-8 decoding.
- A `## YouTube` section with only title-and-canonical-URL entries.
- YouTube watch URLs with only the `v` query parameter.
- `1.` numbering for every video entry.
- A monthly README containing only chronological links to the daily files.
- Per-date duplicate video IDs.

Use `--mode draft` to require every calendar date's file. Use `--mode reviewed` to allow intentional deleted dates while still validating all remaining files.
