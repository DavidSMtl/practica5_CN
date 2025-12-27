import boto3
import json
import time
from loguru import logger
import datetime

# CONFIGURACIÓN
STREAM_NAME = 'weather-stream'
REGION = 'us-east-1'
INPUT_FILE = 'weather_data.json'

kinesis = boto3.client('kinesis', region_name=REGION)

def load_data(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def run_producer():
    data = load_data(INPUT_FILE)
    records_sent = 0
    
    # El JSON tiene una estructura 'included' donde están los arrays de valores
    series_list = data.get('included', [])
    
    logger.info(f"Iniciando transmisión al stream: {STREAM_NAME}...")
    
    # Iteramos sobre las estaciones (equivalente a los tipos de demanda)
    for serie in series_list:
        station_id = serie['attributes']['title']
        valores = serie['attributes']['values']
        
        for registro in valores:
            # Estructura del mensaje a enviar (Flattened for Kinesis)
            payload = {
                'station_id': station_id,
                'timestamp': registro['datetime'],
                'temperature': registro['temperature'],
                'humidity': registro['humidity'],
                'pressure': registro['pressure'],
                'wind_speed': registro['wind_speed']
            }
            
            # Enviar a Kinesis
            response = kinesis.put_record(
                StreamName=STREAM_NAME,
                Data=json.dumps(payload),
                PartitionKey=station_id # Usamos el ID de estación como clave de partición
            )
            
            records_sent += 1
            
            # Logging original style
            logger.info(f"Registro enviado al shard {response['ShardId']} con SequenceNumber {response['SequenceNumber']}")
            logger.info(f"Enviado [{station_id}]: {registro['temperature']} C, {registro['humidity']} %")
            # Pequeña pausa para simular streaming
            time.sleep(0.1)

    logger.info(f"Fin de la transmisión. Total registros enviados: {records_sent}")


if __name__ == '__main__':
    run_producer()