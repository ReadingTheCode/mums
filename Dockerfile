FROM python:2.7
ENV PYTHONUNBUFFERED 1
RUN mkdir /opt/mums
WORKDIR /opt/mums
ADD requirements.txt /opt/mums
RUN pip install -r requirements.txt
ADD . /opt/mums
