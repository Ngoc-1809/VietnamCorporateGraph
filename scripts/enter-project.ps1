# Dot-source this file:  . .\scripts\enter-project.ps1
# Sets every cache/temp/model path to T:\VietnamCorporateGraph BEFORE any ML library is imported.
$Root = 'T:\VietnamCorporateGraph'
if (-not (Test-Path -LiteralPath $Root)) { throw "Project root $Root not found" }

$dirs = @{
    HF_HOME               = "$Root\cache\huggingface"
    HF_HUB_CACHE          = "$Root\cache\huggingface\hub"
    HF_XET_CACHE          = "$Root\cache\huggingface\xet"
    HF_ASSETS_CACHE       = "$Root\cache\huggingface\assets"
    TRANSFORMERS_CACHE    = "$Root\cache\huggingface\hub"
    TORCH_HOME            = "$Root\cache\torch"
    TORCHINDUCTOR_CACHE_DIR = "$Root\cache\torch\inductor"
    TRITON_CACHE_DIR      = "$Root\cache\triton"
    UV_CACHE_DIR          = "$Root\cache\uv"
    UV_PYTHON_INSTALL_DIR = "$Root\runtime\uv-python"
    UV_TOOL_DIR           = "$Root\runtime\tools\uv-tools"
    UV_TOOL_BIN_DIR       = "$Root\runtime\tools\bin"
    PIP_CACHE_DIR         = "$Root\cache\pip"
    XDG_CACHE_HOME        = "$Root\cache\xdg"
    MPLCONFIGDIR          = "$Root\cache\matplotlib"
    NLTK_DATA             = "$Root\cache\nltk"
    TEMP                  = "$Root\tmp"
    TMP                   = "$Root\tmp"
    TMPDIR                = "$Root\tmp"
    OLLAMA_MODELS         = "$Root\models\ollama"
    OLLAMA_TMPDIR         = "$Root\tmp"
    PYTHONPYCACHEPREFIX   = "$Root\cache\pycache"
    PYTHONUTF8            = '1'
    PYTHONIOENCODING      = 'utf-8'
    HF_HUB_DISABLE_TELEMETRY = '1'
    UV_LINK_MODE          = 'copy'
    VCKG_ROOT             = $Root
}
foreach ($k in $dirs.Keys) {
    $v = $dirs[$k]
    if ($v -like 'T:\*') { New-Item -ItemType Directory -Force -Path $v | Out-Null }
    Set-Item -Path "Env:$k" -Value $v
}

# PATH: project tools first (uv, ollama portable, venv)
$extra = @("$Root\.venv\Scripts", "$Root\runtime\tools\bin", "$Root\runtime\ollama", "$Root\runtime\uv-bin")
foreach ($p in $extra) { if ((Test-Path $p) -and ($env:PATH -notlike "*$p*")) { $env:PATH = "$p;$env:PATH" } }

Set-Location $Root
Write-Host "[VCKG] Environment ready. Root=$Root  HF_HOME=$env:HF_HOME  OLLAMA_MODELS=$env:OLLAMA_MODELS"
