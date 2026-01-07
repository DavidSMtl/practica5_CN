$AWS_REGION="us-east-1"
$ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
$BUCKET_NAME="datalake-weather-stations-$ACCOUNT_ID"
$ROLE_ARN=$(aws iam get-role --role-name LabRole --query 'Role.Arn' --output text)




# Crear el bucket
aws s3 mb s3://$BUCKET_NAME

# Crear carpetas (objetos vacíos con / al final)
aws s3api put-object --bucket $BUCKET_NAME --key raw/
aws s3api put-object --bucket $BUCKET_NAME --key raw/weather/
aws s3api put-object --bucket $BUCKET_NAME --key processed/
aws s3api put-object --bucket $BUCKET_NAME --key config/
aws s3api put-object --bucket $BUCKET_NAME --key scripts/
aws s3api put-object --bucket $BUCKET_NAME --key queries/
aws s3api put-object --bucket $BUCKET_NAME --key errors/


aws kinesis create-stream --stream-name weather-stream --shard-count 1




Compress-Archive -Path firehose.py -DestinationPath firehose.zip -Force

aws lambda create-function `
    --function-name weather-firehose-lambda `
    --runtime python3.12 `
    --role $ROLE_ARN `
    --handler firehose.lambda_handler `
    --zip-file fileb://firehose.zip `
    --timeout 60 `
    --memory-size 128

aws lambda update-function-code `
    --function-name weather-firehose-lambda `
    --zip-file fileb://firehose.zip


$LAMBDA_ARN=$(aws lambda get-function --function-name weather-firehose-lambda --query 'Configuration.FunctionArn' --output text)

$jsonConfig = @"
{
    "BucketARN": "arn:aws:s3:::$BUCKET_NAME",
    "RoleARN": "$ROLE_ARN",
    "Prefix": "raw/weather/station_id=!{partitionKeyFromLambda:station_id}/date=!{partitionKeyFromLambda:date}/",
    "ErrorOutputPrefix": "errors/weather/!{firehose:error-output-type}/",
    "BufferingHints": {
        "SizeInMBs": 64,
        "IntervalInSeconds": 60
    },
    "DynamicPartitioningConfiguration": {
        "Enabled": true,
        "RetryOptions": {
            "DurationInSeconds": 300
        }
    },
    "ProcessingConfiguration": {
        "Enabled": true,
        "Processors": [
            {
                "Type": "Lambda",
                "Parameters": [
                    {
                        "ParameterName": "LambdaArn",
                        "ParameterValue": "$LAMBDA_ARN"
                    },
                    {
                        "ParameterName": "BufferSizeInMBs",
                        "ParameterValue": "1"
                    },
                    {
                        "ParameterName": "BufferIntervalInSeconds",
                        "ParameterValue": "60"
                    }
                ]
            }
        ]
    }
}
"@


$jsonConfig | Out-File -FilePath "config_firehose.json" -Encoding ASCII


aws firehose create-delivery-stream `
    --delivery-stream-name weather-delivery-stream `
    --delivery-stream-type KinesisStreamAsSource `
    --kinesis-stream-source-configuration "KinesisStreamARN=arn:aws:kinesis:${AWS_REGION}:${ACCOUNT_ID}:stream/weather-stream,RoleARN=$ROLE_ARN" `
    --extended-s3-destination-configuration file://config_firehose.json



aws glue create-database --database-input "Name=weather_db"

$targets = @"
    {""S3Targets"": [{""Path"": ""s3://$BUCKET_NAME/raw/weather/""}]}
"@

aws glue create-crawler `
    --name weather-raw-crawler `
    --role $ROLE_ARN `
    --database-name weather_db `
    --targets $targets

$targetsProcessed = @"
    {""S3Targets"": [{""Path"": ""s3://$BUCKET_NAME/processed/""}]}
"@

aws glue create-crawler `
    --name weather-processed-crawler `
    --role $ROLE_ARN `
    --database-name weather_db `
    --targets $targetsProcessed



aws s3 cp weather_aggregation.py s3://$BUCKET_NAME/scripts/
aws s3 cp weather_extreme_filter.py s3://$BUCKET_NAME/scripts/

$DATABASE="weather_db"
$TABLE="weather"
$OUTPUT_PATH_DAILY="s3://$BUCKET_NAME/processed/weather_daily/"
$OUTPUT_PATH_EXTREME="s3://$BUCKET_NAME/processed/extreme_weather/"

# Job 1: Daily Aggregation
$scriptLocationDaily = "s3://$BUCKET_NAME/scripts/weather_aggregation.py"

$commandDaily = @"
{
    ""Name"": ""glueetl"",
    ""ScriptLocation"": ""$scriptLocationDaily"",
    ""PythonVersion"": ""3""
}
"@

$defaultArgsDaily = @"
{
    ""--database"": ""$DATABASE"",
    ""--table"": ""$TABLE"",
    ""--output_path"": ""$OUTPUT_PATH_DAILY"",
    ""--enable-continuous-cloudwatch-log"": ""true"",
    ""--spark-event-logs-path"": ""s3://$BUCKET_NAME/logs/""
}
"@

aws glue create-job `
    --name weather-daily-aggregation `
    --role $ROLE_ARN `
    --command $commandDaily `
    --default-arguments $defaultArgsDaily `
    --glue-version "4.0" `
    --number-of-workers 2 `
    --worker-type "G.1X"


# Job 2: Extreme Weather Filter
$scriptLocationExtreme = "s3://$BUCKET_NAME/scripts/weather_extreme_filter.py"

$commandExtreme = @"
{
    ""Name"": ""glueetl"",
    ""ScriptLocation"": ""$scriptLocationExtreme"",
    ""PythonVersion"": ""3""
}
"@

$defaultArgsExtreme = @"
{
    ""--database"": ""$DATABASE"",
    ""--table"": ""$TABLE"",
    ""--output_path"": ""$OUTPUT_PATH_EXTREME"",
    ""--enable-continuous-cloudwatch-log"": ""true"",
    ""--spark-event-logs-path"": ""s3://$BUCKET_NAME/logs/""
}
"@

aws glue create-job `
    --name weather-extreme-filter `
    --role $ROLE_ARN `
    --command $commandExtreme `
    --default-arguments $defaultArgsExtreme `
    --glue-version "4.0" `
    --number-of-workers 2 `
    --worker-type "G.1X"
