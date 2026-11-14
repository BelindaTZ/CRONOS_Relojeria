# Imagen de Airflow (webserver + scheduler, LocalExecutor) con los DAGs/lib/
# warehouse de esta feature ya copiados dentro — Docker en este proyecto NO usa
# bind mounts, así que cada cambio en data/ exige reconstruir esta imagen
# (`docker compose up -d --build airflow-webserver airflow-scheduler airflow-init`).
FROM apache/airflow:2.10.3-python3.12

USER airflow

COPY airflow/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.3/constraints-3.12.txt" \
    -r /tmp/requirements.txt

ENV PYTHONPATH=/opt/airflow

COPY dags/ /opt/airflow/dags/
COPY lib/ /opt/airflow/lib/
COPY warehouse/ /opt/airflow/warehouse/
COPY tests/ /opt/airflow/tests/

RUN mkdir -p /opt/airflow/tmp
