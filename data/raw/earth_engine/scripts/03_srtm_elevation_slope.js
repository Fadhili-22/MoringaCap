// Output: srtm_elevation_slope_county.csv
var dem = ee.Image('USGS/SRTMGL1_003').select('elevation');
var slope = ee.Terrain.slope(dem).rename('slope');
var flat = slope.lt(2).rename('pct_flat');
var step1 = dem.addBands(slope).addBands(flat).reduceRegions({collection: table, reducer: ee.Reducer.mean(), scale: 90, tileScale: 4});
var step2 = dem.reduceRegions({collection: step1, reducer: ee.Reducer.minMax().combine(ee.Reducer.stdDev(), '', true), scale: 90, tileScale: 4})
  .map(function (f) { return f.setGeometry(null); });
Export.table.toDrive({collection: step2, description: 'srtm_elevation_slope_county', fileFormat: 'CSV'});
