FROM python:3.7
LABEL maintainer Tomas Kukral

WORKDIR /code

COPY . app
RUN pip install ./app

CMD /code/app/entrypoint.sh

