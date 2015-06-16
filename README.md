# Quick Started
## Installation
### Applications
- python 2.7 (*)
- mongodb 3 (*)
- dart_sdk (*)
- apache 2
- mod_wsgi
- dartinum

(*) required

### Python Modules
```
pip install -r install/python-dependencies.txt
```

## Running
### Development-mode
- Set environment variable: ```APPLICATION_ENV=development```
- Run development server: ```python app.py```
- Browse to http://localhost:5000/ with **Dartinum**

### Production-mode
- Setup Apache & WSGI pointing to: ```application.wsgi```
- Build Dart: ```cd static\dart & pub build```
- Browse to http://localhost/ with **Chrome**
