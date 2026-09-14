@echo off
setlocal
pushd "%~dp0"
python extract.py
python transform.py
python load.py
set "PIPELINE_EXIT_CODE=%ERRORLEVEL%"
popd
endlocal & exit /b %PIPELINE_EXIT_CODE%
