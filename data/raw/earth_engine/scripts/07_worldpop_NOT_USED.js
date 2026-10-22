// Output: worldpop_county_year.csv -> moved to _not_used/ (counts badly off vs 2019 census; see README)
var pop = ee.ImageCollection('WorldPop/GP/100m/pop').filter(ee.Filter.eq('country', 'KEN'));
var res = pop.map(function (img) {
  var y = img.get('year');
  return img.reduceRegions({collection: table, reducer: ee.Reducer.sum(), scale: 92.77, tileScale: 8})
    .map(function (f) { return f.set({year: y, population: f.get('sum')}).setGeometry(null); });
}).flatten();
Export.table.toDrive({collection: res, description: 'worldpop_county_year', fileFormat: 'CSV'});
