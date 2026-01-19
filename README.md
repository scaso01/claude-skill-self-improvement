# Self-Improving Claude Code

Claude analyzes its own conversation history, finds what went wrong, and tells you how to fix your `CLAUDE.md`.

```
Sessions → Friction patterns → Config updates → Better sessions
    ↑                                                 │
    └─────────────────────────────────────────────────┘
```

## What it does

1. Reads your `.jsonl` conversation files
2. Spawns parallel agents to find friction across sessions
3. Cross-references your existing CLAUDE.md and skills
4. Outputs concrete suggestions you can review and apply

## Install

```bash
git clone https://github.com/bokan/claude-skill-self-improvement ~/.claude/skills/self-improvement
```

## Usage

```
/self-improvement
/self-improvement last 3 days
/self-improvement refactoring
```

## Output

Generates `CLAUDE_IMPROVEMENTS.md`:

- Friction patterns ranked by frequency
- Suggested additions to your config
- What's already working (so you don't break it)
- Potential new skills worth building
- Raw quotes showing where things went sideways

You review. You apply what makes sense. Repeat.

## License

Apache 2.0
