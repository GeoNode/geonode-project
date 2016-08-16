FROM terranodo/django:development
MAINTAINER Ariel Núñez<ariel@terranodo.io>
ONBUILD COPY /usr/src/app/  . 
