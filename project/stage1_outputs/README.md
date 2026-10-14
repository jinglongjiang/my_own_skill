# Stage 1 evidence: stopped at the predeclared label-shuffle gate

The protocol and split were committed remotely at `6dd0ce851bbf4ec15cb48e99b03620c4b67e9d58` before execution. This run ended at 2026-10-13 16:59:12 UTC. Do not resume it or decode locked labels.

Commands executed from the repository root:

1. `python3 project/tools/stage1_offline.py test` — 26 synthetic checks passed. An earlier 21-check version also passed before five additional statistical/denominator checks were added; no test failed.
2. `python3 project/tools/stage1_offline.py cv` — input hashes and development controls passed; process exited 2 when C02's shuffled OOF primary gain was strictly positive.

`CV_TERMINAL.json` is the authoritative stop marker. There were 15 successful fits: five C01 shuffled, five C01 true-label and five C02 shuffled. No fit exceeded 3.115 seconds, no debug retry was used, no C02 true-label or C03 fit occurred, no final model or selected-candidate file was created. No locked outcomes were JSON-decoded by Stage 1.

## Reconstruct already-computed metrics without table or locked labels

The three `*_oof_rows.jsonl.gz` files contain the complete already-computed development per-root metric records. They were compressed only after the stop, using deterministic gzip mtime=0. Their metrics contain safe-oracle/baseline/candidate/random/top5 choices and outcomes only for development rows, along with episode/case groups. Reading these files does not require reopening the source table.

The `summarize(rows, partition_code=0)` function in `project/tools/stage1_offline.py` deterministically recomputes the summaries from these records; it does not train or access the table. The stored summaries include episode-primary and case-block sensitivity, 5,000 paired bootstrap replicates, seeds, all three groups, separate regret/failure denominators, tail diagnostics and descriptive/multiplicity-adjusted intervals. The STOP point was checked before generating summaries of that already-completed control; no further experiment followed.

## Local artifacts

OOF candidate-level predictions, fitted fold models and runtime job arrays remain local and are intentionally ignored by Git. Their hashes and sizes are listed in `LOCAL_ARTIFACTS.json`, together with original uncompressed metric row hashes. The public compressed rows and source are sufficient to independently reproduce the reported statistics without locked outcomes. There is no final selected model to publish.

`saved_output_audit.json` checks finite numeric values in saved outputs only. Packaging did not reread the source table, rerun any model or change the frozen protocol/splits/data/results. `PUBLICATION_MANIFEST.json` lists the precise publication files and their hashes, excluding itself to avoid recursive hashing.
