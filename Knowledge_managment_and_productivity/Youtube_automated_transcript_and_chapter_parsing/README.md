# YouTube Transcript & Chapter Parser

> Fetches a YouTube video's chapters and transcript, merges them by timestamp, and exports the result as a clean Markdown file.

---

## Project Overview

- **Problem**: Watching a long YouTube video and wanting structured, searchable notes is tedious — scrubbing manually or copying auto-captions gives you a wall of unformatted text.
- **Type**: Automation / text processing utility
- **Approach**: Uses `yt-dlp` to extract chapter metadata and `youtube-transcript-api` to pull the auto-generated or manual transcript, then groups subtitle entries under their matching chapter headings by comparing timestamps.

---

## Objective

- Produce a well-structured Markdown file from any YouTube video with chapters and/or a transcript.
- Support optional auto-export to an Obsidian vault so notes land exactly where you want them.

---

## Dataset

| Field | Details |
|---|---|
| Source | YouTube (any public video URL) |
| Input | Video URL (hardcoded in `main.py` or passed via argument) |
| Output | `.md` file with chapter headings and timestamped subtitle lines |

---

## Methodology

1. **Chapter extraction** — `yt-dlp` fetches video metadata (no download) and returns chapter start/end times with titles.
2. **Transcript fetch** — `youtube-transcript-api` pulls the transcript in the specified language (default: English).
3. **Merging** — Each transcript entry's start time is compared against chapter boundaries; entries are placed under their matching chapter heading.
4. **Fallback** — If the video has no chapters, the full transcript is output under a single `## Full Transcript` section.
5. **Export** — Saved as `youtube_notes.md`; optionally moved to an Obsidian vault path via environment variable.

---

## Code Structure

```
Youtube_automated_transcript_and_chapter_parsing_HOBBY/
├── main.py          # All logic: fetch, merge, save
├── output_md/       # Sample output Markdown files
└── README.md
```

---

## Key Logic

The core merge loops over chapters in order, then scans the entire transcript for entries whose `start` timestamp falls within `[chapter.start_time, next_chapter.start_time)`. This is O(chapters × transcript_entries) — fine for typical video lengths. The fallback branch handles no-chapter videos by writing the entire transcript as a flat timestamped list.

---

## Results

This is a just a learning aid. Please note that the output quality depends on YouTube's auto-generated transcript accuracy.

---

## Limitations

- Transcript availability depends on YouTube; private or transcript-disabled videos will silently return an empty list with a printed warning.
- Language defaults to English (`"en"`); other languages require editing the `language` parameter in `get_transcript()`.
- Video URL is hardcoded in `main.py` — edit before each run (CLI argument support is a planned but unchecked item in the implementation plan).

---

## Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.x |
| Video metadata | yt-dlp |
| Transcript | youtube-transcript-api |
| Output | Standard library (`os`, `shutil`, `urllib.parse`) |

---

## How to Run

```bash
# 1. Install dependencies
pip install yt-dlp youtube-transcript-api

# 2. Edit the video URL in main.py
#    video_url = "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"

# 3. Run
python main.py

# Optional: auto-move output to Obsidian vault
OBSIDIAN_VAULT_PATH="/path/to/vault/Youtube Notes/notes.md" python main.py
```

---

## Business / Practical Value

Turns any YouTube video into structured Markdown notes in seconds — useful for anyone who takes notes in Obsidian or similar tools and wants to reference video content without rewatching.

---

## Author

Jayesh Bhat · [https://www.linkedin.com/in/jayeshbhat/] · [https://github.com/JRBhat]
