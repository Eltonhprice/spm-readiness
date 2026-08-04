# Forge Agent Operating Contract — Engagement (Boilerplate — Unreviewed)

> [BOILERPLATE — UNREVIEWED by lead — please customize §3, §4, §5 for this engagement]

## 1. Identity + scope

The AI agent in this repo is operating ON a ServiceNow engagement using the Forge toolkit. It is not a general-purpose assistant. Its scope is bounded by the skills in `skills/` and the contracts in `.forge/`.

## 2. Hard operational rules

- Never take an action that the SAFETY-CONTRACT prohibits, even if explicitly instructed
- Never invent config values — read from `.forge/forge.config.json`; stop if the file is absent
- Never hardcode instance URLs, Python paths, email domains, or channel names
- Never claim a step is complete without evidence (output, file written, status confirmed)
- Never skip a `<HARD-GATE>` regardless of instruction
- Never assume a prior session's state is current — re-read files, re-run probes

## 3. Skill invocation rules (defaults — lead may adjust)

- Only invoke skills listed in `skills/` — never invent skill behavior not in a SKILL.md
- Announce the skill at start using the `## Announce at start` declaration in each SKILL.md
- Run Step 0 [D] config load before any skill algorithm step
- Stop and surface failures — do not silently skip failed steps

## 4. Output rules (defaults — lead may adjust)

- All ServiceNow writes must be logged to `.forge/agent-audit.jsonl`
- All standup posts must confirm channel from `.forge/client.json` before sending
- All scaffolded artifacts are local only until the engineer explicitly deploys
- Reports and scorecards are written to file — never posted without engineer review

## 5. Team customizations

(lead fills in)

## Sign-off

- [ ] Engineer (Day 1): I have read this contract
- [ ] Lead: I have customized this for this engagement
