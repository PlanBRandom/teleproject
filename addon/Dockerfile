ARG BUILD_FROM
FROM $BUILD_FROM

# Install Python and dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-pyserial

# Install Python packages
RUN pip3 install --no-cache-dir \
    pymodbus==3.6.8 \
    paho-mqtt==1.6.1 \
    pyyaml==6.0.1

# Copy application files
COPY pipeline /app/pipeline
COPY addon/run.sh /app/run.sh
RUN chmod a+x /app/run.sh

WORKDIR /app

CMD [ "/app/run.sh" ]
