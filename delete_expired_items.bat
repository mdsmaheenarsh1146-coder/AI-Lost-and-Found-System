
@echo off
cd /d C:\projects\DJANGO\lost_found_project_backup

call venv\Scripts\activate.bat

python manage.py delete_expired_items

