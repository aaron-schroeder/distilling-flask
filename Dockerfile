FROM tiangolo/meinheld-gunicorn:python3.8
LABEL maintainer="aaron@trailzealot.com"

COPY . .

RUN pip install -U pip && pip install -r ./requirements.txt

# I am unclear on what this does if I'm running locally.
# Or generally, who is looking for it.
ENV NGINX_WORKER_PROCESSES auto