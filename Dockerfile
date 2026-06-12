FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY requirements-web.txt .
RUN pip install -r requirements-web.txt

COPY banner_eyelets/ ./banner_eyelets/
COPY web/ ./web/

EXPOSE 8000
CMD ["uvicorn", "web.server:app", "--host", "0.0.0.0", "--port", "8000"]
