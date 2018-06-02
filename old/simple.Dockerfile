FROM continuumio/miniconda3
COPY simple.py .
CMD id -u && id -g && ls -al / && ls -al /output/ && touch /output/hello.txt && ls -al /output/ && python -u simple.py && ls -al /output/ && ls -al /mount && ls -al /mount/job
