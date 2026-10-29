# Data sources

Group 6, Kenya County Flood Risk Early Warning (Moringa DSF-PT15). How each input is used is in `data/DATA_DICTIONARY.md`.
**Check the DOIs and citations marked (†) before submitting: they were written from memory, not copied from the data files.**
The GloFAS DOI and the ERSSTv6 references were taken from the project's own files/brief.

## Rainfall, vegetation, climate indices
- **CHIRPS rainfall**: Climate Hazards Group InfraRed Precipitation with Station data, distributed as the WFP/HDX subnational dekadal rainfall file `ken-rainfall-subnat-full.csv` (column `rfh`). Funk, C. et al. (2015), *Scientific Data* 2, 150066, doi:10.1038/sdata.2015.66 (†). Dataset: WFP, via the Humanitarian Data Exchange (data.humdata.org).
- **WFP NDVI**: WFP/HDX subnational vegetation index file `ken-ndvi-subnat-full.csv` (column `vim`), via the Humanitarian Data Exchange.
- **NOAA ONI**: Oceanic Nino Index from NOAA Climate Prediction Center, served by NOAA PSL, https://psl.noaa.gov/data/timeseries/month/ (`oni.csv`; missing = -9999).
- **DMI (Indian Ocean Dipole)**: Dipole Mode Index from ERSSTv6 (`dmi_ersstv6.txt`; WTIO - SETIO, climatology 1991-2020). Huang, B. et al. (2025), ERSSTv6 Part I, *J. Climate* 38, 1105-1121, doi:10.1175/JCLI-D-23-0707.1; Part II, *J. Climate* 38, 1123-1136, doi:10.1175/JCLI-D-24-0185.1.

## Reanalysis, hydrology and land surface (Google Earth Engine exports; scripts in `data/raw/earth_engine/scripts/`)
- **ERA5-Land**: ECMWF/Copernicus Climate Change Service, monthly aggregates (`ECMWF/ERA5_LAND/MONTHLY_AGGR`): soil moisture layers 1-2 and runoff. Muñoz-Sabater, J. et al. (2021), *Earth Syst. Sci. Data* 13, 4349-4383, doi:10.5194/essd-13-4349-2021 (†). Contains modified Copernicus Climate Change Service information.
- **SRTM**: NASA/USGS Shuttle Radar Topography Mission, 1 arc-second v3 (`USGS/SRTMGL1_003`). Farr, T. G. et al. (2007), *Reviews of Geophysics* 45, RG2004, doi:10.1029/2005RG000183 (†).
- **ESA WorldCover 2021 (v200)**: Zanaga, D. et al. (2022), doi:10.5281/zenodo.7254221 (†). Licence CC BY 4.0.
- **Rivers and surface water**: WWF HydroSHEDS Free Flowing Rivers network (Grill, G. et al. 2019, *Nature* 569, 215-221, doi:10.1038/s41586-019-1111-9 (†)); JRC Global Surface Water v1.4 (Pekel, J.-F. et al. 2016, *Nature* 540, 418-422, doi:10.1038/nature20584 (†)).
- **GHSL built-up surface**: European Commission JRC, GHS-BUILT-S R2023A (`JRC/GHSL/P2023A/GHS_BUILT_S`), epochs 2000-2025 (the 2025 epoch is a modelled projection in this release (†)). Pesaresi, M. and Politis, P. (2023), doi:10.2905/9F06F36F-4B11-47EC-ABB0-4F8B7B1F88F6 (†).
- **GloFAS v4.0 river discharge**: Copernicus Emergency Management Service (CEMS), GloFAS v4.0 historical (consolidated) reanalysis, variable `average_river_discharge_in_the_last_24_hours`, downloaded from the Early Warning Data Store (`cems-glofas-historical`). **DOI 10.24381/cds.a4fdd6b9**. Contains modified Copernicus Emergency Management Service information.

## Boundaries and population
- **OCHA COD-AB Kenya administrative boundaries** (admin-1 counties, version v01, valid 2019-10-31), UN OCHA Common Operational Datasets via the Humanitarian Data Exchange. Licence **CC BY-IGO** (Creative Commons Attribution for Intergovernmental Organisations). Used as `data/raw/boundaries/cod_ab/`; the land-only version `kenya_counties_cod_land.shp` is derived from it by removing large lakes, and is released under the same licence terms with this attribution.
- **Natural Earth 10m Lakes v5.0.0** (`ne_10m_lakes`), naturalearthdata.com, public domain. Used only to cut Lake Victoria, Lake Turkana and Lake Natron out of the county polygons.
- **KNBS 2019 Kenya Population and Housing Census**: county population (2019) and county land area, Kenya National Bureau of Statistics, via `data/raw/population/county_year_population.csv`. Only the 2019 row is used (`pop_density`). The legacy DesInventar polygons (`data/raw/boundaries/lev_0.*`) are kept for reference and are used only where a `*_cod.csv` export has not yet been run.

## Flood labels
- **DesInventar**: UNDRR DesInventar Sendai disaster-loss database, Kenya flood records (https://www.desinventar.net), reshaped to county-month in `data/processed/desinventar_floods_county_month.csv`.
- **EM-DAT**: EM-DAT, CRED / UCLouvain, Brussels, Belgium, www.emdat.be, custom request of 2026-10-20. **Licence: the EM-DAT terms of use (https://doc.emdat.be/docs/legal/terms-of-use/) prohibit redistributing the data or derivative databases. It is NOT redistributed in this repository.** The raw file, the full model table, the EM-DAT place lookup and the full build report live only in `data/raw/flood_labels/emdat/` (git-ignored) and `data/private/` (git-ignored). The public table `data/processed/model_table_public.csv` is built without EM-DAT.
- **DFO**: Brakenridge, G. R., Global Active Archive of Large Flood Events, Dartmouth Flood Observatory, University of Colorado (master list of 2019-04-18), http://floodobservatory.colorado.edu/ (†).
- **Global Flood Database**: Cloud to Street / Dartmouth Flood Observatory (Tellman, B. et al. 2021, *Nature* 596, 80-86, doi:10.1038/s41586-021-03695-w (†)); county-level flooded area from the project's Earth Engine export `kenya_gfd_county_floods.csv`. GFD events share `dfo_id` with the DFO archive, so they count as one source.
