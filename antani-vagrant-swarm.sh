
#!/usr/bin/env bash
# this is the antani script to create an antani canary project.
sudo docker swarm init
source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
mkvirtualenv --python=/usr/bin/python3 antani
pip install Django==3.2
rm -rf antani
django-admin startproject --template=/home/vagrant/geonode-project -e py,sh,md,rst,json,yml,ini,env,sample,properties -n monitoring-cron -n Dockerfile antani
cd /home/vagrant/antani
cp .env.sample .env
sed -i 's/GEOSERVER_WEB_UI_LOCATION=http:\/\/localhost\/geoserver\//GEOSERVER_WEB_UI_LOCATION=http:\/\/localhost:8888\/geoserver\//' .env
sed -i 's/GEOSERVER_PUBLIC_LOCATION=http:\/\/localhost\/geoserver\//GEOSERVER_PUBLIC_LOCATION=http:\/\/localhost:8888\/geoserver\//' .env
sed -i 's/SITEURL=.*/SITEURL=http:\/\/localhost:8888\//' .env
sed -i 's/GEONODE_LB_PORT=80/GEONODE_LB_PORT=8888/' .env
sed -i "s/OAUTH2_CLIENT_ID=.*/OAUTH2_CLIENT_ID=$(pwgen 30 -1)/" .env
sed -i "s/OAUTH2_CLIENT_SECRET=.*/OAUTH2_CLIENT_SECRET=$(pwgen 80 -1)/" .env
sed -i "s/SECRET_KEY=.*/SECRET_KEY=$(pwgen 50 -1)/" .env
chown -R vagrant:vagrant /home/vagrant/antani
sudo docker-compose -f ./geonode-stack.yml build
sudo docker stack deploy -c ./geonode-stack.yml geonode-stack
