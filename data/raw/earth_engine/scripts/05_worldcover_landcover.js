// Output: worldcover_landcover_county.csv
var wc = ee.ImageCollection('ESA/WorldCover/v200').first().select('Map');
var classes = {tree: 10, shrub: 20, grass: 30, crop: 40, built: 50, bare: 60, water: 80, wetland: 90, mangrove: 95};
var bands = Object.keys(classes).map(function (k) { return wc.eq(classes[k]).rename('pct_' + k); });
var res = ee.Image.cat(bands).reduceRegions({collection: table, reducer: ee.Reducer.mean(), scale: 100, tileScale: 8})
  .map(function (f) { return f.set('area_km2', f.geometry().area(100).divide(1e6)).setGeometry(null); });
Export.table.toDrive({collection: res, description: 'worldcover_landcover_county', fileFormat: 'CSV'});
