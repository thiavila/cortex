---
status: incomplete
---

# Codex task-board reminders

Implemented native Codex hook packaging and an opt-in standalone installer. User explicitly chose hooks with existing MD and memories unchanged. The adapter emits context on UserPromptSubmit and SessionStart startup/resume/compact; no task writes, transcript parsing, LLM calls or Stop continuations in the hook. The agent applies skill/board policy and current authorization.

The standalone installer preserves unrelated hooks, snapshots runtime files, backs up config, supports idempotent install/update/removal and recovery after interruption. It neither selects a board nor writes trust/config.toml. Shared installed skills have priority over the bundled fallback.

Verification: 48 Python tests + 6 Node tests passed, Claude plugin manifest validation passed with the existing root CLAUDE.md warning, git diff --check passed. Native package installed in isolated Codex home; hooks/list discovered both plugin hooks without warnings/errors, substituted PLUGIN_ROOT correctly. Installed standalone commands for prompt and compact payloads emitted the expected context/identity. Claude Opus final review approved; see REVIEW.md for hashes, usage and limitations.

Local installation completed, retaining existing GSD and voice hooks. Official hooks/list shows new handlers enabled but untrusted. **Required remaining step:** user reviews/trusts the two Cortex reminder definitions through Codex Settings > Hooks or /hooks. No trust hashes were forged and no bypass flag was used. Computer use cannot access the Codex app in this environment. Until trusted, delivery by the host is intentionally skipped; direct command smoke is not live trusted delivery.

Repository changes are local on codex/cortex-codex-hooks, based on existing runtime branch 0542d95. No push, PR update, merge or public release. Overall runtime branch retains its independent outstanding review/release work. No backfill or messages to audited chats. Current implementation is tracked in the task board separately.
