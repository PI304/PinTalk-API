FROM python:3.10

COPY ./ /home/pintalk/

WORKDIR /home/pintalk/

RUN apt-get update

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["bash", "-c", "python3 manage.py migrate && python3 manage.py runserver 0.0.0.0:8000"]