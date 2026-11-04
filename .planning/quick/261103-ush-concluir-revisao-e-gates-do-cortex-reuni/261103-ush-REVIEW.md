# Revisão final do candidato Cortex

Implementação OpenAI; revisão Claude `claude-opus-5-5`, perfil Pessoal, helper `claude-peer`, somente leitura.

Primeira rodada NO-GO por esgotamento definitivo de recibos. Corrigido junto com versões frias, recorrência tombstonada, diff check e checkout do atestado. Segunda rodada `ok:true`, `result_subtype:success`, **GO** sobre commit `4cb310c`. Nenhuma alteração de fonte depois da revisão.

Uso agregado: entrada52, saída18287, cache criado103167, cache lido937743. Custo equivalente USD1.3788326 (assinatura local, não implica cobrança API adicional).

**Verdict: GO.** The receipt-exhaustion blocker is fixed, the four other findings are fixed or no longer apply, and I found no new blocker. I read the code at 4cb310c directly and made no edits or commands.

## Former blocker: receipt exhaustion is fixed
- **Writes no longer stop.** The hard `quota_exceeded` refusal is gone. Every write now inserts its receipt and then calls `_compact_receipts` in the same transaction (`skills/tarefas/local_store.py:224-227`).
- **Compaction works as described.** It walks the stored results from newest to oldest. Once it passes 10,000 results or 64 MiB, it sets each older result to `''` and keeps the row (`local_store.py:242-253`). It never deletes rows, so the ID and digest remain as a permanent marker.
- **Ordering is safe.** The table uses an implicit rowid, nothing is ever deleted, and rowids keep increasing, so "newest first" is correct.
- **Retry behaviour matches your description** (`local_store.py:211-218`):
  - Same ID, different request → `conflict`.
  - Same ID, identical request, payload compacted → `receipt_expired`.
  - Otherwise the stored result is returned.
  - A real result can never be `''`, since every result is a JSON object, so an empty result reliably means "compacted".
- **Existing databases are covered.** The partial index is created lazily inside the write transaction (`local_store.py:246`), and the compaction query uses its filter.
- **The test covers the important cases** (`tests/test_local.py:222-241`): exact replay of the newest request, the oldest one expiring without being re-applied (the version stays at 9), a mismatched request conflicting, and writes continuing after the byte cap. The tradeoff is documented in `LOCAL.md:100-104`.

## Other findings

| Finding | Status | Evidence |
|---|---|---|
| Write before any read silently used the latest server version | **Fixed** | `local-adapter.js:111` refuses with `conflict` before sending anything. The test checks that no `tasks` request is made (`test_local_adapter.js:172-177`). |
| Deleted recurrence card blocked its recurrence | **Fixed** | `board-src.html:599` treats a local deletion marker (`exists:false` with a version) as already created. The code still reaches the `ultima` update at `:612`. The test runs the real function sliced out of `board-src.html` (`test_local_adapter.js:179-193`). |
| `git diff --check` checked nothing | **Fixed** | `local-ci.steps:4` now compares `origin/main...HEAD`. `ci.yml:25` uses `fetch-depth: 0`, and `local-ci.sh:12` fetches `origin/main` first. On a push to main the diff is empty and passes, which is correct. |
| Attestation compared the wrong tree | **Fixed (informational only)** | `local-ci-gate.yml:15` checks out the PR head SHA. The step never fails the build, and the `checks` job always runs the full suite (`ci.yml:17-33`). |
| Release candidate had uncommitted edits | **Fixed** | The tree is clean at 4cb310c. |

## Test results
`/private/tmp/cortex-final-checks.txt` shows 50 Python tests OK and 13 of 13 Node tests passing, including the two new adapter tests, plus the manifest validation. That output contains no commit SHA, so I can't confirm it was produced from this exact tree. The `local-ci` rerun before publishing will settle that.

## Non-blocking (worth a follow-up)
1. **Write cost grows with stored results.** `_compact_receipts` (`local_store.py:247`) computes `LENGTH(CAST(result AS BLOB))` over every uncompacted result on every write. That likely reads up to 64 MiB of payload per write. It's correct, just slower than it needs to be; storing the size in its own column at insert time would fix it.
2. **`receipt_expired` returns HTTP 400.** It isn't in the status map at `local.py:124-125`, so it falls through to the default. That's acceptable today because the UI never retries with the same ID, but a 409 would describe it better.
3. **Markers grow without limit** (about 100–150 bytes per write) and don't count toward the board quota. This is the documented tradeoff and is acceptable.

## Limitations
- I didn't run anything.
- I re-checked only the corrected areas. I didn't repeat the line-by-line analysis of code that hasn't changed.
- This verdict doesn't cover live hook trust or delivery.
- Merging still depends on the `local-ci` rerun on this tree and the official `checks` job passing.
