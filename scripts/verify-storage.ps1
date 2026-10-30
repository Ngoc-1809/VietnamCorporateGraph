# Verifies that all project cache/temp/model paths point to T:\VietnamCorporateGraph.
# Usage: . .\scripts\enter-project.ps1; .\scripts\verify-storage.ps1
$Root = 'T:\VietnamCorporateGraph'
$vars = 'HF_HOME','HF_HUB_CACHE','HF_XET_CACHE','HF_ASSETS_CACHE','TORCH_HOME','UV_CACHE_DIR',
        'UV_PYTHON_INSTALL_DIR','PIP_CACHE_DIR','TEMP','TMP','TMPDIR','OLLAMA_MODELS','XDG_CACHE_HOME','TRITON_CACHE_DIR'
$bad = 0
foreach ($v in $vars) {
    $val = [Environment]::GetEnvironmentVariable($v, 'Process')
    if ([string]::IsNullOrEmpty($val)) { Write-Host "[FAIL] $v is not set" -ForegroundColor Red; $bad++; continue }
    $full = [IO.Path]::GetFullPath($val)
    if ($full.StartsWith($Root, [StringComparison]::OrdinalIgnoreCase)) {
        Write-Host "[ OK ] $v = $full" -ForegroundColor Green
    } else {
        Write-Host "[WARN] $v points outside project: $full" -ForegroundColor Yellow; $bad++
    }
}
# Tools should resolve under the project (venv python / uv) when installed
foreach ($t in 'python','uv','ollama') {
    $c = Get-Command $t -ErrorAction SilentlyContinue
    if ($c) {
        $ok = $c.Source.StartsWith($Root, [StringComparison]::OrdinalIgnoreCase)
        $tag = if ($ok) { '[ OK ]' } else { '[INFO]' }
        Write-Host "$tag tool $t -> $($c.Source)"
        if ($t -eq 'python' -and -not $ok) { Write-Host "[WARN] python is not the project venv" -ForegroundColor Yellow; $bad++ }
    } else { Write-Host "[INFO] tool $t not found on PATH" }
}
# Ollama server process: model dir must match
$op = Get-Process ollama -ErrorAction SilentlyContinue
if ($op) { Write-Host "[INFO] ollama running (PID $($op.Id -join ',')); ensure it was started after enter-project.ps1" }
# C: and common C: cache dirs that must not grow
$c = Get-PSDrive C; $t = Get-PSDrive T
Write-Host ("Free: C: {0:N2} GB | T: {1:N2} GB" -f ($c.Free/1GB), ($t.Free/1GB))
foreach ($p in "$env:USERPROFILE\.cache\huggingface","$env:USERPROFILE\.ollama\models","$env:LOCALAPPDATA\uv\cache","$env:LOCALAPPDATA\pip\Cache","$env:USERPROFILE\.cache\torch") {
    if (Test-Path $p) {
        $s = (Get-ChildItem $p -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
        Write-Host ("[INFO] pre-existing C: dir {0}: {1:N1} MB (not touched)" -f $p, ($s/1MB))
    }
}
if ($bad -gt 0) { Write-Host "verify-storage: $bad problem(s)" -ForegroundColor Red; exit 1 }
Write-Host "verify-storage: all project paths on T:" -ForegroundColor Green; exit 0
