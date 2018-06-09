FROM continuumio/miniconda3

RUN apt-get update -y -qq && pip install pymongo flask ansi2html celery

COPY frontend.py .
COPY tasks.py .
COPY templates templates

## Add the wait script to the image
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.2.0/wait /wait
RUN chmod +x /wait

## Launch the wait tool and then the frontend
CMD /wait && python -u frontend.py
