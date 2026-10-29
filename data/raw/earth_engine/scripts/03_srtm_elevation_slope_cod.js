// Output: srtm_elevation_slope_county_cod.csv
// Boundaries: OCHA COD-AB Kenya admin-1 with Lake Victoria, Lake Turkana and Lake Natron cut out (land-only;
// small lakes and dams stay in). Source file: data/raw/boundaries/cod_ab/kenya_counties_cod_land.shp.
// No `table` import is needed (remove the old `table` import from the Code Editor if it is still there).
// Output rows are keyed by `pcode` (KE001-KE047) instead of COUNTYCO; every calculation below is unchanged.
var table = ee.FeatureCollection('projects/grounded-pager-478418-p6/assets/kenya_counties_cod_land')
  .select(['pcode', 'county']);
print('Counties:', table.size(), table.first().propertyNames());  // expect 47 and [pcode, county]
var dem = ee.Image('USGS/SRTMGL1_003').select('elevation');
var slope = ee.Terrain.slope(dem).rename('slope');
var flat = slope.lt(2).rename('pct_flat');
var step1 = dem.addBands(slope).addBands(flat).reduceRegions({collection: table, reducer: ee.Reducer.mean(), scale: 90, tileScale: 4});
var step2 = dem.reduceRegions({collection: step1, reducer: ee.Reducer.minMax().combine(ee.Reducer.stdDev(), '', true), scale: 90, tileScale: 4})
  .map(function (f) { return f.setGeometry(null); });
Export.table.toDrive({collection: step2, description: 'srtm_elevation_slope_county_cod', fileFormat: 'CSV'});
