@echo off
REM Analyze Collected Monitoring Data
REM Generates reports and exports from radio and Modbus logs

cd /d "%~dp0"

echo.
echo ================================================================================
echo   OI-7500 DATA ANALYSIS
echo ================================================================================
echo.
echo This will analyze all collected monitoring data and generate:
echo   - Gas sensor readings CSV
echo   - Summary report
echo   - Network statistics
echo.
pause

.venv\Scripts\python.exe analyze_data.py

echo.
echo ================================================================================
echo   ANALYSIS COMPLETE
echo ================================================================================
echo.
echo Check the 'exports' folder for:
echo   - gas_readings_*.csv (open in Excel)
echo   - monitoring_report_*.txt (summary)
echo.
echo Read DATA_USAGE_GUIDE.md for tips on using your data
echo.
pause
