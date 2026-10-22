// Output: proximity_rivers_water_county.csv
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
Export.table.toDrive({collection: res, description: 'proximity_rivers_water_county', fileFormat: 'CSV'});
