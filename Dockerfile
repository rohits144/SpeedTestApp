FROM python:3.7
RUN apt-get update && apt-get install -y python3 python3-pip
COPY . /SpeedTestApp
WORKDIR /SpeedTestApp
RUN pip install -r requirements.txt
CMD ["python3", "./speedTest.py"]
