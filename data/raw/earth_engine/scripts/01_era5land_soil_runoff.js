// Output: era5land_soil_runoff_county_month.csv
var era5 = ee.ImageCollection('ECMWF/ERA5_LAND/MONTHLY_AGGR')
  .filterDate('1999-10-01', '2026-01-01')
  .select(['volumetric_soil_water_layer_1', 'volumetric_soil_water_layer_2',
           'surface_runoff_sum', 'runoff_sum']);
var results = era5.map(function (img) {
  var d = img.date();
  return img.reduceRegions({collection: table, reducer: ee.Reducer.mean(), scale: 1000, tileScale: 4})
    .map(function (f) { return f.set({year: d.get('year'), month: d.get('month')}).setGeometry(null); });
}).flatten();
Export.table.toDrive({collection: results, description: 'era5land_soil_runoff_county_month', fileFormat: 'CSV'});
