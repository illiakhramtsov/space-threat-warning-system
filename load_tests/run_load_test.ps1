param(
    [string]$HostUrl = "http://localhost:8000",
    [int]$Users = 100,
    [int]$SpawnRate = 10,
    [string]$Duration = "1m"
)

$OutDir = "load_tests/results"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "Running Locust against $HostUrl ($Users VUsers, ramp-up $SpawnRate/s, duration $Duration)..."
locust -f load_tests/locustfile.py `
  --headless `
  --host $HostUrl `
  -u $Users `
  -r $SpawnRate `
  -t $Duration `
  --csv "$OutDir/run" `
  --html "$OutDir/report.html"

python load_tests/plot_results.py --csv-prefix "$OutDir/run" --out-dir "$OutDir"
Write-Host "Done! Open $OutDir/report.html and PNG charts in $OutDir/"
