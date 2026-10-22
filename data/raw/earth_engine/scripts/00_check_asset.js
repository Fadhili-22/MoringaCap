// Import the county asset as `table`: projects/grounded-pager-478418-p6/assets/kenyan_counties
print('Number of counties:', table.size());           // 47
print('Field names:', table.first().propertyNames()); // COUNTYCO, FIRST_COUN, COUNT
Map.centerObject(table, 6);
Map.addLayer(table, {color: 'red'}, 'Counties');
