
#!/usr/bin/env bash
# this is the antani script to create an antani canary project.

source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
mkvirtualenv --python=/usr/bin/python3 antani
pip install Django==3.2
rm -rf antani
django-admin startproject --template=/home/vagrant/geonode-project -e py,sh,md,rst,json,yml,ini,env,sample,properties -n monitoring-cron -n Dockerfile antani
cd /home/vagrant/antani
cp .env.sample .env
chown -R vagrant:vagrant /home/vagrant/antani
sudo docker-compose build
sudo docker-compose up -d
