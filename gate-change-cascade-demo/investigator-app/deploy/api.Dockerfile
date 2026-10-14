## gate-change-cascade investigator-api
##
## Pure FastAPI + Kafka — no database.
## Agent activity log is kept in-memory (bounded deque); Kafka topic tailing
## is done via ephemeral consumer groups pointed at the participant's cluster.
##
##   Build context:  usecases/gate-change-cascade
##   Dockerfile:     investigator-app/deploy/api.Dockerfile

FROM registry.access.redhat.com/ubi9/python-311:latest

WORKDIR /app

COPY investigator-app/investigator/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY investigator-app/investigator/ /app/

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

EXPOSE 8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
