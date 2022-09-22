FROM python:3.8.5-alpine3.12

COPY .gitconfig /root/

RUN mkdir -p /root/.ssh/ && \
	touch /root/.ssh/config && \
	mkdir -p /opt/service

WORKDIR /opt/service

COPY requirements.txt .

RUN apk add git openssh \
    && pip install --no-cache-dir -r requirements.txt \
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

ENV PYTHONPATH "/opt/service/lib:${PYTHONPATH}"

CMD ["/opt/service/bin/daemon.py"]
