FROM python:3.11-slim

RUN addgroup --system --gid 1000 appuser && \
    adduser --system --uid 1000 --ingroup appuser appuser

WORKDIR /app

COPY req.txt .
RUN pip install --no-cache-dir -r req.txt

COPY --chown=appuser:appuser . .

USER appuser

CMD ["python", "main.py"]