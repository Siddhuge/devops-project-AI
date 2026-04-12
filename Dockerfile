FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p reports logs
RUN touch cache.json

CMD ["python", "main.py"]
# AI Fix
2.33.1-0.1+deb10u1
