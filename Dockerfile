FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN grep -v '^\-e' requirements.txt > deps.txt && \
    pip install --no-cache-dir -r deps.txt && \
    rm deps.txt

COPY . .
RUN pip install -e .

EXPOSE 8501

CMD ["streamlit", "run", "scrapper_ui.py", "--server.port=8501", "--server.address=0.0.0.0"]
