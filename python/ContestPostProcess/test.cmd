@echo off

REM These may be pre-set in the environment
REM SET QRZ_USERNAME=n7dz
REM SET QRZ_PASSWORD=not_the_real_password

IF "%QRZ_USERNAME%"=="" (
    set /p QRZ_USERNAME=Enter QRZ username: 
)

IF "%QRZ_PASSWORD%"=="" (
    set /p QRZ_PASSWORD=Enter QRZ password: 
)

copy testdata\input\qrz_cache.json testdata\output\
python -m contest_summary "./testdata/input/sample_log.adi" --outdir ./testdata/output --qrz yes --map states_dx
rem python -m contest_summary "\temp\test_split_by_operator\W1AW_7_2026-0225_to_2026-0303 (whole event).adi" --qrz yes --map na_states_dx

type \temp\test_split_by_operator\summary.txt