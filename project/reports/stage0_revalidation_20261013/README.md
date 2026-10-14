# Revalidation evidence (2026-10-13)

This directory is additive. The frozen data, frozen result files, historical strict report and historical comparator remain untouched.

Authorized numeric rule: integers match exactly; floats have absolute error <= 1e-9. JSON integer and float types remain distinct. No relative tolerance.

Executed from the repository root, in this order; every command exited zero:

1. `python3 tests/test_tools.py` (logs/test_tools.log)
2. `python3 tools/validate.py` (logs/validate.log)
3. `python3 project/reports/stage0_revalidation_20261013/compare_results.py --self-test` (11 tests)
4. `python3 skills/prescreen/scripts/regret_ruler.py target project/data/kda_s443_cf/table.jsonl.gz --group cell --group-map '0,1=5人;2,3=10人;4,5=20人' --cluster episode --key key --boot 5000 --seed 1 --json-out project/reports/stage0_revalidation_20261013/kda_s443_target.reproduced.json`
5. `python3 project/reports/stage0_revalidation_20261013/compare_results.py project/results/kda_s443_target.json project/reports/stage0_revalidation_20261013/kda_s443_target.reproduced.json --target-path-prefix` (target_comparison.json)
6. `python3 project/tools/rescue_stats.py project/data/kda_s443_cf/table.jsonl.gz` (kda_s443_rescue.reproduced.json)
7. `python3 project/reports/stage0_revalidation_20261013/compare_results.py project/results/kda_s443_rescue.json project/reports/stage0_revalidation_20261013/kda_s443_rescue.reproduced.json` (rescue_comparison.json)
8. `python3 project/reports/stage0_revalidation_20261013/verify_manifest.py` (manifest_verification.json)
9. `git diff --exit-code cf85574 -- project/data project/results` (empty logs/immutable_paths.log; exit zero)

`--json-out` only serializes the full-precision result of the task's target command; no computation or bootstrap settings were changed.

The three local gates (tests, reproduction, manifest hashes) passed. The fourth brief item, external feature definitions, remains unverified. External feature definitions are unverified, so subsequent work must remain scalar-only until a separately documented source check succeeds. NPZ bytes were hashed without decoding arrays. Source index and mother weights listed in MANIFEST are not local files and were not rehashed.
