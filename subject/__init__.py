from flask import Blueprint, request, jsonify
from db_adapter import DbAdapter
import json
from bson.objectid import ObjectId
import scraper
import os

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

@subjectBlueprint.route('/', methods=['PUT'])
def add():
	# @TODO put path in config file
	template_path = os.path.dirname(scraper.__file__) + "/twitter_profile.tpl"

	screenNames = request.data.split('\n')
	for screenName in screenNames:
		result = scraper.Scraper.load(template_path).extract(screenName)

		# @TODO find an elegant way to group these attributes
		twitterDict = {}
		for key in result:
			if 'twitter.' in key:
				twitterDict[key.replace('twitter.', '')] = result[key]
		result['twitter'] = twitterDict

		tweetsDict = {}
		for key in twitterDict:
			if 'tweets.' in key:
				tweetsDict[key.replace('tweets.', '')] = twitterDict[key]
			del result['twitter.' + key]
		twitterDict['tweets'] = tweetsDict

		for key in tweetsDict:
			del twitterDict['tweets.' + key]

		db.update({'username': screenName}, {'$set': result}, upsert=True)
	return jsonify(success=True)

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
