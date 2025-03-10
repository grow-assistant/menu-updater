# PowerShell script to run the follow-up query test

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
    Write-Host "Required variables: OPENAI_API_KEY, GEMINI_API_KEY, DATABASE_URL, ELEVENLABS_API_KEY"
}

# Verify environment variables are set
$requiredVars = @("OPENAI_API_KEY", "GEMINI_API_KEY", "DATABASE_URL", "ELEVENLABS_API_KEY")
$missingVars = $requiredVars | Where-Object { [string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable($_)) }

if ($missingVars.Count -gt 0) {
    Write-Host "❌ Missing required environment variables: $($missingVars -join ', ')" -ForegroundColor Red
    Write-Host "Please set these variables in your .env file or system environment."
    exit 1
}

Write-Host "Environment variables verified."
Write-Host "Running follow-up query test..."

# Run the test
python -m pytest tests/test_followup_queries.py -xvs

# Check the exit code
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Test completed successfully!" -ForegroundColor Green
} else {
    Write-Host "`n❌ Test failed." -ForegroundColor Red
}

Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 