FROM python:3.12.0-slim-bullseye
ADD . /web-page-archiver
WORKDIR /web-page-archiver
RUN pip install -r requirements.txt
