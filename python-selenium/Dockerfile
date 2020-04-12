FROM python:3

# vimとseleniumをインストール
RUN set -x && \
  apt-get update && \
  apt-get install -y vim && \
  apt-get update && \
  apt-get install -y cron && \
  pip install selenium slackclient

RUN echo '11 10 * * * python /root/script/access_jobcan.py > /var/tmp/cron.log 2>&1' >> /etc/crontab
# RUN sed -i '1s/^/CRON_TZ=Asia/Tokyo\n/'
RUN chmod 777 /etc/crontab
RUN crontab -u root /etc/crontab
RUN /etc/init.d/cron start
