// Output: proximity_rivers_water_county_cod.csv
// Boundaries: OCHA COD-AB Kenya admin-1 with Lake Victoria, Lake Turkana and Lake Natron cut out (land-only;
// small lakes and dams stay in). Source file: data/raw/boundaries/cod_ab/kenya_counties_cod_land.shp.
// No `table` import is needed (remove the old `table` import from the Code Editor if it is still there).
// Output rows are keyed by `pcode` (KE001-KE047) instead of COUNTYCO; every calculation below is unchanged.
var table = ee.FeatureCollection('projects/grounded-pager-478418-p6/assets/kenya_counties_cod_land')
  .select(['pcode', 'county']);
print('Counties:', table.size(), table.first().propertyNames());  // expect 47 and [pcode, county]
var kenya = table.geometry().bounds();
var rivers = ee.FeatureCollection('WWF/HydroSHEDS/v1/FreeFlowingRivers')
  .filterBounds(kenya).filter(ee.Filter.gte('UPLAND_SKM', 1000));
var riverDist = rivers.distance(5000).unmask(5000).rename('river_dist_m');
var gsw = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence').unmask(0);
var water = gsw.gte(50);
var waterDist = water.distance(ee.Kernel.euclidean(5000, 'meters')).unmask(5000).rename('water_dist_m');
var occasional = gsw.gt(0).and(gsw.lt(50)).rename('pct_occasional_water');
var stack = ee.Image.cat([riverDist, riverDist.lte(1000).rename('pct_within_1km_river'),
  riverDist.lte(5000 - 1).rename('pct_within_5km_river'), waterDist,
  waterDist.lte(1000).rename('pct_within_1km_water'), water.rename('pct_water'), occasional]);
var res = stack.reduceRegions({collection: table, reducer: ee.Reducer.mean(), scale: 100, tileScale: 8})
  .map(function (f) { return f.setGeometry(null); });
Export.table.toDrive({collection: res, description: 'proximity_rivers_water_county_cod', fileFormat: 'CSV'});
