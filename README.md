# Práctica 5 - Cloud Computing (ULPGC)

Este proyecto implementa un pipeline de procesamiento de datos en tiempo real y por lotes utilizando servicios de AWS. El objetivo es ingerir, almacenar, procesar y analizar datos meteorológicos simulados.

## Arquitectura y Flujo de Datos

El flujo de datos sigue el siguiente recorrido:

1.  **Generación de Datos**:
    -   `generate_weather_data.py`: Genera datos sintéticos de estaciones meteorológicas (temperatura, humedad, presión, viento) en formato JSON.
    -   `kinesis.py`: Lee estos datos y actúa como *productor*, enviando registros al **Kinesis Data Stream**.

2.  **Ingesta (Kinesis & Firehose)**:
    -   **Amazon Kinesis Data Stream**: Recibe los datos en tiempo real.
    -   **Amazon Kinesis Data Firehose**: Consume los datos del stream para entregarlos a Amazon S3.
    -   **AWS Lambda (`firehose.py`)**: Firehose invoca esta función para transformar los datos antes de guardarlos. La función:
        -   Decodifica los registros.
        -   Extrae el `station_id` y la fecha (`date`) del timestamp.
        -   Añade estos campos como metadatos de partición para que Firehose organice los archivos en S3 dinámicamente (`raw/weather/station_id=.../date=.../`).

3.  **Almacenamiento (Amazon S3)**:
    -   Se utiliza un bucket S3 (`datalake-weather-stations-...`) como Data Lake.
    -   Carpeta `raw/`: Almacena los datos crudos particionados.
    -   Carpeta `processed/`: Almacena los datos procesados y agregados.

4.  **Catalogación (AWS Glue Crawler)**:
    -   Un **Glue Crawler** (`weather-raw-crawler`) escanea la carpeta `raw/` en S3.
    -   Infiere el esquema de los datos (JSON) y crea una tabla (`weather`) en la base de datos de Glue (`weather_db`). Esto hace que los datos sean consultables inmediatamente.

5.  **Procesamiento (AWS Glue ETL & Spark)**:
    -   **AWS Glue Job**: Ejecuta un script de PySpark (`weather_aggregation.py`).
    -   Lee los datos crudos del Catálogo de Datos.
    -   Realiza agregaciones diarias (promedios de temperatura, humedad, etc.) agrupando por estación y fecha.
    -   Escribe los resultados en formato **Parquet** (optimizado para consultas) en la carpeta `processed/weather_daily/`.

6.  **Análisis (Amazon Athena)**:
    -   Se utiliza Athena para realizar consultas SQL estándar sobre los datos crudos y procesados almacenados en S3, aprovechando las tablas definidas en el Glue Data Catalog.

## Componentes y Configuración

El despliegue de la infraestructura se orquesta mediante el script `script.ps1`.

### Componentes Principales

*   **Amazon Kinesis Data Streams**:
    -   Stream: `weather-stream`
    -   Capacidad: 1 Shard (suficiente para la demostración).

*   **Amazon Kinesis Data Firehose**:
    -   Delivery Stream: `weather-delivery-stream`
    -   Fuente: Kinesis Data Stream.
    -   Transformación: Lambda activada.
    -   Particionamiento Dinámico: Habilitado. Organiza los objetos en S3 basándose en claves extraídas por la Lambda (Partition Projection).

*   **AWS Glue**:
    -   **Base de Datos**: `weather_db`
    -   **Crawler**: Actualiza la metadata de los datos crudos.
    -   **Job ETL**: `weather-daily-aggregation` (Workers G.1X).

### Scripts del Proyecto

*   `generate_weather_data.py`: Crea el dataset `weather_data.json`.
*   `kinesis.py`: Script en Python (boto3) que simula el envío de datos de sensores al stream.
*   `firehose.py`: Código de la función Lambda de transformación.
*   `weather_aggregation.py`: Script ETL de Spark para el Glue Job.
*   `script.ps1`: Script de PowerShell que utiliza AWS CLI para crear y configurar todos los recursos en la nube (S3, IAM Roles, Kinesis, Lambda, Glue, etc.).

## Cómo Ejecutar

1.  **Configurar Credenciales**: Asegurarse de tener AWS CLI configurado (`aws configure`) con permisos adecuados.
2.  **Desplegar Infraestructura**: Ejecutar `.\script.ps1`. Esto creará todos los recursos necesarios en AWS.
3.  **Generar Datos**: Ejecutar `python generate_weather_data.py` para crear el archivo local de datos.
4.  **Enviar Datos**: Ejecutar `python kinesis.py` para empezar a transmitir datos al Kinesis Stream.
5.  **Verificar Ingesta**: Revisar la consola de S3 (carpeta `raw/`) o usar Athena para consultar la tabla `weather`.
6.  **Ejecutar ETL**: Iniciar el Glue Job desde la consola o CLI para generar los agregados diarios en `processed/`.
