FROM python:3.7

RUN pip install kubernetes==8.0

COPY operator.py /operator.py

CMD ["/operator.py"]