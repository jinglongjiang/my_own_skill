#!/usr/bin/env python3
"""CPU-only execution of the remotely committed scalar Stage 1 protocol.

The fixed protocol/split files are read-only inputs. CV filters raw lines by
episode before JSON decoding, so locked future labels cannot enter that path.
"""
import os
for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_variable] = "2"

import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import time

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from threadpoolctl import threadpool_limits


ROOT = Path(__file__).resolve().parents[2]
FROZEN = ROOT / "project/stage1"
OUT = ROOT / "project/stage1_outputs"
TABLE = ROOT / "project/data/kda_s443_cf/table.jsonl.gz"
PROTOCOL_COMMIT = "6dd0ce851bbf4ec15cb48e99b03620c4b67e9d58"
ALLOWLIST = ("rewards", "values", "clearance", "commands", "final_scores", "pred_terminal", "eligible")
GROUPS = ((0, 1), (2, 3), (4, 5))
GROUP_NAMES = ("5人", "10人", "20人")
N_BOOT = 5000
BOOT_SEED = 20261013
STAGE1_DEADLINE = datetime(2026, 10, 13, 22, 43, tzinfo=timezone.utc)


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def note(message):
    text = utcnow() + " " + message
    print(text, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "logs/execution.log").open("a") as stream:
        stream.write(text + "\n")


def verify_inputs():
    manifest = json.loads((FROZEN / "ARTIFACTS.json").read_text())
    checks = []
    for item in manifest["files"]:
        actual = sha(ROOT / item["path"])
        checks.append({"path": item["path"], "expected": item["sha256"], "actual": actual})
        if actual != item["sha256"]:
            raise AssertionError("STOP frozen asset SHA mismatch: " + item["path"])
    data = ROOT / "project/data/kda_s443_cf"
    frozen_manifest = json.loads((data / "MANIFEST.json").read_text())
    assert sha(data / "MANIFEST.json") == "0bd2428d061665ac9d89c34e02553d53b73da697322161ce33d57d15ecc72993"
    for name, expected in frozen_manifest["files"].items():
        path = data / name
        actual = sha(path)
        assert actual == expected["sha256"] and path.stat().st_size == expected["bytes"], "STOP data SHA/size mismatch: " + name
        checks.append({"path": str(path.relative_to(ROOT)), "expected": expected["sha256"], "actual": actual})
    save_json(OUT / "input_integrity.json", {"status": "已验证通过", "protocol_remote_commit": PROTOCOL_COMMIT, "time": utcnow(), "checks": checks})


def assignments():
    with (FROZEN / "episodes.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1050 and len({r["episode"] for r in rows}) == 1050
    return {r["episode"]: r for r in rows}


def raw_episode(line):
    matches = re.findall(r'(?:^|[,\{])\s*"episode"\s*:\s*"([^"\\]+)"', line)
    if len(matches) != 1:
        raise AssertionError("Missing or ambiguous episode identity")
    return matches[0]


def filtered_records(lines, split, partition):
    """Only parse admitted lines. A malformed excluded label stays unreachable."""
    records = []
    for line in lines:
        if not line.strip():
            continue
        episode = raw_episode(line)
        assert episode in split, "Unknown episode"
        if split[episode]["partition"] != partition:
            continue
        row = json.loads(line)
        assert row["episode"] == episode
        records.append(row)
    return records


def load_development(split):
    with gzip.open(TABLE, "rt", encoding="utf-8") as stream:
        records = filtered_records(stream, split, "development")
    assert len(records) == 1680 and len({r["key"] for r in records}) == 1680
    expected = {x[k] for x in split.values() if x["partition"] == "development" for k in ["key_1", "key_2"]}
    assert {r["key"] for r in records} == expected
    return sorted(records, key=lambda r: r["key"])


def feature_rows(safe):
    """Only allowlisted decision-time input. Never accepts outcome-bearing rows."""
    assert set(safe) == set(ALLOWLIST), "Feature source allowlist violation"
    scores = np.asarray(safe["final_scores"], dtype=float)
    eligible = np.asarray(safe["eligible"], dtype=bool)
    assert scores.shape == eligible.shape == (80,)
    assert np.isfinite(scores).all()
    assert np.array_equal(eligible, scores > -1e8)
    pool = np.flatnonzero(eligible)
    assert len(pool) > 0, "No safe actions"
    order = pool[np.argsort(-scores[pool])]
    ranks = np.zeros(80, dtype=float)
    ranks[order] = np.arange(len(order), dtype=float)
    commands = np.asarray(safe["commands"], dtype=float)
    assert commands.shape == (80, 2)
    feature = np.column_stack([
        np.asarray(safe["rewards"], dtype=float)[pool],
        np.asarray(safe["values"], dtype=float)[pool],
        np.asarray(safe["clearance"], dtype=float)[pool],
        commands[pool, 0], commands[pool, 1],
        np.linalg.norm(commands[pool], axis=1),
        ranks[pool], scores[pool] - scores[pool].max(),
        np.asarray(safe["pred_terminal"], dtype=float)[pool],
    ])
    assert feature.shape == (len(pool), 9) and np.isfinite(feature).all()
    return feature, pool


def permutation(key, size):
    seed = int(hashlib.sha256(("dots-stage1-shuffle-v1|20261013|" + key).encode()).hexdigest()[:16], 16)
    return np.random.default_rng(seed).permutation(size)


def make_dataset(records, split):
    Xs, returns, failures, shuffled_returns, shuffled_failures, weights, folds = [], [], [], [], [], [], []
    pools, offsets = [], [0]
    for row in records:
        safe = {k: row[k] for k in ALLOWLIST}
        x, pool = feature_rows(safe)
        score = np.asarray(row["final_scores"], dtype=float)
        chosen = row["chosen"]
        assert type(chosen) is int and chosen in pool and score[chosen] == score[pool].max()
        ret = np.asarray(row["G_A"], dtype=float)
        outcome = np.asarray(row["branch_outcome"])
        assert ret.shape == outcome.shape == (80,) and np.isfinite(ret).all()
        assert set(outcome).issubset({"success", "collision", "timeout"})
        y = ret[pool]
        yf = (outcome[pool] != "success").astype(float)
        perm = permutation(row["key"], len(pool))
        Xs.append(x); returns.append(y); failures.append(yf)
        shuffled_returns.append(y[perm]); shuffled_failures.append(yf[perm])
        weights.append(np.full(len(pool), 1.0 / len(pool)))
        folds.append(np.full(len(pool), int(split[row["episode"]]["fold"]), dtype=int))
        pools.append(pool); offsets.append(offsets[-1] + len(pool))
    return {
        "X": np.concatenate(Xs), "return": np.concatenate(returns), "failure": np.concatenate(failures),
        "shuffle_return": np.concatenate(shuffled_returns), "shuffle_failure": np.concatenate(shuffled_failures),
        "weight": np.concatenate(weights), "fold": np.concatenate(folds),
        "pools": pools, "offsets": offsets,
    }


def choose_from_scores(row, pool, scores):
    scores = np.asarray(scores, dtype=float)
    assert len(scores) == len(pool) and np.isfinite(scores).all()
    tied = pool[scores == scores.max()]
    base = row["chosen"]
    if base in tied:
        return int(base)
    original = np.asarray(row["final_scores"], dtype=float)
    best_original = original[tied].max()
    return int(tied[original[tied] == best_original].min())


def choices_from_prediction(records, dataset, predicted, config):
    assert np.isfinite(predicted).all() and len(predicted) == len(dataset["X"])
    out = []
    for i, row in enumerate(records):
        pool = dataset["pools"][i]
        values = predicted[dataset["offsets"][i]:dataset["offsets"][i + 1]]
        if config["id"] == "C03":
            original = np.asarray(row["final_scores"], dtype=float)
            top = np.argsort(-original[pool])[:config["k"]]
            chosen = choose_from_scores(row, pool[top], original[pool[top]] - config["lambda"] * values[top])
        else:
            chosen = choose_from_scores(row, pool, values)
        out.append(chosen)
    return np.asarray(out, dtype=int)


def reference_metrics(row, choice):
    scores = np.asarray(row["final_scores"], dtype=float)
    pool = np.flatnonzero(np.asarray(row["eligible"], dtype=bool))
    G = np.asarray(row["G_A"], dtype=float)
    fail = np.asarray(row["branch_outcome"]) != "success"
    base = int(row["chosen"])
    top5 = pool[np.argsort(-scores[pool])[:5]]
    oracle = choose_from_scores(row, top5, G[top5])
    best = G[pool].max()
    assert int(choice) in pool
    return {
        "key": row["key"], "episode": row["episode"], "case": int(row["episode"].split("-k")[1]),
        "cell": row["cell"], "eligible_count": len(pool), "choice": int(choice), "baseline_choice": base,
        "regret_base": float(best - G[base]), "regret_candidate": float(best - G[choice]),
        "regret_random": float(best - G[pool].mean()), "regret_random_top5": float(best - G[top5].mean()),
        "regret_oracle_top5": float(best - G[oracle]),
        "failure_base": float(fail[base]), "failure_candidate": float(fail[choice]),
        "failure_random": float(fail[pool].mean()), "failure_random_top5": float(fail[top5].mean()),
        "failure_oracle_top5": float(fail[oracle]),
    }


def import_repo_module(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_development_controls(records):
    ruler = import_repo_module("skills/prescreen/scripts/regret_ruler.py", "stage1_ruler")
    rescue = import_repo_module("project/tools/rescue_stats.py", "stage1_rescue")
    args = argparse.Namespace(group_map="0,1=5人;2,3=10人;4,5=20人", key="key", score="final_scores", ret="G_A", group="cell", cluster="episode", mode="target", chosen="chosen", mask_below=-1e8)
    states, groups, skipped = ruler.build(records, args)
    by_key = {s.rec["key"]: s for s in states}
    max_abs = 0.0
    for row in records:
        metrics = reference_metrics(row, row["chosen"])
        if metrics["eligible_count"] >= 2:
            s = by_key[row["key"]]
            expected = [s.best - s.ret[s.base], s.best - s.ret[s.feas].mean()]
            got = [metrics["regret_base"], metrics["regret_random"]]
            error = float(np.max(np.abs(np.asarray(expected) - got)))
            assert error <= 1e-9, "STOP independent baseline/random mismatch"
            max_abs = max(max_abs, error)
        else:
            assert row["key"] not in by_key
        original_rescue = rescue.per_row(row)
        assert metrics["failure_base"] == original_rescue[0]
        error = abs(metrics["failure_random"] - original_rescue[3])
        assert error <= 1e-9, "STOP rescue random mismatch"
        max_abs = max(max_abs, error)
    assert len(states) + skipped == len(records)
    report = {"status": "已验证通过", "data_partition": "development only", "full_table_reproduction": "project/reports/stage0_revalidation_20261013", "roots": len(records), "regret_roots": len(states), "single_eligible_skipped": skipped, "maximum_absolute_difference": max_abs, "integer_counts_exact": True, "locked_labels_decoded": False}
    save_json(OUT / "development_controls.json", report)
    return report


def model_fit_worker(job_path, config_path, model_path, prediction_path):
    config = json.loads(Path(config_path).read_text())
    job = np.load(job_path, allow_pickle=False)
    X, y, weight, valid = job["X"], job["y"], job["weight"], job["valid"]
    mean, scale = None, None
    with threadpool_limits(limits=2):
        if config["id"] == "C01":
            mean = np.average(X, axis=0, weights=weight)
            scale = np.sqrt(np.average((X - mean) ** 2, axis=0, weights=weight))
            scale[scale == 0] = 1.0
            X = (X - mean) / scale
            valid = (valid - mean) / scale
            estimator = Ridge(**config["parameters"])
        elif config["id"] == "C02":
            estimator = HistGradientBoostingRegressor(**config["parameters"])
        else:
            estimator = HistGradientBoostingClassifier(**config["parameters"])
        if config["id"] == "C03" and len(np.unique(y)) == 1:
            model = {"constant_failure_probability": float(y[0]), "mean": mean, "scale": scale, "config": config}
            predicted = np.full(len(valid), y[0])
        else:
            estimator.fit(X, y, sample_weight=weight)
            predicted = estimator.predict_proba(valid)[:, list(estimator.classes_).index(1)] if config["id"] == "C03" else estimator.predict(valid)
            model = {"estimator": estimator, "mean": mean, "scale": scale, "config": config}
        assert np.isfinite(predicted).all()
        joblib.dump(model, model_path, compress=3)
        np.save(prediction_path, predicted, allow_pickle=False)
    print(json.dumps({"status": "fit_complete", "model_sha256": sha(model_path), "predictions": len(predicted)}), flush=True)


def one_fit(dataset, config, train_mask, valid_mask, target, name):
    remaining = (STAGE1_DEADLINE - datetime.now(timezone.utc)).total_seconds()
    if remaining <= 0:
        raise AssertionError("STOP: Stage 1 wall-clock deadline reached")
    runtime = OUT / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    (OUT / "models").mkdir(exist_ok=True)
    job = runtime / "fit_job.npz"
    cfg = runtime / "fit_config.json"
    model_path = OUT / "models" / (name + ".joblib")
    pred_path = runtime / (name + ".npy")
    np.savez(job, X=dataset["X"][train_mask], y=dataset[target][train_mask], weight=dataset["weight"][train_mask], valid=dataset["X"][valid_mask])
    save_json(cfg, config)
    log_path = OUT / "logs" / (name + ".log")
    started = time.monotonic()
    note("Fit starts: " + name)
    command = [sys.executable, str(Path(__file__)), "fit", "--job", str(job), "--config", str(cfg), "--model", str(model_path), "--prediction", str(pred_path)]
    status, error = "complete", None
    try:
        with log_path.open("w") as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=min(1200, remaining), check=False)
        if result.returncode != 0:
            status, error = "fit_exception", "exit code %d" % result.returncode
    except subprocess.TimeoutExpired:
        status, error = "fit_timeout", "Wall-clock exceeded 1200 seconds"
    elapsed = time.monotonic() - started
    record = {"fit": name, "candidate": config["id"], "status": status, "wall_seconds": elapsed, "error": error, "log": str(log_path.relative_to(ROOT)), "debug_retries_used": 0, "maximum_debug_retries": 1}
    with (OUT / "fit_ledger.jsonl").open("a") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    note("Fit ends: %s %s %.2fs" % (name, status, elapsed))
    if status != "complete":
        return None
    predicted = np.load(pred_path, allow_pickle=False)
    assert len(predicted) == int(valid_mask.sum()) and np.isfinite(predicted).all()
    return predicted, model_path


def oof_fit(records, split, dataset, config, shuffled):
    predicted = np.full(len(dataset["X"]), np.nan)
    label = "failure" if config["id"] == "C03" else "return"
    if shuffled:
        label = "shuffle_" + label
    suffix = "shuffle" if shuffled else "true"
    for fold in range(5):
        train = dataset["fold"] != fold
        valid = ~train
        train_cases = {int(split[row["episode"]]["case"]) for row in records if int(split[row["episode"]]["fold"]) != fold}
        valid_cases = {int(split[row["episode"]]["case"]) for row in records if int(split[row["episode"]]["fold"]) == fold}
        assert not train_cases & valid_cases and len(train_cases) == 112 and len(valid_cases) == 28
        got = one_fit(dataset, config, train, valid, label, "%s_%s_fold%d" % (config["id"], suffix, fold))
        if got is None:
            note("Candidate abandoned after a fit failure; no debug retry used: " + config["id"])
            return None
        predicted[valid] = got[0]
    assert np.isfinite(predicted).all()
    np.save(OUT / ("%s_%s_oof_predictions.npy" % (config["id"], suffix)), predicted, allow_pickle=False)
    choices = choices_from_prediction(records, dataset, predicted, config)
    metric_rows = [reference_metrics(row, choice) for row, choice in zip(records, choices)]
    with (OUT / ("%s_%s_oof_rows.jsonl" % (config["id"], suffix))).open("w") as stream:
        for row in metric_rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    return metric_rows


def percentile(values, coverage=0.95):
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    alpha = (1.0 - coverage) * 50.0
    return [float(x) for x in np.percentile(finite, [alpha, 100 - alpha])] if len(finite) else None


def ratio(num, den):
    num, den = np.broadcast_arrays(np.asarray(num, dtype=float), np.asarray(den, dtype=float))
    result = np.full(num.shape, np.nan)
    np.divide(num, den, out=result, where=den != 0)
    return result


def finite_scalar(x):
    return float(x) if np.isfinite(x) else None


def bootstrap_weights(rows, cluster_field, group_index, partition_code):
    clusters = sorted({r[cluster_field] for r in rows})
    index = {key: i for i, key in enumerate(clusters)}
    seed = [BOOT_SEED, partition_code, group_index, 0 if cluster_field == "episode" else 1]
    rng = np.random.default_rng(np.random.SeedSequence(seed))
    draws = rng.integers(0, len(clusters), size=(N_BOOT, len(clusters)))
    counts = np.array([np.bincount(row, minlength=len(clusters)) for row in draws], dtype=float)
    row_cluster = np.array([index[r[cluster_field]] for r in rows])
    return counts[:, row_cluster], seed


def summary_one_group(rows, group_index, partition_code, cluster_field, include_tail):
    weights, seed = bootstrap_weights(rows, cluster_field, group_index, partition_code)
    eligible = np.array([r["eligible_count"] >= 2 for r in rows])
    base = np.array([r["regret_base"] for r in rows])
    cand = np.array([r["regret_candidate"] for r in rows])
    fb = np.array([r["failure_base"] for r in rows])
    fc = np.array([r["failure_candidate"] for r in rows])
    wreg = weights * eligible
    nreg = wreg.sum(axis=1)
    nall = weights.sum(axis=1)
    base_sum = wreg @ base
    delta_sum = wreg @ (base - cand)
    reduction_boot = ratio(delta_sum, base_sum)
    point = ratio((base[eligible] - cand[eligible]).sum(), base[eligible].sum()).item()
    result = {
        "n_states_failure": len(rows), "n_states_regret": int(eligible.sum()),
        "n_episodes": len({r["episode"] for r in rows}), "n_cases": len({r["case"] for r in rows}),
        "regret_reduction": finite_scalar(point), "regret_reduction_ci95": percentile(reduction_boot),
        "regret_reduction_ci98_3333_cv_bonferroni": percentile(reduction_boot, 1 - 0.05 / 3) if partition_code == 0 else None,
        "paired_regret_gain": float((base[eligible] - cand[eligible]).mean()),
        "paired_regret_gain_ci95": percentile(ratio(delta_sum, nreg)),
        "failure_change_candidate_minus_base": float((fc - fb).mean()),
        "failure_change_ci95": percentile(ratio(weights @ (fc - fb), nall)),
        "failure_change_comparable_subset": float((fc[eligible] - fb[eligible]).mean()),
        "failure_change_comparable_subset_ci95": percentile(ratio(wreg @ (fc - fb), nreg)),
        "bootstrap": {"cluster": cluster_field, "replicates": N_BOOT, "seed_sequence": seed, "invalid_regret_ratio_replicates": int((~np.isfinite(reduction_boot)).sum())},
    }
    for arm in ["base", "candidate", "random", "random_top5", "oracle_top5"]:
        regret = np.array([r["regret_" + arm] for r in rows])
        failure = np.array([r["failure_" + arm] for r in rows])
        result[arm] = {
            "regret_mean": float(regret[eligible].mean()), "regret_mean_ci95": percentile(ratio(wreg @ regret, nreg)),
            "failure_rate": float(failure.mean()), "failure_rate_ci95": percentile(ratio(weights @ failure, nall)),
            "failure_rate_comparable_subset": float(failure[eligible].mean()), "failure_rate_comparable_subset_ci95": percentile(ratio(wreg @ failure, nreg)),
        }
    if include_tail:
        result["tail"] = tail_summary(rows, weights, eligible, base, cand)
    return result


def tail_summary(rows, weights, eligible, base, cand):
    base_reg, cand_reg = base[eligible], cand[eligible]
    order = np.argsort(-base_reg, kind="stable")
    shares = {1: [], 3: []}
    trimmed = {1: [], 3: []}
    med_base, med_cand, med_difference = [], [], []
    for w in weights[:, eligible]:
        idx = np.repeat(np.arange(len(base_reg)), w.astype(int))
        b, c = base_reg[idx], cand_reg[idx]
        rank = np.argsort(-b, kind="stable")
        for k in (1, 3):
            shares[k].append(ratio(b[rank[:k]].sum(), b.sum()).item())
            kept = rank[k:]
            trimmed[k].append(ratio((b[kept] - c[kept]).sum(), b[kept].sum()).item())
        mb, mc = np.median(b), np.median(c)
        med_base.append(mb); med_cand.append(mc); med_difference.append(mb - mc)
    result = {}
    for k in (1, 3):
        kept = order[k:]
        result["base_top%d_share" % k] = {"point": finite_scalar(ratio(base_reg[order[:k]].sum(), base_reg.sum()).item()), "ci95": percentile(shares[k])}
        result["drop_base_top%d_reduction" % k] = {"point": finite_scalar(ratio((base_reg[kept] - cand_reg[kept]).sum(), base_reg[kept].sum()).item()), "ci95": percentile(trimmed[k])}
    result["median_base"] = {"point": float(np.median(base_reg)), "ci95": percentile(med_base)}
    result["median_candidate"] = {"point": float(np.median(cand_reg)), "ci95": percentile(med_cand)}
    result["median_difference"] = {"point": float(np.median(base_reg) - np.median(cand_reg)), "ci95": percentile(med_difference)}
    cases = sorted({r["case"] for r in rows})
    absolute_gain = np.abs(base - cand) * eligible
    case_masks = np.array([[r["case"] == c for r in rows] for c in cases], dtype=float)
    case_total = case_masks @ absolute_gain
    case_boot = (weights * absolute_gain) @ case_masks.T
    for k in (1, 3):
        point = ratio(np.sort(case_total)[-k:].sum(), case_total.sum()).item()
        boot = ratio(np.sort(case_boot, axis=1)[:, -k:].sum(axis=1), case_boot.sum(axis=1))
        result["top%d_case_share_absolute_gain" % k] = {"point": finite_scalar(point), "ci95": percentile(boot)}
    return result


def summarize(rows, partition_code=0):
    output = {}
    for gi, cells in enumerate(GROUPS):
        group_rows = [r for r in rows if r["cell"] in cells]
        output[GROUP_NAMES[gi]] = {
            "episode_primary": summary_one_group(group_rows, gi, partition_code, "episode", True),
            "case_sensitivity": summary_one_group(group_rows, gi, partition_code, "case", False),
        }
    return output


def main_gain(rows):
    valid = [r for r in rows if r["cell"] in (4, 5) and r["eligible_count"] >= 2]
    return float(np.mean([r["regret_base"] - r["regret_candidate"] for r in valid]))


def synthetic_tests():
    count = 0
    def check(condition):
        nonlocal count
        assert condition, "Synthetic unit check %d failed" % (count + 1)
        count += 1
    safe = {
        "rewards": [0.0] * 80, "values": [1.0] * 80, "clearance": [0.5] * 80,
        "commands": [[1.0, 0.0]] * 80, "final_scores": [0.9, 0.8] + [-1e9] * 78,
        "pred_terminal": [False] * 80, "eligible": [True, True] + [False] * 78,
    }
    x, pool = feature_rows(safe)
    check(x.shape == (2, 9) and np.array_equal(pool, [0, 1]))
    check(np.array_equal(x[:, 6], [0, 1]) and np.allclose(x[:, 7], [0.0, -0.1]))
    row = dict(safe, key="c4-k93000-s1", episode="c4-k93000", cell=4, chosen=0,
               G_A=[0.5, 0.9] + [0.0] * 78, branch_outcome=["collision", "success"] + ["timeout"] * 78)
    changed = dict(row, G_A=[999.0] * 80, branch_outcome=["success"] * 80, true_terminal_step1=[True] * 80)
    check(np.array_equal(feature_rows({k: row[k] for k in ALLOWLIST})[0], feature_rows({k: changed[k] for k in ALLOWLIST})[0]))
    denied = False
    try:
        feature_rows(row)
    except AssertionError:
        denied = True
    check(denied)
    split = {"c4-k93000": {"partition": "development", "fold": "0"}, "c4-k93001": {"partition": "locked", "fold": ""}}
    # Deliberately invalid JSON label proves the excluded row is never decoded.
    lines = [json.dumps(row), '{"episode":"c4-k93001","G_A":THIS_MUST_NOT_BE_PARSED}']
    got = filtered_records(lines, split, "development")
    check(len(got) == 1 and got[0]["episode"] == "c4-k93000")
    dataset = make_dataset([row], split)
    check(abs(dataset["weight"].sum() - 1.0) < 1e-15)
    check(np.array_equal(np.sort(dataset["shuffle_return"]), np.sort(dataset["return"])))
    # Paired label permutation preserves return/failure association, not action association.
    check(np.array_equal(dataset["shuffle_failure"], (dataset["shuffle_return"] == 0.5).astype(float)))
    check(np.array_equal(permutation(row["key"], 2), permutation(row["key"], 2)))
    check(choose_from_scores(row, pool, [1.0, 1.0]) == 0)
    check(choose_from_scores(row, pool, [0.0, 1.0]) == 1)
    metrics = reference_metrics(row, 1)
    check(abs(metrics["regret_base"] - 0.4) < 1e-15 and metrics["regret_candidate"] == 0.0)
    check(abs(metrics["regret_random"] - 0.2) < 1e-15 and metrics["failure_random"] == 0.5)
    check(metrics["failure_base"] == 1.0 and metrics["failure_candidate"] == 0.0)
    check(ratio(1, 2).item() == 0.5 and np.isnan(ratio(1, 0).item()))
    check(np.allclose(percentile([0, 1, np.nan]), [0.025, 0.975], rtol=0, atol=1e-15))
    rows = [dict(metrics, episode="c4-k93000", case=93000), dict(metrics, episode="c4-k93000", case=93000), dict(metrics, episode="c5-k93001", case=93001)]
    w, seed = bootstrap_weights(rows, "episode", 2, 0)
    check(np.array_equal(w[:, 0], w[:, 1]))
    check(seed == [20261013, 0, 2, 0] and w.shape == (5000, 3))
    gain = main_gain(rows)
    check(gain > 0 and abs(gain - 0.4) < 1e-15)
    check(main_gain([dict(metrics, regret_candidate=metrics["regret_base"])]) == 0.0)
    # Feature scaling is train-only and total weights are root-balanced by construction.
    check(np.all(dataset["fold"] == 0) and dataset["X"].shape[1] == 9)
    summary = summary_one_group(rows, 2, 0, "episode", True)
    check(summary["regret_reduction"] == 1.0 and summary["regret_reduction_ci95"] == [1.0, 1.0])
    check(summary["failure_change_candidate_minus_base"] == -1.0 and summary["failure_change_ci95"] == [-1.0, -1.0])
    check(abs(summary["tail"]["base_top1_share"]["point"] - 1 / 3) < 1e-15)
    singleton = dict(metrics, key="c4-k93002-s1", episode="c4-k93002", case=93002,
                     eligible_count=1, regret_base=0.0, regret_candidate=0.0,
                     regret_random=0.0, regret_random_top5=0.0, regret_oracle_top5=0.0,
                     failure_candidate=1.0)
    separated = summary_one_group(rows + [singleton], 2, 0, "episode", False)
    check(separated["n_states_failure"] == 4 and separated["n_states_regret"] == 3)
    check(separated["candidate"]["failure_rate"] == 0.25 and separated["candidate"]["failure_rate_comparable_subset"] == 0.0)
    save_json(OUT / "synthetic_tests.json", {"status": "已验证通过", "checks_passed": count, "time": utcnow(), "real_data_loaded": False, "implementation_sha256": sha(Path(__file__))})
    print("Synthetic checks passed:", count, flush=True)


def run_cv():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "logs").mkdir(exist_ok=True)
    assert not (OUT / "CV_TERMINAL.json").exists(), "Refuse rerunning a terminal CV execution"
    verify_inputs()
    tests = json.loads((OUT / "synthetic_tests.json").read_text())
    assert tests["status"] == "已验证通过"
    split = assignments()
    records = load_development(split)
    controls = verify_development_controls(records)
    dataset = make_dataset(records, split)
    note("Development loaded: %d roots, %d candidate samples, nine allowed features; locked labels excluded" % (len(records), len(dataset["X"])))
    completed, skipped = [], []
    configs = json.loads((FROZEN / "candidates.json").read_text())["candidates"]
    for config in configs:
        shuffled = oof_fit(records, split, dataset, config, True)
        if shuffled is None:
            skipped.append({"candidate": config["id"], "reason": "shuffle fit failed"})
            continue
        gain = main_gain(shuffled)
        hard_stop = gain > 0.0
        note("Shuffle gate: %s paired 20-person mean regret gain %.17g; %s" % (config["id"], gain, "STOP" if hard_stop else "PASS"))
        gate = {"candidate": config["id"], "twenty_person_paired_mean_regret_gain": gain, "threshold": "strictly > 0.0", "status": "已确认失败" if hard_stop else "已验证通过", "locked_labels_decoded": False, "time": utcnow()}
        save_json(OUT / (config["id"] + "_shuffle_gate.json"), gate)
        if hard_stop:
            # Stop all experiments first. Summaries only document the already obtained control.
            terminal = {"status": "已确认失败", "reason": "positive label-shuffle OOF gain", "candidate": config["id"], "gain": gain, "completed_true_candidates": completed, "skipped": skipped, "locked_labels_decoded": False, "time": utcnow()}
            save_json(OUT / "CV_TERMINAL.json", terminal)
            save_json(OUT / (config["id"] + "_shuffle_summary.json"), summarize(shuffled))
            print(json.dumps(terminal, ensure_ascii=False), flush=True)
            return 2
        save_json(OUT / (config["id"] + "_shuffle_summary.json"), summarize(shuffled))
        true_rows = oof_fit(records, split, dataset, config, False)
        if true_rows is None:
            skipped.append({"candidate": config["id"], "reason": "true-label fit failed"})
            continue
        summary = summarize(true_rows)
        save_json(OUT / (config["id"] + "_true_summary.json"), summary)
        primary = summary["20人"]["episode_primary"]
        completed.append({"candidate": config["id"], "regret": primary["candidate"]["regret_mean"], "failure": primary["candidate"]["failure_rate"], "reduction": primary["regret_reduction"]})
        note("True OOF complete: %s 20-person reduction %s" % (config["id"], primary["regret_reduction"]))
    if not completed:
        save_json(OUT / "CV_TERMINAL.json", {"status": "已确认失败", "reason": "No candidate completed", "skipped": skipped, "locked_labels_decoded": False, "time": utcnow()})
        return 2
    winner = sorted(completed, key=lambda x: (x["regret"], x["failure"], x["candidate"]))[0]
    config = next(x for x in configs if x["id"] == winner["candidate"])
    final = one_fit(dataset, config, np.ones(len(dataset["X"]), dtype=bool), np.ones(len(dataset["X"]), dtype=bool), "failure" if config["id"] == "C03" else "return", config["id"] + "_final_development")
    if final is None:
        save_json(OUT / "CV_TERMINAL.json", {"status": "已确认失败", "reason": "Selected full-development fit failed; no locked evaluation", "winner": winner, "locked_labels_decoded": False, "time": utcnow()})
        return 2
    selection = {"status": "selection prepared; locked labels remain sealed pending remote commit confirmation", "selected_candidate": config, "selection_rule": "lowest 20-person OOF regret, then failure, then ID", "winner": winner, "all_completed_candidates": completed, "skipped_candidates": skipped, "model_path": str(final[1].relative_to(ROOT)), "model_sha256": sha(final[1]), "protocol_remote_commit": PROTOCOL_COMMIT, "protocol_sha256": sha(FROZEN / "PROTOCOL.md"), "episodes_csv_sha256": sha(FROZEN / "episodes.csv"), "candidate_list_sha256": sha(FROZEN / "candidates.json"), "implementation_sha256": sha(Path(__file__)), "training_roots": len(records), "training_candidates": len(dataset["X"]), "locked_labels_decoded": False, "time": utcnow()}
    save_json(OUT / "SELECTED_CANDIDATE.json", selection)
    save_json(OUT / "CV_TERMINAL.json", {"status": "已验证通过", "reason": "CV complete; selection awaits remote commit before locked read", "winner": winner, "locked_labels_decoded": False, "time": utcnow()})
    note("Selection ready for remote commit; no locked read: " + winner["candidate"])
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["test", "cv", "fit"])
    parser.add_argument("--job"); parser.add_argument("--config"); parser.add_argument("--model"); parser.add_argument("--prediction")
    args = parser.parse_args()
    if args.mode == "test":
        synthetic_tests()
    elif args.mode == "fit":
        model_fit_worker(args.job, args.config, args.model, args.prediction)
    else:
        with threadpool_limits(limits=2):
            return run_cv()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
