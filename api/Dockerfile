FROM python:3.8.5-alpine3.12

RUN mkdir -p /opt/service

WORKDIR /opt/service

COPY requirements.txt .

RUN apk add --no-cache --virtual .pip-deps  \
        git \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del --no-network .pip-deps \
	&& find /usr/local -depth \
		\( \
			\( -type d -a \( -name test -o -name tests -o -name idle_test \) \) \
			-o \
			\( -type f -a \( -name '*.pyc' -o -name '*.pyo' \) \) \
		\) -exec rm -rf '{}' + \
	&& rm requirements.txt \
	&& rm -rf dep

COPY bin bin
COPY lib lib

ENV PYTHONPATH "/opt/service/forge:/opt/service/lib:${PYTHONPATH}"

CMD ["/opt/service/bin/api.py"]
