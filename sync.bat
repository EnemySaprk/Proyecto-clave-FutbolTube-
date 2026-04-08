@echo off
cd /d "C:\Users\asus\Desktop\Proyectos\futboltube"
call venv\Scripts\activate.bat
python manage.py sincronizar_agenda --dias 7
python manage.py obtener_logos
