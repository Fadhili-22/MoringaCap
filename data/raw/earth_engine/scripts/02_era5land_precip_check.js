// Output: era5land_precip_county_month.csv (diagnostic only; the delivered file was run before setOutputs was added, so its column is `mean`)
var era5p = ee.ImageCollection('ECMWF/ERA5_LAND/MONTHLY_AGGR')
  .filterDate('1999-10-01', '2026-01-01')
  .select(['total_precipitation_sum']);
var results = era5p.map(function (img) {
  var d = img.date();
  return img.reduceRegions({collection: table, reducer: ee.Reducer.mean().setOutputs(['era5_precip_m']), scale: 1000, tileScale: 4})
    .map(function (f) { return f.set({year: d.get('year'), month: d.get('month')}).setGeometry(null); });
}).flatten();
Export.table.toDrive({collection: results, description: 'era5land_precip_county_month', fileFormat: 'CSV'});
