# Interview talking points
- Why Auto Loader? It persists discovery/schema state and supports cheap append-only file ingestion; `availableNow` matches this finite source.
- Why quarantine? Bad typing or rescued schema cannot silently become null and contaminate marts.
- Why source-row identity? Business columns legitimately repeat (5,270 source rows collide under the old business hash), so Bronze ingests each immutable file as bytes and assigns its physical CSV line with `posexplode`; Silver hashes file path plus line number and cannot collapse exact duplicate facts.
- Why is the MERGE safe? The source is deduplicated only on that immutable identity before MERGE, so Delta never receives multiple source rows for one target key.
- How is publication fail-closed? Row balance, rescued content, quarantine threshold, duplicate identity, and unknown-review threshold are measured and persisted; Gold runs only after all pass, and success is not written early.
- How is revenue protected? Only positively identified merchandise enters KPI measures; services/accounting and unknowns remain reconcilable.
- How would production evolve? Add system-table monitoring, alerts, workload identity, cluster policies, expectations thresholds, and live bundle integration tests after workspace provisioning.
