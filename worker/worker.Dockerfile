FROM continuumio/miniconda3

RUN pip install pymongo tee

RUN curl -fsSL get.docker.com -o get-docker.sh && \
    sh get-docker.sh && \
    curl -L https://github.com/docker/compose/releases/download/1.21.2/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose && \
    chmod +x /usr/local/bin/docker-compose

# Add user baleen and put it into its own group and also the docker group so
# that it can launch child docker instances
RUN groupadd -g 628 baleen && \
    useradd -r -u 628 -g baleen baleen && \
    usermod -aG docker baleen

# Switch to our user
USER baleen

ADD worker.py .
ADD worker_entrypoint.sh .

COPY worker-docker-compose.yml docker-compose.yml

# Make sure the stdout is unbuffered (the -u is important)
# See: https://github.com/moby/moby/issues/12447
CMD ["python","-u","worker.py"]

