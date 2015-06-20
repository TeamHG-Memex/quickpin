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

### For Ubuntu Server 14.04 (clean install)
```
cd ~
sudo apt-get update
sudo apt-get install -y git
# Obtain your private key and ssh-add it (unless you already have ssh forward agent)
git clone git@github.com:TeamHG-Memex/quickpin.git
sh ~/quickpin/install/setup.sh
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
