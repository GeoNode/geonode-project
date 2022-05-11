
#!/usr/bin/env bash
# this is the testproject script to create an testproject canary project.

source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
mkvirtualenv --python=/usr/bin/python3 testproject
pip install Django==3.2
rm -rf testproject
django-admin startproject --template=/home/vagrant/geonode-project -e py,sh,md,rst,json,yml,ini,env,sample,properties -n monitoring-cron -n Dockerfile testproject
cd /home/vagrant/testproject
python create-envfile.py --geonodepwd geonode \
  --geoserverpwd geoserver \
  --pgpwd postgres \
  --dbpwd geonode \
  --geodbpwd geonode
sed -i 's/GEOSERVER_WEB_UI_LOCATION=http:\/\/localhost\/geoserver\//GEOSERVER_WEB_UI_LOCATION=http:\/\/localhost:8888\/geoserver\//' .env
sed -i 's/GEOSERVER_PUBLIC_LOCATION=http:\/\/localhost\/geoserver\//GEOSERVER_PUBLIC_LOCATION=http:\/\/localhost:8888\/geoserver\//' .env
sed -i 's/SITEURL=.*/SITEURL=http:\/\/localhost:8888\//' .env
sed -i 's/GEONODE_LB_PORT=80/GEONODE_LB_PORT=8888/' .env
chown -R vagrant:vagrant /home/vagrant/testproject
sudo docker-compose build
sudo docker-compose up -d
