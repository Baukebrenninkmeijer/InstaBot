FROM python:3.7-slim-stretch
COPY ./requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt

RUN apt-get update && apt-get install -y --no-install-recommends apt-utils
RUN apt-get -y install libglib2.0-0 libsm6 libxext6 libxrender-dev
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY . /app
WORKDIR /app
RUN python -m spacy download en
ENTRYPOINT python runner.py
