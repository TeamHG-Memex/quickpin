from flask import Blueprint, Flask, render_template, send_from_directory, send_file, redirect
from subject import subjectBlueprint
from os import getenv

# Determine development mode from environment variable
debug_mode = (getenv('APPLICATION_ENV') == 'development')

app = Flask(__name__, template_folder='static/dart/web')

# @TODO move paths to config file
devBlueprint = Blueprint('dart', __name__, static_url_path='', static_folder='static/dart')
@devBlueprint.after_request
def add_header(response):
	response.cache_control.max_age = 0
	return response
@devBlueprint.route('/packages/<path:filename>')
def fetch_dev_packages(filename):
	return send_from_directory('static/dart/web/packages', filename)

prodBlueprint = Blueprint('js', __name__, static_url_path='', static_folder='static/dart/build')
@prodBlueprint.route('/packages/<path:filename>')
def fetch_prod_packages(filename):
	return send_from_directory('static/dart/build/web/packages', filename)

app.register_blueprint(devBlueprint if debug_mode else prodBlueprint)
app.register_blueprint(subjectBlueprint, url_prefix='/api/subject')

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
	return send_file('static/favicon.ico')

@app.route('/hashtag/<string:hashtagString>')
def hashtag(hashtagString):
	return redirect('https://twitter.com/hashtag/' + hashtagString, code=301)

if __name__ == '__main__':
	app.run(debug=debug_mode, host='0.0.0.0' if debug_mode else '127.0.0.1')
