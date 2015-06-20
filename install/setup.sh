sudo sh -c 'curl https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -'
sudo apt-add-repository -y 'deb [arch=amd64] https://storage.googleapis.com/download.dartlang.org/linux/debian stable main'
sudo apt-get update
sudo apt-get install -y mongodb dart python python-pip python-dev libffi-dev libssl-dev libxml2-dev libxslt1-dev
sudo ln -s /usr/lib/dart/bin/pub /usr/bin
cd ~/quickpin
sudo pip install virtualenv
virtualenv venv
source venv/bin/activate
pip install -r install/python-dependencies.txt
cd ~/quickpin/static/dart
pub get
pub build
