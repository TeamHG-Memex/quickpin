# Quick Started

## Installation

### Requirement

- Memory: 4GB or more (EC2 `t2.medium` or larger)

### For Ubuntu Server 14.04 (clean install)

    cd ~
    sudo apt-get update
    sudo apt-get install -y git
    # Obtain your private key and ssh-add it (unless you already have ssh forward agent)
    git clone git@github.com:TeamHG-Memex/quickpin.git
    sh ~/quickpin/install/setup.sh

## Running

### Development-mode

- Set environment variable: `export APPLICATION_ENV=development`
- Run development server: `python app.py`
- Browse to http://localhost:5000/ with **Dartium**

### Production-mode

- Setup Apache & WSGI pointing to: `application.wsgi`
- Build Dart: `cd static/dart & pub build`
- Browse to http://localhost/ with **Chrome**

### For Ubuntu Server 14.04 (using setup script above)

- Simply browse to http://localhost/ with **Chrome**.
- When code are changed, refresh production server with `cd static/dart & pub build`
- To run development server: `source venv/bin/activate; APPLICATION_ENV=development python app.py`
- Browse to http://localhost:5000/ with **Dartium**
