from flask import Blueprint, request, jsonify
from db_adapter import DbAdapter
import json
from bson.objectid import ObjectId

subjectBlueprint = Blueprint('subject', __name__)
client = DbAdapter.connect()
db = client.subjects

@subjectBlueprint.route('/')
def list():
	results = []
	for subject in db.find():
		subject['_id'] = str(subject['_id'])
		results.append(subject)
	return json.dumps(results)

@subjectBlueprint.route('/<string:oid>')
def get(oid):
	result = db.find_one({'_id': ObjectId(oid)})
	result['_id'] = str(result['_id'])
	return json.dumps(result)

@subjectBlueprint.route('/byUsername/<string:username>')
def findByUsername(username):
	result = db.find_one({'username': username})
	result['_id'] = str(result['_id'])
	return json.dumps(result)

@subjectBlueprint.route('/<string:oid>', methods=['POST'])
def update(oid):
	print(request.json)
	db.update({'_id': ObjectId(oid)}, {'$set': request.json})
	return jsonify(success=True)
