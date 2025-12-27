import json
import random
import time
from datetime import datetime, timedelta

# Configuration
NUM_RECORDS_PER_STATION = 400
STATIONS = ["ST-001", "ST-002", "ST-003", "ST-004", "ST-005"]
START_TIME = datetime.now() - timedelta(days=7)

def generate_station_data(station_id):
    values = []
    current_time = START_TIME
    
    for _ in range(NUM_RECORDS_PER_STATION):
        # Advance time by roughly 10 minutes per record
        current_time += timedelta(minutes=random.randint(5, 15))
        
        temp = round(random.uniform(-5.0, 35.0), 1)
        if temp > 25:
            humidity = random.randint(20, 60)
        else:
            humidity = random.randint(40, 95)
            
        pressure = round(random.uniform(990.0, 1030.0), 1)
        wind_speed = round(random.uniform(0.0, 50.0), 1)
        
        values.append({
            "datetime": current_time.isoformat(),
            "temperature": temp,
            "humidity": humidity,
            "pressure": pressure,
            "wind_speed": wind_speed
        })
        
    return {
        "type": "Weather Station",
        "id": station_id,
        "attributes": {
            "title": station_id,
            "description": f"Weather data for {station_id}",
            "values": values
        }
    }

def main():
    print(f"Generating weather records for {len(STATIONS)} stations...")
    
    included_data = []
    for station in STATIONS:
        included_data.append(generate_station_data(station))
        
    final_structure = {
        "data": {
            "type": "Weather Data Collection",
            "id": "weather_batch_01",
            "attributes": {
                "title": "Synthetic Weather Data",
                "created_at": datetime.now().isoformat()
            }
        },
        "included": included_data
    }

    output_file = "weather_data.json"
    with open(output_file, "w") as f:
        json.dump(final_structure, f, indent=4)
    
    total_records = len(STATIONS) * NUM_RECORDS_PER_STATION
    print(f"Successfully generated {total_records} records in '{output_file}' with original structure.")

if __name__ == "__main__":
    main()
