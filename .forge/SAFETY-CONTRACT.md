# Forge Safety Contract — Engagement (Boilerplate — Unreviewed)

> [BOILERPLATE — UNREVIEWED by lead — please customize §2, §3, §5 for this engagement]

## 1. Hard prohibitions
- Never delete records on production instances
- Never push to production without verbatim `confirm production deploy {scope}`
- Never include customer PII, credentials, or tokens in chat / commits / posts
- Never modify OOB records without lead approval
- Never create scoped apps in global scope
- Never auto-deploy from non-main branch

## 2. Confirmation gates (defaults — lead may adjust)
- Bulk ops > 10 records
- ACL / business rule / shared script changes
- Multi-scope changes in one action
- Deploys to non-dev instances
- Cross-team artifact changes

## 3. Allowed without confirmation (defaults — lead may adjust)
- Read-only queries against dev
- Local file edits
- now-sdk build + install to dev
- Posting to engagement channel via /forge-standup
- Tests

## 4. Audit
- Mutations log to .forge/agent-audit.jsonl
- Lead reviews weekly

## 5. Team customizations
(lead fills in)

## Sign-off
- [ ] Engineer (Day 1): I have read this contract
- [ ] Lead: I have customized this for this engagement
