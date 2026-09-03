# Interaction record

The record behind Supplementary Sections S12.2 and S14.4.

## `paper_llm/`

The coded analysis of the conversational record.

| File | Contents |
|---|---|
| `turns.json`, `user_turns.json` | Turn-level index of the sessions, operator turns separated from tool results, harness injections, and compaction summaries. |
| `operator_prompts.json` | The operator prompts, coded by role setting, literature supply, challenge, correction, self-correction, physics injection, design, planning, method specification, instrument constraint, data return, tooling, and deliverable request. |
| `coding.py` | The coding scheme itself, released so the assignments can be checked. |
| `quotes.json` | The verbatim excerpts reproduced in the figures, with their turn identifiers. |
| `guards.json` | Which PITFALLS entries became executable checks, and where. |
| `findings.json` | FINDINGS entries with their grades and supersessions, machine readable. |
| `phase2.json`, `phase2_spans.json` | The Campaign 2 iteration spans. |
| `stage_times.json`, `exp_time.json`, `blocks.json` | Wall-clock intervals behind Table S5. |
| `estimator_compare.json`, `estimator_test.py`, `noise_compare.json`, `noise_test*.py` | The estimator and noise comparisons of Section S8. |
| `dose_fixed.json`, `nb_cells.json`, `paper_numbers.json` | Dose series, notebook cell index, and the numbers quoted in the paper. |
| `utk_maps.npz` | Cached director population maps for the IT10b letters. |

**Caveat, stated in the paper.** The prompt coding was assisted by a model from
the same class as the one under study, so the assignments are descriptive rather
than an independent behavioural measurement. The scheme and every assignment are
released here so a reader can recode them. There is also no control arm: nothing
here measures what the same operator would have achieved without the agent, or
what the same agent would have achieved with another operator.

## Redactions

The session context carried the operator's personal contact details and the
local filesystem paths of the machines involved, so those appear inside the
verbatim record. They are replaced, visibly, so a reader can see that the record
was altered and exactly how:

| Original | Replacement |
|---|---|
| the operator's personal email address | `[operator email redacted]` |
| the operator's Google Drive project root | `<DRIVE>` |
| the operator's home directory | `<HOME>` |

Nothing else is altered. The instrument-computer paths (`C:\Users\Asylum
User\...`) are a shared laboratory account and are left in place, because they
are what the scripts actually used.

## `transcripts/`

Readable Markdown renderings of the five sessions, produced by
`export_history*.py`. The raw JSON session dumps, about 24,000 entries, are in
the separate data deposit rather than here; see `../docs/DATA_AVAILABILITY.md`.

Licence: CC BY 4.0, see `../LICENSE-DATA`.
