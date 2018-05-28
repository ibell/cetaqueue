FROM continuumio/miniconda3

RUN pip install pymongo tee

RUN curl -fsSL get.docker.com -o get-docker.sh &&  sh get-docker.sh

ADD worker.py .

# Make sure the stdout is unbuffered (the -u is important)
# See: https://github.com/moby/moby/issues/12447
CMD python -u worker.py
