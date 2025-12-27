import json
import base64
import datetime

def lambda_handler(event, context):
    output = []
    for record in event['records']:
        payload = base64.b64decode(record['data']).decode('utf-8')
        data_json = json.loads(payload)
        
        # Extract fields for partitioning
        station_id = data_json.get('station_id', 'unknown')
        timestamp_str = data_json.get('timestamp')
        
        # Parse timestamp to get date
        if timestamp_str:
            try:
                dt = datetime.datetime.fromisoformat(timestamp_str)
                date_str = dt.strftime('%Y-%m-%d')
            except ValueError:
                date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        else:
            date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        
        output_record = {
            'recordId': record['recordId'],
            'result': 'Ok',
            'data': base64.b64encode((json.dumps(data_json) + '\n').encode('utf-8')).decode('utf-8'),
            'metadata': {
                'partitionKeys': {
                    'station_id': station_id,
                    'date': date_str
                }
            }
        }
        output.append(output_record)
    
    return {'records': output}