@echo off
cd /d C:\Projects\fb-marketplace-agent
C:\Users\admin\.pyenv\pyenv-win\versions\3.11.0\python.exe ebay_agent.py >> logs\ebay_agent.log 2>&1
