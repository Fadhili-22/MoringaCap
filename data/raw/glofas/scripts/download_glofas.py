"""Download GloFAS v4.0 historical (consolidated) daily river discharge for Kenya.

Source: Copernicus CEMS Early Warning Data Store (EWDS), dataset cems-glofas-historical.
The form allows one year per request, so there is one request per year (1999-2025). The wait is ECMWF's
queue, not the file size (~7 MB a year), so this script does NOT block on a request:

  * it keeps up to --window (default 8) year-requests on the server at once (submitted, not yet downloaded);
  * every request ID is stored in requests.json (next to this folder's .nc files), so a restart resumes polling
    the same IDs instead of resubmitting;
  * on start it also reads the EWDS "Your requests" list and re-uses jobs already queued or finished there
    (finished-but-never-downloaded jobs are downloaded straight away);
  * every --poll seconds (default 150) it checks each outstanding request; a finished one is streamed to disk
    as <file>.part and renamed to glofas_kenya_<year>.nc only when complete, and the next year is submitted;
  * if the server rejects a submission (rate limit / service protection) the window drops to --min-window
    (default 4) and stays there for the rest of the run.

Files: data/raw/glofas/glofas_kenya_<year>.nc. Years whose final file exists are skipped. Log: download_log.txt.
Credentials come from %USERPROFILE%\\.cdsapirc (url https://ewds.climate.copernicus.eu/api).

Usage:
    python download_glofas.py [--first 1999] [--last 2025] [--window 8] [--min-window 4] [--poll 150]
    python download_glofas.py --validate-only
"""
import argparse
import json
import os
import time
from datetime import datetime

import cdsapi
import pandas as pd

# data/raw/glofas/scripts/download_glofas.py -> the repo root is four folders up
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
OUT_DIR = os.path.join(REPO_ROOT, "data", "raw", "glofas")
LOG = os.path.join(OUT_DIR, "download_log.txt")
REQUESTS_JSON = os.path.join(OUT_DIR, "requests.json")
COLLECTION = "cems-glofas-historical"
MAX_SUBMIT_FAILURES = 3  # consecutive failed submissions of one year before it is reported as missing
MAX_DOWNLOAD_TRIES = 3
# valid_time stamps the source does not have: the EWDS constraints for Dec 2024 stop at the 30th, so the 2024 file has no
# 2025-01-01 step (365, not 366). Nothing else may be missing. Keep in step with src/data/08_glofas.py.
KNOWN_SOURCE_GAP_VALID_DATES = {"2025-01-01"}
MAX_RESUBMITS = 2  # a year whose server job failed/was dismissed is submitted again at most this many times

MONTHS = [f"{m:02d}" for m in range(1, 13)]
DAYS = [f"{d:02d}" for d in range(1, 32)]
RATE_LIMIT_WORDS = ("429", "403", "too many", "rate limit", "service protection", "limit", "quota", "rejected")


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def final_path(year):
    return os.path.join(OUT_DIR, f"glofas_kenya_{year}.nc")


def build_request(year):
    return {
        "system_version": ["version_4_0"],
        "hydrological_model": ["lisflood"],
        "product_type": ["consolidated"],
        "timespan": ["time_mean"],
        "variable": ["average_river_discharge_in_the_last_24_hours"],
        "year": [str(year)],
        "month": MONTHS,
        "day": DAYS,
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": [5.5, 33.5, -5.5, 42.5],
    }


def load_ids():
    try:
        with open(REQUESTS_JSON, encoding="utf-8") as f:
            return {int(k): v for k, v in json.load(f).items()}
    except (FileNotFoundError, ValueError):
        return {}


def save_ids(ids):
    tmp = REQUESTS_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in sorted(ids.items())}, f, indent=1)
    os.replace(tmp, REQUESTS_JSON)


def job_year(remote):
    """The year a server job covers, or None unless it is exactly our full-year request.

    A job is only re-used if it asks for all 12 months and all 31 day slots of one year, with the same
    variable, product, version and area as build_request(). (A one-day test job once slipped through a
    year-only check and produced a 55 KB "2020" file.)
    """
    req = remote.request
    inputs = req.get("inputs", req) if isinstance(req, dict) else {}
    years = inputs.get("year")
    if not (isinstance(years, list) and len(years) == 1):
        return None
    for key, expected in build_request(int(years[0])).items():
        got = inputs.get(key)
        if isinstance(expected, list):
            if not isinstance(got, list) or sorted(map(str, got)) != sorted(map(str, expected)):
                return None
        elif got != expected:
            return None
    return int(years[0])


def adopt_server_jobs(client, ids, years):
    """Look through the EWDS "Your requests" list and re-use jobs for years we still need.

    Preference per year: a finished job (download immediately), else the OLDEST queued/running job (best queue place).
    Jobs already in requests.json are kept as they are unless they are dead.
    """
    try:
        jobs = client.get_jobs(limit=200).json.get("jobs", [])
    except Exception as e:
        log(f"could not read the EWDS request list ({e!r}); continuing with requests.json only")
        return
    best = {}  # year -> (rank, created, job_id)
    for j in jobs:
        if j.get("processID") != COLLECTION or j["status"] not in ("successful", "accepted", "running"):
            continue
        try:
            y = job_year(client.get_remote(j["jobID"]))
        except Exception:
            continue
        if y not in years or os.path.exists(final_path(y)):
            continue
        rank = 0 if j["status"] == "successful" else 1
        key = (rank, j["created"])
        if y not in best or key < best[y][0]:
            best[y] = (key, j["jobID"], j["status"])
    for y, (_, jid, status) in sorted(best.items()):
        cur = ids.get(y)
        if cur and cur["id"] == jid:
            continue
        if cur:
            try:
                cur_status = client.get_remote(cur["id"]).status
            except Exception:
                cur_status = "unknown"
            if cur_status in ("successful", "accepted", "running") and not (status == "successful" and cur_status != "successful"):
                continue  # the one we already track is fine
        ids[y] = {"id": jid, "submitted": datetime.now().isoformat(timespec="seconds"), "source": f"adopted from EWDS list ({status})",
                  "resubmits": cur["resubmits"] if cur else 0}
        log(f"{y}: re-using existing EWDS job {jid[:8]} ({status})")
    save_ids(ids)


def missing_valid_dates(nc, year):
    """Dates a full-year file should hold (valid_time = request date + 1 day: Jan 2 of the year to Jan 1 of the next) but does not."""
    import netCDF4
    t = nc.variables["valid_time"]
    got = {d.strftime("%Y-%m-%d") for d in netCDF4.num2date(t[:], t.units, only_use_cftime_datetimes=False)}
    want = {d.strftime("%Y-%m-%d") for d in pd.date_range(f"{year}-01-02", f"{year + 1}-01-01")}
    return sorted(want - got)


def short_year_problem(nc, year):
    """None if the file is a full year (allowing only the known source gap), else a description of what is missing."""
    missing = [d for d in missing_valid_dates(nc, year) if d not in KNOWN_SOURCE_GAP_VALID_DATES]
    if not missing:
        return None
    return f"{len(missing)} valid_time day(s) missing, e.g. {missing[:3]}"


def download(remote, year):
    out = final_path(year)
    tmp = out + ".part"
    t0 = time.time()
    remote.download(tmp)  # streams to disk in chunks
    if os.path.exists(out):  # a manual download of this year landed meanwhile: keep it
        os.remove(tmp)
        log(f"{year}: file appeared during the download, kept the existing one")
        return
    import netCDF4
    with netCDF4.Dataset(tmp) as nc:  # header-only check: every day of the year must be there (bar the known source gap)
        problem = short_year_problem(nc, year)
    if problem:
        os.remove(tmp)
        raise RuntimeError(f"{year}: downloaded file is not a full year: {problem}")
    os.replace(tmp, out)  # only a complete download gets the final name
    log(f"{year}: downloaded {os.path.getsize(out) / 1e6:.1f} MB in {time.time() - t0:.0f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", type=int, default=1999)
    ap.add_argument("--last", type=int, default=2025)
    ap.add_argument("--window", type=int, default=8, help="year-requests kept on the server at once")
    ap.add_argument("--min-window", type=int, default=4, help="window after the server rejects a submission")
    ap.add_argument("--poll", type=int, default=150, help="seconds between polls")
    a = ap.parse_args()
    years = list(range(a.first, a.last + 1))
    todo = [y for y in years if not os.path.exists(final_path(y))]
    log(f"start: years {a.first}-{a.last}, {len(years) - len(todo)} already on disk, {len(todo)} to get; "
        f"window {a.window} (falls back to {a.min_window}), poll every {a.poll}s")
    client = cdsapi.Client(quiet=True).client  # ecmwf-datastores-client: submit() does not wait

    ids = {y: v for y, v in load_ids().items() if y in todo}
    if ids:
        log(f"requests.json: resuming {len(ids)} tracked request(s): {sorted(ids)}")
    adopt_server_jobs(client, ids, set(todo))

    window = a.window
    submit_fail = {}
    pending = list(todo)  # years not yet downloaded, ascending
    failed = []
    while pending:
        # 1. poll the outstanding requests, download the finished ones
        for y in [y for y in pending if y in ids]:
            info = ids[y]
            try:
                remote = client.get_remote(info["id"])
                status = remote.status
            except Exception as e:
                log(f"{y}: status check failed ({e!r}); will retry next poll")
                continue
            if status == "successful":
                for attempt in range(1, MAX_DOWNLOAD_TRIES + 1):
                    try:
                        download(remote, y)
                        break
                    except Exception as e:
                        log(f"{y}: download error (attempt {attempt}/{MAX_DOWNLOAD_TRIES}): {e!r}")
                        if os.path.exists(final_path(y) + ".part"):
                            os.remove(final_path(y) + ".part")
                if os.path.exists(final_path(y)):
                    pending.remove(y)
                    del ids[y]
                    save_ids(ids)
                else:
                    info["download_failures"] = info.get("download_failures", 0) + 1
                    if info["download_failures"] >= 3:
                        log(f"{y}: giving up after repeated download failures")
                        failed.append(y)
                        pending.remove(y)
                        del ids[y]
                        save_ids(ids)
            elif status in ("failed", "rejected", "dismissed", "deleted"):
                err = ""
                try:
                    err = str(remote.error)[:200]
                except Exception:
                    pass
                log(f"{y}: server job {info['id'][:8]} ended as {status} {err}")
                del ids[y]
                if info.get("resubmits", 0) >= MAX_RESUBMITS:
                    log(f"{y}: giving up after {MAX_RESUBMITS} resubmits")
                    failed.append(y)
                    pending.remove(y)
                else:
                    ids_resubmit[y] = info.get("resubmits", 0) + 1
                save_ids(ids)

        # 2. top the server queue up to the window with the next years
        queued = sum(1 for y in pending if y in ids)
        for y in pending:
            if queued >= window:
                break
            if y in ids or submit_fail.get(y, 0) >= MAX_SUBMIT_FAILURES:
                continue
            try:
                remote = client.submit(COLLECTION, build_request(y))
                ids[y] = {"id": remote.request_id, "submitted": datetime.now().isoformat(timespec="seconds"),
                          "source": "submitted by this script", "resubmits": ids_resubmit.pop(y, 0)}
                save_ids(ids)
                queued += 1
                submit_fail.pop(y, None)
                log(f"{y}: submitted, request {remote.request_id[:8]} ({queued}/{window} queued)")
            except Exception as e:
                text = repr(e).lower()
                if any(w in text for w in RATE_LIMIT_WORDS):
                    if window > a.min_window:
                        window = a.min_window
                        log(f"{y}: submission rejected ({e!r}); window lowered to {window}")
                    else:
                        log(f"{y}: submission rejected again ({e!r}); pausing submissions until the next poll")
                    break
                submit_fail[y] = max(submit_fail.get(y, 0), 0) + 1
                log(f"{y}: submit error {e!r} ({submit_fail[y]}/{MAX_SUBMIT_FAILURES})")
                if submit_fail[y] >= MAX_SUBMIT_FAILURES:
                    failed.append(y)

        pending = [y for y in pending if y not in failed]
        if not pending:
            break
        log(f"status: {len(todo) - len(pending)}/{len(todo)} downloaded, {sum(1 for y in pending if y in ids)} queued on the server, "
            f"{sum(1 for y in pending if y not in ids)} not yet submitted; next poll in {a.poll}s")
        time.sleep(a.poll)

    missing = [y for y in years if not os.path.exists(final_path(y))]
    log(f"SUMMARY: {len(years) - len(missing)}/{len(years)} years present. Missing: {missing if missing else 'none'}")
    validate(years)


ids_resubmit = {}  # year -> number of times it has been resubmitted (only needed between a failure and the next submit)


def validate(years):
    """Header-only check of each file. Runs only after every download has finished (never during)."""
    import netCDF4

    bad = []
    for y in years:
        p = final_path(y)
        if not os.path.exists(p):
            continue
        try:
            with netCDF4.Dataset(p) as nc:  # reads metadata, not the data array
                v = nc.variables.get("avg_dis")
                t = nc.variables.get("valid_time")
                if v is None or t is None:
                    bad.append((y, f"variables {list(nc.variables)}"))
                elif short_year_problem(nc, y):  # a truncated / test-size file
                    bad.append((y, short_year_problem(nc, y)))
                else:
                    gap = [d for d in missing_valid_dates(nc, y) if d in KNOWN_SOURCE_GAP_VALID_DATES]
                    log(f"validate {y}: avg_dis{v.shape}, {t.shape[0]} valid_time steps" + (f" (known source gap {gap})" if gap else ""))
        except Exception as e:  # unreadable / truncated file
            bad.append((y, repr(e)))
    log("VALIDATION: all present files readable with avg_dis + valid_time" if not bad else f"VALIDATION PROBLEMS: {bad}")


if __name__ == "__main__":
    import sys

    if "--validate-only" in sys.argv:
        validate(range(1999, 2026))
    else:
        main()
