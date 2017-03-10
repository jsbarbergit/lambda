@echo off
echo Running pylint for %1
pylint %1.py
set upload=n
set /p upload="If you're happy with pylint score, Upload to Lambda? [y/n] (default n):  "

if "%upload%"=="y" (
	echo Uploading to NonProd Lambda and Publishing
	echo Replacing current Zip File
	7z a %1.zip %1.py
	aws lambda update-function-code --function-name %1 --zip-file fileb://%1.zip --publish --profile nonprod
)
