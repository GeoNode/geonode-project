
#!/usr/bin/env bash
# this is the generated-project script to create an generated-project canary project.
sudo docker swarm init
source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
mkvirtualenv --python=/usr/bin/python3 generated-project
pip install Django==3.2.16
rm -rf generated-project
django-admin startproject --template=/home/vagrant/geonode-project -e py,sh,md,rst,json,yml,ini,env,sample,properties -n monitoring-cron -n Dockerfile generated-project
cd /home/vagrant/generated-project
python create-envfile.py --geonodepwd geonode \
  --geoserverpwd geoserver \
  --pgpwd postgres \
  --dbpwd geonode \
  --geodbpwd geonode
sed -i 's/GEOSERVER_WEB_UI_LOCATION=http:\/\/localhost\/geoserver\//GEOSERVER_WEB_UI_LOCATION=http:\/\/localhost:8888\/geoserver\//' .env
sed -i 's/GEOSERVER_PUBLIC_LOCATION=http:\/\/localhost\/geoserver\//GEOSERVER_PUBLIC_LOCATION=http:\/\/localhost:8888\/geoserver\//' .env
sed -i 's/SITEURL=.*/SITEURL=http:\/\/localhost:8888\//' .env
sed -i 's/GEONODE_LB_PORT=80/GEONODE_LB_PORT=8888/' .env
chown -R vagrant:vagrant /home/vagrant/generated-project
sudo docker-compose -f ./geonode-stack.yml build
sudo docker stack deploy -c ./geonode-stack.yml geonode-stack
