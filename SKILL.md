---
name: self-improvement
description: Analyze accumulated correction signals from the unaudited buffer; propose CLAUDE.md rule additions, reinforcements, and prune candidates. Run when the SessionStart gate fires or when reviewing what went wrong.
allowed-tools: Read, Write, Bash, Grep, Glob
---

# Self-Improvement - Audit CLAUDE.md Against Accumulated Signals

Reads the pre-computed correction buffer (populated by `reflect_analyzer.py` after every session)
and classifies signals against current CLAUDE.md rules. No agent dispatch. No multi-MB jsonl reads.

## Phase 1: Read Unaudited Buffer

Read `~/.claude/hooks/data/self-improvement-state.json`.

Extract `unaudited_findings` list. If the list is empty, report:

> "No uncovered signals accumulated. Nothing to audit."

Then skip directly to Phase 6 (still reset state so `last_improvement_run` is updated).

Each finding has:
- `snippet` — first 200 chars of the user correction message
- `signals` — list of regex patterns that matched
- `session_id` — which session it came from
- `timestamp` — when it was recorded

## Phase 2: Read CLAUDE.md

Read `~/.claude/CLAUDE.md` fully.

Extract rule keywords:
- Bold phrases: regex `\*\*(.+?)\*\*` — lowercase each match, split on whitespace, keep tokens >= 5 chars
- Headings: regex `^#{1,4}\s+(.+)$` (multiline) — same lowercasing/splitting/filtering

Build a flat keyword set from all tokens.

## Phase 3: Classify Findings into 3 Buckets

For each finding in `unaudited_findings`:

**Covered check:** does any keyword from Phase 2 appear as a substring (case-insensitive) in the finding's `snippet`?

**Frequency check:** across ALL findings in the buffer, how many distinct `session_id` values contributed findings that match the same keyword?

Buckets:
1. **Covered & followed** — finding matches a keyword AND that keyword appears in fewer than 2 distinct sessions' findings in the buffer. Rule is working.
2. **Covered but violated repeatedly** — finding matches a keyword AND that keyword appears in >= 2 distinct sessions' findings. Rule exists but isn't landing.
3. **Uncovered** — finding matches no keyword. Genuinely new pattern not yet captured in CLAUDE.md.

## Phase 4: Write CLAUDE_IMPROVEMENTS.md

Create `~/.claude/CLAUDE_IMPROVEMENTS.md` (overwrite if exists) with this structure:

```markdown
# CLAUDE.md Improvement Suggestions

Generated: <ISO8601 timestamp>
Buffer size: <N> findings across <M> distinct sessions

---

## Reinforce (rules exist but are being violated)

For each "covered but violated repeatedly" cluster, group by matched keyword.

### Rule: "<matched keyword>"
- Violation count: N findings across M sessions
- Sample quotes:
  - "snippet 1 (truncated to 120 chars)"
  - "snippet 2"
- Recommendation: [reinforce wording / move to Critical Rules / accept as dead]

---

## Add (genuinely new patterns not in CLAUDE.md)

For each cluster of "uncovered" findings (group by similar signal patterns):

### Pattern: "<describe the common theme>"
- Count: N findings
- Sample quotes:
  - "snippet 1"
  - "snippet 2"
- Proposed rule text:
  > **[Rule name]** — [one-sentence rule derived from the pattern]

---

## Prune Candidates (rules not violated this period)

List rule keywords from Phase 2 that have ZERO matches anywhere in the buffer.
These are candidates for removal — but only meaningful if buffer has >= 20 findings.
If buffer < 20, add a caveat: "Buffer too small to draw conclusions about dead rules."

| Keyword | Last seen in buffer |
|---------|---------------------|
| keyword | never               |

---

## Already Working

Keywords that appear in the buffer AND are only in the "covered & followed" bucket.
These rules are firing correctly — don't change them.
```

**Do NOT apply changes** — write the file for user review only.

## Phase 5: Confirm Report on Disk

After writing, read back the first 5 lines of `~/.claude/CLAUDE_IMPROVEMENTS.md` to confirm
the file is on disk with content. If it is not present or empty, stop here and report the error.
Do NOT proceed to Phase 6.

## Phase 6: Reset State File

Write `~/.claude/hooks/data/self-improvement-state.json` with this exact shape:

```json
{
  "session_count": 0,
  "seen_session_ids": [],
  "last_improvement_run": "<ISO_8601_TIMESTAMP_NOW>",
  "unaudited_findings": []
}
```

- `unaudited_findings` MUST be reset to `[]`. This clears the buffer so new signals accumulate fresh.
- `seen_session_ids` MUST be reset to `[]`. The Stop-hook counter deduplicates on this list.
- `session_count` MUST be reset to `0`.
- `<ISO_8601_TIMESTAMP_NOW>` is the current datetime in ISO 8601 format (e.g. `2026-04-29T10:15:00.123456`). Do NOT use a UUID — the field must be a timestamp or the auto-reset logic in `reflect_analyzer.py` can't parse it.

Use the Write tool to overwrite the file. Only run this step AFTER the Phase 5 confirmation
that the report is on disk.

## Usage Examples

```
/self-improvement
```
