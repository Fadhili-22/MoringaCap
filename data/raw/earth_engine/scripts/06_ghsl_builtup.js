// Output: ghsl_builtup_county_5yr.csv
var ghsl = ee.ImageCollection('JRC/GHSL/P2023A/GHS_BUILT_S').filterDate('2000-01-01', '2026-01-01').select('built_surface');
var res = ghsl.map(function (img) {
  return img.divide(10000).reduceRegions({collection: table, reducer: ee.Reducer.mean().setOutputs(['pct_built']), scale: 100, tileScale: 8})
    .map(function (f) { return f.set('year', img.date().get('year')).setGeometry(null); });
}).flatten();
Export.table.toDrive({collection: res, description: 'ghsl_builtup_county_5yr', fileFormat: 'CSV'});
