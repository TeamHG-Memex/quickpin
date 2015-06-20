from os import path, environ

def application(env, res):
	activate_this = path.dirname(path.realpath(__file__)) + '/venv/bin/activate_this.py'
	execfile(activate_this, dict(__file__=activate_this))

	for key in ['APPLICATION_ENV']:
		environ[key] = env.get(key, '')

	from app import app

	return app(env, res)
