FROM python:3-slim
LABEL maintainer Tomas Kukral

WORKDIR /code

COPY . app
RUN pip install ./app

CMD ["/code/app/entrypoint.sh"]
