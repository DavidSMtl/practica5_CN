import sys
import logging
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col
from awsglue.dynamicframe import DynamicFrame

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    args = getResolvedOptions(sys.argv, ['JOB_NAME', 'database', 'table', 'output_path'])
    
    logger.info(f"Job Name: {args['JOB_NAME']}")
    logger.info(f"Database: {args['database']}, Table: {args['table']}, Output: {args['output_path']}")

    sc = SparkContext()
    glueContext = GlueContext(sc)
    spark = glueContext.spark_session
    job = Job(glueContext)
    job.init(args['JOB_NAME'], args)

    # Read from Glue Catalog
    dynamic_frame = glueContext.create_dynamic_frame.from_catalog(
        database = args['database'], 
        table_name = args['table']
    )

    df = dynamic_frame.toDF()
    original_count = df.count()
    logger.info(f"Registros leídos: {original_count}")

    # Ensure types are correct
    df = df.withColumn("temperature", col("temperature").cast("double")) \
           .withColumn("humidity", col("humidity").cast("double")) \
           .withColumn("pressure", col("pressure").cast("double")) \
           .withColumn("wind_speed", col("wind_speed").cast("double"))

    # Filter for Extreme Weather
    # High Temperature (> 30) OR High Wind (> 20)
    extreme_weather_df = df.filter((col("temperature") > 30.0) | (col("wind_speed") > 20.0))
    
    filtered_count = extreme_weather_df.count()
    logger.info(f"Registros de clima extremo encontrados: {filtered_count}")

    # Convert back to DynamicFrame for Glue writing
    output_dynamic_frame = DynamicFrame.fromDF(extreme_weather_df, glueContext, "output")

    # Write back to S3
    glueContext.write_dynamic_frame.from_options(
        frame=output_dynamic_frame,
        connection_type="s3",
        connection_options={
            "path": args['output_path'],
            "partitionKeys": ["date", "station_id"]
        },
        format="parquet",
        format_options={"compression": "snappy"}
    )
    
    logger.info("Escritura en S3 completada.")
    job.commit()

if __name__ == "__main__":
    main()
