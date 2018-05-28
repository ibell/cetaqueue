FROM continuumio/miniconda3

RUN apt-get update -y -qq && pip install pymongo

COPY job_producer.py .
COPY simple.py .
COPY simple.Dockerfile .

## Add the wait script to the image
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.2.0/wait /wait
RUN chmod +x /wait

## Launch the wait tool and then the application
CMD /wait && python job_producer.py
