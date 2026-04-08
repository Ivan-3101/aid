FROM python:3.12
ENV TZ=Asia/Calcutta

RUN mkdir -p /app
WORKDIR /app

COPY config.json /app
COPY requirements.txt /app
#RUN pip install  -r requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
ENV TZ=Asia/Calcutta


COPY *.py /app/

RUN mkdir -p /app/logs /app/secrets

# COPY secrets/* /app/secrets/

EXPOSE 8000


CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

