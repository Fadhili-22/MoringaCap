// Output: ghsl_builtup_county_5yr_cod.csv
// Boundaries: OCHA COD-AB Kenya admin-1 with Lake Victoria, Lake Turkana and Lake Natron cut out (land-only;
// small lakes and dams stay in). Source file: data/raw/boundaries/cod_ab/kenya_counties_cod_land.shp.
// No `table` import is needed (remove the old `table` import from the Code Editor if it is still there).
// Output rows are keyed by `pcode` (KE001-KE047) instead of COUNTYCO; every calculation below is unchanged.
var table = ee.FeatureCollection('projects/grounded-pager-478418-p6/assets/kenya_counties_cod_land')
  .select(['pcode', 'county']);
print('Counties:', table.size(), table.first().propertyNames());  // expect 47 and [pcode, county]
var ghsl = ee.ImageCollection('JRC/GHSL/P2023A/GHS_BUILT_S').filterDate('2000-01-01', '2026-01-01').select('built_surface');
var res = ghsl.map(function (img) {
  return img.divide(10000).reduceRegions({collection: table, reducer: ee.Reducer.mean().setOutputs(['pct_built']), scale: 100, tileScale: 8})
    .map(function (f) { return f.set('year', img.date().get('year')).setGeometry(null); });
}).flatten();
Export.table.toDrive({collection: res, description: 'ghsl_builtup_county_5yr_cod', fileFormat: 'CSV'});
