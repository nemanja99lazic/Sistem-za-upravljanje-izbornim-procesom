FROM python:3

RUN mkdir -p /opt/src/authentication

WORKDIR /opt/src/authentication

COPY authentication/application.py ./application.py
COPY authentication/configuration.py ./configuration.py
COPY authentication/models.py ./models.py
COPY authentication/requirements.txt ./requirements.txt
COPY authentication/roleCheckDecorator.py ./roleCheckDecorator.py

RUN pip install -r ./requirements.txt

ENTRYPOINT ["python", "./application.py"]
