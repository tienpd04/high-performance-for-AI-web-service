FROM python:3.12-slim

ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get clean

# RUN apt-get install -y procps

RUN apt-get install -y curl


COPY ./requirements.txt /code/requirements.txt

RUN pip install -r /code/requirements.txt

COPY . /code
COPY .env /code/.env

RUN rm -rf /code/.git

RUN mkdir -p /code/logs


RUN chmod +x /code/scripts/docker-entrypoint.sh

WORKDIR /code

ENTRYPOINT ["/bin/bash", "/code/scripts/docker-entrypoint.sh"]