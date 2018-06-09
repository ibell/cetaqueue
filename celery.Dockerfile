FROM continuumio/miniconda3

RUN curl -fsSL get.docker.com -o get-docker.sh && \
    sh get-docker.sh && \
    curl -L https://github.com/docker/compose/releases/download/1.21.2/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose && \
    chmod +x /usr/local/bin/docker-compose

RUN pip install celery pymongo
COPY tasks.py /
COPY worker/worker-docker-compose.yml docker-compose.yml
COPY worker/worker_entrypoint.sh /worker_entrypoint.sh

# Add user baleen and put it into its own group and also the docker group so
# that it can launch child docker instances
RUN groupadd -g 628 baleen && \
    useradd -r -u 628 -g baleen baleen && \
    groupadd -g 629 gris && \
    useradd -r -u 629 -g gris gris && \
    usermod -aG docker gris

# Switch to our user
USER gris


CMD ["celery","-A","tasks","worker","--loglevel=info"]
