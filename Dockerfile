FROM python:3.6-alpine
RUN apt-get update
RUN apt-get install -y cron
ENV PYTHONUNBUFFERED 1
RUN mkdir /FFXIVBOT
WORKDIR /FFXIVBOT
ADD  requirements.txt /FFXIVBOT/
# RUN wget https://tuna.moe/oh-my-tuna/oh-my-tuna.py  # Remove this line if your server is located outside of mainland China
# RUN python oh-my-tuna.py  # Remove this line if your server is located outside of mainland China
RUN pip install -r requirements.txt
ADD . /FFXIVBOT/
RUN ls
EXPOSE 8002

