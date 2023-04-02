FROM public.ecr.aws/docker/library/python:3.9-slim-bullseye

COPY  requirements.txt .

RUN pip install -r requirements.txt

ENV PYTHONUNBUFFERED=TRUE