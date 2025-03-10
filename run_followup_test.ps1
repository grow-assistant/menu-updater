# PowerShell script to run the follow-up query test

# Set environment variables
$env:OPENAI_API_KEY = "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"
$env:GEMINI_API_KEY = "AIzaSyDkSUyf4trFy0LDF6nVmvsCy17eMR9gsWI" 
$env:DATABASE_URL = "postgresql://postgres:Swoop123!@localhost:5433/byrdi"
$env:ELEVENLABS_API_KEY = "sk_6b0386660b88145b59fdd5b2dfa5a8da5e817484542dee64"

Write-Host "Environment variables set."
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