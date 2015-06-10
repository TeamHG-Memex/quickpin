from flask import Blueprint, send_file

subjectBlueprint = Blueprint('subject', __name__)
@subjectBlueprint.route('/')
def list():
	return send_file('samples/subjects.json')