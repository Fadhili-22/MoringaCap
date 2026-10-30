# GloFAS river discharge (Kenya, 1999-2025)

Daily river discharge used by `src/data/08_glofas.py` to build `discharge_rank` and `discharge_rank_lag1`.

## Source and licence
- **Dataset:** Copernicus Emergency Management Service (CEMS), GloFAS v4.0 historical (consolidated) reanalysis, `cems-glofas-historical`, served by the Early Warning Data Store (EWDS) at https://ewds.climate.copernicus.eu.
- **DOI:** 10.24381/cds.a4fdd6b9
- **Licence:** CEMS-FLOODS datasets licence (accept it on the dataset's download page before the first request; see below). Attribution: "Contains modified Copernicus Emergency Management Service information".
- Full citation list: `SOURCES.md` at the repo root.

## The request
One request per year (the form allows one year at a time), Kenya bounding box (north, west, south, east = 5.5, 33.5, -5.5, 42.5):

```python
{
    "system_version": ["version_4_0"],
    "hydrological_model": ["lisflood"],
    "product_type": ["consolidated"],
    "timespan": ["time_mean"],
    "variable": ["average_river_discharge_in_the_last_24_hours"],
    "year": ["<YYYY>"],
    "month": ["01", ..., "12"],
    "day": ["01", ..., "31"],
    "data_format": "netcdf",
    "download_format": "unarchived",
    "area": [5.5, 33.5, -5.5, 42.5],
}
```

The file holds the variable `avg_dis` and a `valid_time` axis. Each daily value is the mean for the day *before* `valid_time`; `08_glofas.py` shifts the date by one day. So each file runs from 2 January of its year to 1 January of the next, and the 2025 file covers all of 2025.

**Known source gap.** ECMWF has no data for the 2024-12-31 request (the EWDS list of available days for December 2024 stops at the 30th), so `glofas_kenya_2024.nc` has 365 steps instead of 366 and no `valid_time` 2025-01-01. The downloader and `08_glofas.py` allow exactly that one date; any other missing day is an error. December 2024 is therefore a mean over 30 of 31 days.

## What is in this folder
- `glofas_kenya_<year>.nc`, one file per year, about 7-9 MB each. **The `.nc` files are NOT in the repo** (git-ignored); download them as below or get them from the team's shared drive.
- `scripts/download_glofas.py`, the downloader.
- `requests.json` and `download_log.txt` are written while downloading and are git-ignored.

## How to run the downloader
1. Create a free account at https://ewds.climate.copernicus.eu and copy your personal access token from your profile page.
2. Create `%USERPROFILE%\.cdsapirc` (Windows) or `~/.cdsapirc` with:
   ```
   url: https://ewds.climate.copernicus.eu/api
   key: <your-personal-access-token>
   ```
   Use the EWDS URL above, not the old `cds.climate.copernicus.eu` one.
3. Open the `cems-glofas-historical` dataset page on the EWDS site, go to **Download**, and accept the CEMS-FLOODS licence at the bottom of the form once. Without this, requests are rejected.
4. Install the client: `pip install cdsapi netCDF4` (see the root `requirements.txt` for the rest of the pipeline).
5. From the repo root:
   ```
   python data/raw/glofas/scripts/download_glofas.py --first 1999 --last 2025
   ```
   Options: `--window 8` (year-requests kept queued on the server at once), `--min-window 4` (used if the server starts rejecting submissions), `--poll 150` (seconds between status checks), `--validate-only` (header check of the files already on disk).

The files are small; the wait is ECMWF's queue, and **the queue can take many hours** for the full 27 years. The script submits without blocking, stores every request ID in `requests.json`, and polls. If it is stopped it can be started again with the same command: it resumes the stored requests and re-uses jobs already listed under "Your requests" on the EWDS site instead of submitting them again, and years that already have a file are skipped. Each download is written to `<file>.part` and renamed only when complete. When all years are in, it checks every file has `avg_dis` and `valid_time`.

## After downloading
Rebuild the table so `discharge_rank` is filled: `python src/data/build_model_table.py` (or only `08_glofas` through `13_outputs`).
