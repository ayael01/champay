sudo service nginx stop
kill $(ps aux | grep '[p]ython3 app.py' | awk '{print $2}')