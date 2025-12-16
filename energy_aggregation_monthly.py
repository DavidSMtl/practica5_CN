# monthly_aggregation.py
import sys
import logging
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from pyspark.sql.functions import col, sum as spark_sum, avg, substring
from awsglue.dynamicframe import DynamicFrame

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    args = getResolvedOptions(sys.argv, ['database', 'table', 'output_path'])
    database = args['database']
    table = args['table']
    output_path = args['output_path']

    logger.info(f"Database: {database}, Table: {table}, Output: {output_path}")
    
    sc = SparkContext()
    glueContext = GlueContext(sc)

    df = df.withColumn("fecha", substring(col("timestamp_origen"), 1, 7))
    
    daily_df = df.groupBy("fecha", "tipo") \
        .agg(
            spark_sum("valor").alias("valor_total"),
            avg("porcentaje").alias("porcentaje_promedio")
        ) \
        .orderBy("fecha", "tipo")
    
    output_dynamic_frame = DynamicFrame.fromDF(daily_df, glueContext, "output")
    
    logger.info(f"Registros agregados: {output_dynamic_frame.count()}")
    
    # Escribir usando GlueContext
    glueContext.write_dynamic_frame.from_options(
        frame=output_dynamic_frame,
        connection_type="s3",
        connection_options={
            "path": output_path,
            "partitionKeys": ["fecha"]
        },
        format="parquet",
        format_options={"compression": "snappy"}
    )
    
    logger.info(f"Completado. Registros: {daily_df.count()}")

if __name__ == "__main__":
    main()