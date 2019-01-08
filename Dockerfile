FROM python:3.6
ENV PYTHONUNBUFFERED 1
RUN mkdir /FFXIVBOT
WORKDIR /FFXIVBOT
ADD  requirements.txt /FFXIVBOT/
RUN ls
RUN pip install -r requirements.txt
ADD . /FFXIVBOT/
EXPOSE 8002

