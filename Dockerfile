FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY scrapper.py .
COPY domain ./domain
COPY services ./services
COPY .env .

RUN mkdir -p doctorsData

RUN echo '#!/bin/bash\n\
python scrapper.py & \n\
sleep 10 && \n\
cd /app && python app.py\n' > start.sh && \
chmod +x start.sh

EXPOSE 5000 5001

CMD ["./start.sh"]