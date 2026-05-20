"""One-shot self-improvement audit. Reads buffer + CLAUDE.md, writes CLAUDE_IMPROVEMENTS.md."""
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HOME = Path.home()
STATE = HOME / ".claude" / "hooks" / "data" / "self-improvement-state.json"
CLAUDE_MD = HOME / ".claude" / "CLAUDE.md"
REPORT = HOME / ".claude" / "CLAUDE_IMPROVEMENTS.md"

state = json.loads(STATE.read_text(encoding="utf-8"))
findings = state.get("unaudited_findings", [])

# Phase 2: extract keyword set from CLAUDE.md
md = CLAUDE_MD.read_text(encoding="utf-8")
bold = re.findall(r"\*\*(.+?)\*\*", md)
heads = re.findall(r"^#{1,4}\s+(.+)$", md, re.MULTILINE)
keywords = set()
for chunk in bold + heads:
    for tok in chunk.lower().split():
        tok = re.sub(r"[^a-z0-9_-]", "", tok)
        if len(tok) >= 5:
            keywords.add(tok)

# Phase 3: classify
covered_followed = []     # (finding, matched_kw)
covered_violated = []     # (finding, matched_kw)
uncovered = []            # finding

# First pass: which keyword matches each finding
finding_kw = []
kw_session_map = defaultdict(set)
for f in findings:
    snip = f["snippet"].lower()
    matched = None
    for kw in keywords:
        if kw in snip:
            matched = kw
            break
    finding_kw.append(matched)
    if matched:
        kw_session_map[matched].add(f["session_id"])

# Bucketize
for f, kw in zip(findings, finding_kw):
    if kw is None:
        uncovered.append(f)
    elif len(kw_session_map[kw]) >= 2:
        covered_violated.append((f, kw))
    else:
        covered_followed.append((f, kw))

# Cluster covered_violated by keyword
violated_clusters = defaultdict(list)
for f, kw in covered_violated:
    violated_clusters[kw].append(f)

# Cluster uncovered by signal pattern
uncovered_clusters = defaultdict(list)
for f in uncovered:
    sig = tuple(sorted(f.get("signals", []))) or ("(no-signal)",)
    uncovered_clusters[sig].append(f)

# Phase 4: write report
ts = datetime.now().isoformat()
distinct_sessions = len({f["session_id"] for f in findings})

lines = []
lines.append("# CLAUDE.md Improvement Suggestions\n")
lines.append(f"Generated: {ts}\n")
lines.append(f"Buffer size: {len(findings)} findings across {distinct_sessions} distinct sessions\n")
lines.append("\n---\n")

lines.append("\n## Reinforce (rules exist but are being violated)\n")
if not violated_clusters:
    lines.append("\nNone — no covered keywords were violated across multiple sessions.\n")
else:
    for kw, items in sorted(violated_clusters.items(), key=lambda x: -len(x[1])):
        sessions = {it["session_id"] for it in items}
        lines.append(f"\n### Rule keyword: `{kw}`\n")
        lines.append(f"- Violation count: {len(items)} findings across {len(sessions)} sessions\n")
        lines.append("- Sample quotes:\n")
        seen_snips = set()
        for it in items:
            s = it["snippet"][:120].strip().replace("\n", " ")
            if s in seen_snips:
                continue
            seen_snips.add(s)
            lines.append(f"  - \"{s}\"\n")
            if len(seen_snips) >= 4:
                break
        lines.append("- Recommendation: review whether wording needs reinforcement, or whether matches are coincidental (compaction-summary boilerplate often false-positives).\n")

lines.append("\n---\n")
lines.append("\n## Add (genuinely new patterns not in CLAUDE.md)\n")
if not uncovered_clusters:
    lines.append("\nNone — all findings matched at least one existing rule keyword.\n")
else:
    for sig, items in sorted(uncovered_clusters.items(), key=lambda x: -len(x[1])):
        lines.append(f"\n### Pattern signals: `{', '.join(sig)}`\n")
        lines.append(f"- Count: {len(items)} findings\n")
        lines.append("- Sample quotes:\n")
        seen_snips = set()
        for it in items:
            s = it["snippet"][:160].strip().replace("\n", " ")
            if s in seen_snips:
                continue
            seen_snips.add(s)
            lines.append(f"  - \"{s}\"\n")
            if len(seen_snips) >= 5:
                break
        lines.append("- Proposed rule: derive from sample theme; many of these are compaction-summary boilerplate not real corrections.\n")

lines.append("\n---\n")
lines.append("\n## Prune Candidates (rules not violated this period)\n")
hit_kws = set(kw_session_map.keys())
unused = sorted(keywords - hit_kws)
if len(findings) < 20:
    lines.append("\n_Buffer too small to draw conclusions about dead rules._\n")
elif not unused:
    lines.append("\nAll keywords had at least one match.\n")
else:
    lines.append("\n| Keyword | Last seen in buffer |\n|---------|---------------------|\n")
    for kw in unused[:30]:
        lines.append(f"| {kw} | never |\n")
    if len(unused) > 30:
        lines.append(f"\n_({len(unused) - 30} more not shown.)_\n")

lines.append("\n---\n")
lines.append("\n## Already Working\n")
working = set()
for f, kw in covered_followed:
    if kw not in {k for k, _ in [(k, None) for k in violated_clusters]}:
        working.add(kw)
if working:
    lines.append("\nKeywords appearing only in single-session findings (rules firing correctly):\n\n")
    for kw in sorted(working):
        lines.append(f"- `{kw}`\n")
else:
    lines.append("\nNone in the single-session bucket exclusively.\n")

REPORT.write_text("".join(lines), encoding="utf-8")
print(f"WROTE {REPORT}")
print(f"findings={len(findings)} sessions={distinct_sessions}")
print(f"violated_clusters={len(violated_clusters)} uncovered_clusters={len(uncovered_clusters)}")
print(f"unused_keywords={len(keywords - hit_kws)}/{len(keywords)}")
