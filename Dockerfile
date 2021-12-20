FROM fkrull/multi-python:latest

WORKDIR /home/django-freeipa-auth

RUN pip3 install tox

COPY . .
