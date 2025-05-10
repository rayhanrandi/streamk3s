FROM python:3.6.9-slim
WORKDIR /usr/publish

COPY publish.py .

RUN mkdir /Publish
WORKDIR /Publish
COPY ./config/ ./config/
COPY ./publish.py ./
COPY ./Interface.py ./
COPY ./consume.py ./
RUN pip3 install pika==1.2.0 \
    flask[async] \
    requests \
    tenacity
ENV RABBIT_IP="#ip"
ENV TOPIC="#topic"
ENV RABBITMQ_PASSWORD = "#password"

EXPOSE 4321
CMD ["/usr/local/bin/python","./Interface.py"]