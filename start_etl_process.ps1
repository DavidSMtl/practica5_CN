$CRAWLER_NAME = "weather-raw-crawler"
$JOB_DAILY = "weather-daily-aggregation"
$JOB_EXTREME = "weather-extreme-filter"

function Wait-ForCrawler {
    param ($CrawlerName)
    Write-Host "Iniciando crawler: $CrawlerName"
    aws glue start-crawler --name $CrawlerName

    do {
        Start-Sleep -Seconds 5
        $status = aws glue get-crawler --name $CrawlerName --query "Crawler.State" --output text
        Write-Host "Estado del crawler ($CrawlerName): $status"
    } until ($status -eq "READY")
    
    $lastStatus = aws glue get-crawler --name $CrawlerName --query "Crawler.LastCrawl.Status" --output text
    Write-Host "Crawler finalizado. Resultado ultimo crawl: $lastStatus"
    
    if ($lastStatus -eq "FAILED") {
        Write-Error "El crawler fallo. Deteniendo proceso."
        exit 1
    }
}

function Wait-ForJob {
    param ($JobName)
    Write-Host "Iniciando trabajo: $JobName"
    $runId = aws glue start-job-run --job-name $JobName --query "JobRunId" --output text
    Write-Host "Job Run ID: $runId"

    do {
        Start-Sleep -Seconds 10
        $status = aws glue get-job-run --job-name $JobName --run-id $runId --query "JobRun.JobRunState" --output text
        Write-Host "Estado del trabajo ($JobName): $status"
    } until ($status -in "SUCCEEDED", "STOPPED", "FAILED", "TIMEOUT")

    if ($status -ne "SUCCEEDED") {
        Write-Error "El trabajo $JobName no termino correctamente. Estado: $status"
        exit 1
    }
    Write-Host "Trabajo $JobName completado con exito."
}



Write-Host "INICIANDO PROCESO ETL"

Wait-ForCrawler -CrawlerName $CRAWLER_NAME

Wait-ForJob -JobName $JOB_DAILY

Wait-ForJob -JobName $JOB_EXTREME

$CRAWLER_PROCESSED = "weather-processed-crawler"
Wait-ForCrawler -CrawlerName $CRAWLER_PROCESSED

Write-Host "PROCESO ETL COMPLETADO"
