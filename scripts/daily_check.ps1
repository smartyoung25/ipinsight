# daily_check.ps1 — IPInsight 일일 운영 점검 스크립트
# 실행: powershell -ExecutionPolicy Bypass -File scripts\daily_check.ps1
# 권장: 매일 오전 9시 작업 스케줄러 등록

param(
    [string]$BaseUrl   = "http://localhost:8100",
    [string]$PythonExe = "python",
    [string]$RootDir   = $PSScriptRoot + "\.."
)

$ErrorActionPreference = "Continue"
$TS = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$PASS = "[PASS]"; $FAIL = "[FAIL]"; $WARN = "[WARN]"
$results = @()

function Log($status, $name, $detail) {
    $line = "$status  $($name.PadRight(40)) $detail"
    Write-Host $line
    $script:results += [PSCustomObject]@{ Status=$status; Name=$name; Detail=$detail }
}

Write-Host "`n======================================================"
Write-Host "  IPInsight 일일 점검  $TS"
Write-Host "======================================================`n"

# ── 1. 서버 /health ──────────────────────────────────────────
try {
    $resp = Invoke-RestMethod -Uri "$BaseUrl/health" -TimeoutSec 5
    if ($resp.status -eq "ok") {
        Log $PASS "API /health" "status=ok  version=$($resp.version)"
        # 커넥터 상태
        if ($resp.connectors) {
            $resp.connectors.PSObject.Properties | ForEach-Object {
                $icon = if ($_.Value) { $PASS } else { $WARN }
                Log $icon "  커넥터: $($_.Name)" $(if ($_.Value) { "설정됨" } else { "미설정 (폴백 동작)" })
            }
        }
    } else {
        Log $FAIL "API /health" "status=$($resp.status)"
    }
} catch {
    Log $FAIL "API /health" "서버 미응답: $($_.Exception.Message)"
}

# ── 2. 환경변수 점검 ──────────────────────────────────────────
$envVars = @{
    "ANTHROPIC_API_KEY" = "LLM·AI 에이전트"
    "EPO_CLIENT_ID"     = "특허 EPO OPS"
    "EPO_CLIENT_SECRET" = "특허 EPO OPS"
    "FDA_API_KEY"       = "FDA 510(k) 의료기기"
    "NTIS_API_KEY"      = "NTIS 정책 (승인 대기 가능)"
    "SLACK_WEBHOOK_URL" = "Slack 알림 (선택)"
    "ALLOWED_ORIGINS"   = "CORS 허용 도메인 (선택)"
}
$dotenvPath = Join-Path $RootDir ".env"
if (Test-Path $dotenvPath) {
    Get-Content $dotenvPath | ForEach-Object {
        if ($_ -match "^([^#=]+)=(.+)$") {
            [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), "Process")
        }
    }
}
foreach ($var in $envVars.Keys) {
    $val = [System.Environment]::GetEnvironmentVariable($var)
    if ($val) {
        Log $PASS "ENV: $var" "$($envVars[$var])"
    } else {
        $sev = if ($var -like "*SLACK*" -or $var -like "*ALLOWED*") { $WARN } else { $WARN }
        Log $sev "ENV: $var" "미설정 — $($envVars[$var])"
    }
}

# ── 3. 지식베이스 파일 무결성 ────────────────────────────────
$knowledgeDir = Join-Path $RootDir "knowledge"
if (Test-Path $knowledgeDir) {
    $jsons = Get-ChildItem $knowledgeDir -Filter "*.json"
    $ok = 0; $fail = 0
    foreach ($f in $jsons) {
        try {
            $null = Get-Content $f.FullName -Raw | ConvertFrom-Json
            $ok++
        } catch {
            $fail++
            Log $FAIL "knowledge: $($f.Name)" "JSON 파싱 실패"
        }
    }
    if ($fail -eq 0) {
        Log $PASS "knowledge/*.json" "$ok 파일 파싱 성공"
    } else {
        Log $FAIL "knowledge/*.json" "$ok 성공, $fail 실패"
    }
} else {
    Log $FAIL "knowledge/ 디렉터리" "경로 없음: $knowledgeDir"
}

# ── 4. requirements.txt 패키지 점검 ──────────────────────────
$reqPath = Join-Path $RootDir "requirements.txt"
if (Test-Path $reqPath) {
    try {
        $pip = & $PythonExe -m pip check 2>&1
        if ($LASTEXITCODE -eq 0) {
            Log $PASS "pip check" "의존성 충돌 없음"
        } else {
            Log $WARN "pip check" ($pip -join " " | Select-Object -First 1)
        }
    } catch {
        Log $WARN "pip check" "pip 실행 실패"
    }
} else {
    Log $FAIL "requirements.txt" "파일 없음"
}

# ── 5. 캐시 정리 (7일 이상 파일) ─────────────────────────────
$cacheDir = Join-Path $RootDir ".rag_cache"
if (Test-Path $cacheDir) {
    $old = Get-ChildItem $cacheDir -File | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) }
    if ($old.Count -gt 0) {
        $old | Remove-Item -Force
        Log $PASS "캐시 정리" "$($old.Count)개 만료 캐시 삭제 (7일 이상)"
    } else {
        Log $PASS "캐시 정리" "만료 캐시 없음"
    }
} else {
    Log $WARN "캐시 디렉터리" ".rag_cache 없음 (첫 실행 전 정상)"
}

# ── 6. PoC 검증 실행 ──────────────────────────────────────────
$pocPath = Join-Path $RootDir "deploy\poc_checklist.py"
if (Test-Path $pocPath) {
    try {
        $poc = & $PythonExe $pocPath 2>&1 | Select-String "통과율"
        if ($poc) {
            Log $PASS "PoC 검증" $poc[0].Line.Trim()
        } else {
            Log $WARN "PoC 검증" "통과율 파싱 불가 (실행됨)"
        }
    } catch {
        Log $WARN "PoC 검증" "실행 실패: $($_.Exception.Message)"
    }
} else {
    Log $WARN "PoC 검증" "poc_checklist.py 없음"
}

# ── 요약 ─────────────────────────────────────────────────────
$pass  = ($results | Where-Object { $_.Status -eq $PASS }).Count
$fail  = ($results | Where-Object { $_.Status -eq $FAIL }).Count
$warn  = ($results | Where-Object { $_.Status -eq $WARN }).Count
Write-Host "`n------------------------------------------------------"
Write-Host "  결과: PASS=$pass  FAIL=$fail  WARN=$warn  총 $($results.Count)건"
Write-Host "======================================================"

# JSON 보고서 저장
$report = @{
    timestamp = $TS
    pass      = $pass
    fail      = $fail
    warn      = $warn
    items     = $results
} | ConvertTo-Json -Depth 5
$reportPath = Join-Path $RootDir "deploy\daily_check_report.json"
$report | Out-File -FilePath $reportPath -Encoding utf8
Write-Host "  [SAVE] 보고서: $reportPath`n"

exit $(if ($fail -gt 0) { 1 } else { 0 })
