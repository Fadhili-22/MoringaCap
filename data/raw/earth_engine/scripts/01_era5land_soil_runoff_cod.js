// Output: era5land_soil_runoff_county_month_cod.csv
// Boundaries: OCHA COD-AB Kenya admin-1 with Lake Victoria, Lake Turkana and Lake Natron cut out (land-only;
// small lakes and dams stay in). Source file: data/raw/boundaries/cod_ab/kenya_counties_cod_land.shp.
// No `table` import is needed (remove the old `table` import from the Code Editor if it is still there).
// Output rows are keyed by `pcode` (KE001-KE047) instead of COUNTYCO; every calculation below is unchanged.
var table = ee.FeatureCollection('projects/grounded-pager-478418-p6/assets/kenya_counties_cod_land')
  .select(['pcode', 'county']);
print('Counties:', table.size(), table.first().propertyNames());  // expect 47 and [pcode, county]
var era5 = ee.ImageCollection('ECMWF/ERA5_LAND/MONTHLY_AGGR')
  .filterDate('1999-10-01', '2026-01-01')
  .select(['volumetric_soil_water_layer_1', 'volumetric_soil_water_layer_2',
           'surface_runoff_sum', 'runoff_sum']);
var results = era5.map(function (img) {
  var d = img.date();
  return img.reduceRegions({collection: table, reducer: ee.Reducer.mean(), scale: 1000, tileScale: 4})
    .map(function (f) { return f.set({year: d.get('year'), month: d.get('month')}).setGeometry(null); });
}).flatten();
Export.table.toDrive({collection: results, description: 'era5land_soil_runoff_county_month_cod', fileFormat: 'CSV'});
