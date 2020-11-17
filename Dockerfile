FROM python:3.7-alpine
WORKDIR /code
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
RUN apk add --no-cache gcc musl-dev linux-headers curl
COPY requirements.docker.txt requirements.txt
RUN pip install -r requirements.txt
EXPOSE ${FLASK_RUN_PORT}
COPY . .
CMD ["flask", "run"]
