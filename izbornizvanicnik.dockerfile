FROM python:3

RUN mkdir -p /opt/src/applications

WORKDIR /opt/src/applications

COPY applications/izborni_zvanicnik/application.py ./application.py
COPY applications/izborni_zvanicnik/configuration.py ./configuration.py
COPY applications/izborni_zvanicnik/izborniZvanicnikDecorator.py ./izborniZvanicnikDecorator.py
COPY applications/izborni_zvanicnik/requirements.txt ./requirements.txt

RUN pip install -r ./requirements.txt

ENTRYPOINT ["python", "./application.py"]