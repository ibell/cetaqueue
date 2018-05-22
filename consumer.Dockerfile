FROM continuumio/miniconda3

RUN apt-get update -y -qq && pip install pymongo

COPY result_consumer.py .

## Add the wait script to the image
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.2.0/wait /wait
RUN chmod +x /wait

## Launch the wait tool and then your application
CMD /wait && python result_consumer.py
