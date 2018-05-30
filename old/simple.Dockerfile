FROM continuumio/miniconda3
COPY simple.py .
CMD id -u && id -g && ls -al / && ls -al /output && python -u simple.py && ls -al /output
