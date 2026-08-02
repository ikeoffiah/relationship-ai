FROM python:3.12-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Which manifest to install. Defaults to the runtime one, so a plain
# `docker build` still produces a lean image; docker-compose passes `dev.txt`,
# because the local stack is also where the test suite runs.
#
# The whole directory is copied rather than the one file, because dev.txt opens
# with `-r base.txt` and pip resolves that relative to the file it is reading.
ARG REQUIREMENTS=base.txt
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/${REQUIREMENTS}

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
