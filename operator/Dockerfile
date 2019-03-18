FROM python:3.7

COPY requirements.txt /requirements.txt
RUN pip install -r requirements.txt

COPY operator.py /operator.py

CMD ["/operator.py"]
