from pymongo import MongoClient

class DbAdapter:
	client = None
	
	@staticmethod
	def connect():
		if DbAdapter.client == None:
			DbAdapter.client = MongoClient()
		return DbAdapter.client.quickpin