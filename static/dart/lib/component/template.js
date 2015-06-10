var fs = require('fs');
var componentName = process.argv.pop().split(' ');
function toTitleCase(string) {
	return string.charAt(0).toUpperCase() + string.substr(1).toLowerCase();
}
function toLowerCase(string) {
	return string.toLowerCase();
}
function toUpperCase(string) {
	return string.toUpperCase();
}

fs.readFile('my-template.dart.template', {'encoding': 'utf8'}, function(error, data) {
	var result = data
		.replace(/my_template/g, componentName.map(toLowerCase).join('_'))
		.replace(/my-template/g, componentName.map(toLowerCase).join('-'))
		.replace(/MyTemplate/g, componentName.map(toTitleCase).join(''))
	;
	fs.writeFileSync(componentName.map(toLowerCase).join('-') + '.dart', result);
	fs.writeFileSync(componentName.map(toLowerCase).join('-') + '.html', '');
	fs.writeFileSync(componentName.map(toLowerCase).join('-') + '.css', '');
});

fs.readFile('../app.dart', { 'encoding': 'utf8' }, function (error, data) {
	var result = data
		.replace('// import components here', [
		'// import components here',
		"import 'packages:quickpin/component/" + componentName.map(toLowerCase).join('-') + ".dart';"
		].join("\n"))
		.replace('// bind components here', [
		'// bind components here',
		'    bind(' + componentName.map(toTitleCase).join('') + 'Component);'
		].join("\n"))
	;
	fs.writeFileSync('../app.dart', result);
});

fs.readFile('../../pubspec.yaml', { 'encoding': 'utf8' }, function (error, data) {
	var result = data
		.replace('    html_files:', [
		'    html_files:',
		'      - lib/component/' + componentName.map(toLowerCase).join('-') + '.html'
		].join("\n"))
	;
	fs.writeFileSync('../../pubspec.yaml', result);
});
