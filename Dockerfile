FROM python:3.10

COPY ./ /home/pintalk/

WORKDIR /home/pintalk/

RUN mkdir -p config/logs
RUN touch config/logs/pintalk.log

RUN apt-get update

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["bash", "-c", "python3 manage.py migrate && daphne -b 0.0.0.0 -p 8080 config.asgi.deploy:application"]