// Output: worldcover_landcover_county_cod.csv
// Boundaries: OCHA COD-AB Kenya admin-1 with Lake Victoria, Lake Turkana and Lake Natron cut out (land-only;
// small lakes and dams stay in). Source file: data/raw/boundaries/cod_ab/kenya_counties_cod_land.shp.
// No `table` import is needed (remove the old `table` import from the Code Editor if it is still there).
// Output rows are keyed by `pcode` (KE001-KE047) instead of COUNTYCO; every calculation below is unchanged.
var table = ee.FeatureCollection('projects/grounded-pager-478418-p6/assets/kenya_counties_cod_land')
  .select(['pcode', 'county']);
print('Counties:', table.size(), table.first().propertyNames());  // expect 47 and [pcode, county]
var wc = ee.ImageCollection('ESA/WorldCover/v200').first().select('Map');
var classes = {tree: 10, shrub: 20, grass: 30, crop: 40, built: 50, bare: 60, water: 80, wetland: 90, mangrove: 95};
var bands = Object.keys(classes).map(function (k) { return wc.eq(classes[k]).rename('pct_' + k); });
var res = ee.Image.cat(bands).reduceRegions({collection: table, reducer: ee.Reducer.mean(), scale: 100, tileScale: 8})
  .map(function (f) { return f.set('area_km2', f.geometry().area(100).divide(1e6)).setGeometry(null); });
Export.table.toDrive({collection: res, description: 'worldcover_landcover_county_cod', fileFormat: 'CSV'});
