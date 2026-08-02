# Workmen's Diary

A diary logging work changes — covering both the `Training` repo (where this diary lives) and the `Constistant` repo, since most work spans both repos — used to record who did what, what changed, and when, so that whoever picks up the work next (or a new Claude session) can read it and immediately understand the background without having to trawl through `git log` or ask again.

> Moved to the root of the `Training` repo on 2026-07-07 (previously lived in the `Constistant` repo) — see the July 7 entry for the reason.

## Writing rules

1. **Write in English.** Every entry in this diary is written in English — the diary was fully converted from Thai to English on 2026-08-02, and the parallel `en/` translation folder that used to sit alongside it was deleted at the same time (it had fallen out of date after 2026-07-21, so one English source of truth beats two folders that disagree). Do not start a Thai entry and translate it later; write it in English the first time.
   - **Keep verbatim, do not translate:** Thai filenames and paths (`หน้า25_beam_plan.json`, `สิ่งที่ต้องแก้.md`, `json_แก้ไขแล้ว/`, `rawjson_ยังไม่ได้แก้ไขโดนคน/`, house folder names like `บ้าน_เล็ก_2ชั้น_03`), and Thai text quoted **from a drawing or from JSON data** (`"ป.Ø6มม.@0.20"`, `"หยุดที่ L/8"`, `ตอม่อ/ฐานราก`). Those are identifiers and data values — translating them breaks the link back to the real file or the real drawing.
   - Only the surrounding prose is English.
2. **Filename = date, format `year-month-day.md`**, e.g. `2026-07-05.md`
3. **1 day = 1 file** — if more than one person works on that day, or work happens in multiple sessions, **open that day's existing file and append to it** (add a new entry to the same file). **Do not create a new file for a date that already has one.**
4. Each entry in the file must have complete information:
   - **Person's name** (or the name of the AI/session standing in for them, e.g. "Claude — session with Makham")
   - **Date** (can repeat the filename's date, included for clarity when reading files individually)
   - **Time** (actual start/end time, or the time range worked)
   - **Detailed account of what changed** — not just a broad heading; must specify:
     - Which file/folder was edited/created/moved/deleted (give the full path)
     - What changed from what to what (if a value was changed)
     - The reason for the change (why it was done)
     - Impact/things to watch out for going forward (if any)
     - Work still pending/unfinished (if any — note it so the next person can read it and continue)

## Template for a new entry

```markdown
## [time] Person's name

**Work done:**
- ...

**Files changed:**
- `path/to/file` — what changed, why

**Impact/precautions:**
- ...

**Left pending / to continue:**
- ...

---
```

## Usage example

- On 2026-07-05 Makham worked in the morning, then a friend continued in the afternoon of the same day → both write into the same `2026-07-05.md` file, as separate entries (separated by `---`)
- The next day (2026-07-06) someone continues the work → create a new file `2026-07-06.md`

## Why this diary exists

Git commit messages are too short to explain the context/reasoning behind each change, especially work that spans multiple people/repos (e.g. Constistant and Training) — this diary keeps the "why" and "what to watch out for next" that `git log` can't tell you.
