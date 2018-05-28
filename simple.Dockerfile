FROM continuumio/miniconda3
COPY simple.py .
CMD python -u simple.py
