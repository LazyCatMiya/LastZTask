FROM python:3.12-slim

WORKDIR /app

COPY lastz_tasks.py run_daily_tasks.py accounts.json ./

RUN useradd --create-home --shell /usr/sbin/nologin appuser
USER appuser

ENTRYPOINT ["python3", "run_daily_tasks.py"]
CMD ["--insecure", "--quiet"]
