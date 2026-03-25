FROM python:3.13-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app/src

RUN python -m pytest tests -vv --maxfail=1

CMD ["python", "main.py"]