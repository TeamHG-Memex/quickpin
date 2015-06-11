from flask import Blueprint, Flask, render_template, send_from_directory, send_file
from subject import subjectBlueprint

app = Flask(__name__, template_folder='static/dart/web')

# @TODO move paths to config file
devBlueprint = Blueprint('dart', __name__, static_url_path='', static_folder='static/dart')
@devBlueprint.route('/packages/<path:filename>')
def fetch_dev_packages(filename):
	return send_from_directory('static/dart/web/packages', filename)

prodBlueprint = Blueprint('js', __name__, static_url_path='', static_folder='static/dart/build')
@prodBlueprint.route('/packages/<path:filename>')
def fetch_prod_packages(filename):
	return send_from_directory('static/dart/build/web/packages', filename)

# @TODO determine development mode from environment variable
app.register_blueprint(devBlueprint)
app.register_blueprint(subjectBlueprint, url_prefix='/api/subject')

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
	return send_file('static/favicon.ico')

if __name__ == '__main__':
	app.run(debug=True)
