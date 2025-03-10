# PowerShell script to run all query integration tests

# Check if .env file exists and load variables from it
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value)
        }
    }
    Write-Host "Loaded environment variables from .env file."
} else {
    Write-Host "No .env file found. Make sure you have the required environment variables set."
    Write-Host "Required variables: OPENAI_API_KEY, GEMINI_API_KEY, DB_CONNECTION_STRING, ELEVENLABS_API_KEY"
}

# Verify environment variables are set
$requiredVars = @("OPENAI_API_KEY", "GEMINI_API_KEY", "DB_CONNECTION_STRING", "ELEVENLABS_API_KEY")
$missingVars = $requiredVars | Where-Object { [string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable($_)) }

if ($missingVars.Count -gt 0) {
    Write-Host "❌ Missing required environment variables: $($missingVars -join ', ')" -ForegroundColor Red
    Write-Host "Please set these variables in your .env file or system environment."
    exit 1
}

Write-Host "Environment variables verified."
Write-Host "Running all query integration tests..."

# Run specific query category tests
# Uncomment the specific tests you want to run
python -m pytest tests/integration/queries/order_history -xvs

# Check the exit code
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Test completed successfully!" -ForegroundColor Green
} else {
    Write-Host "`n❌ Test failed." -ForegroundColor Red
}

# python -m pytest tests/integration/queries/menu_inquiry -xvs
# python -m pytest tests/integration/queries/popular_items -xvs

# Or run all query tests
# python -m pytest tests/integration/queries -xvs

Write-Host "Tests completed!" 
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# PowerShell script to run the follow-up query test
