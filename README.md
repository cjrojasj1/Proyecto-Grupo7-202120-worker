# Proyecto-Grupo7-202120

## Acerca de la aplicación
API web que permite a un usuario convertir archivos de audio en línea de un formato a otro, seleccionando únicamente el formato destino.  Está desarrollada sobre servidor Flask, Celery, Gunicorn y nginx.

## Instalación
### Requisitos y consideraciones para la instalación.
<ul>
<li>Máquina Ubuntu Linux versión 20.04 con:</li>
<ol>
<li>Conexión a Internet</li>
<li>Sistema de paquetes apt instalado</li>
<li>Usuario con privilegios sudo</li>
</ol>
<li>Usuario y la contraseña del usuario de git del repositorio</li>
</ul>

### Procedimiento de instalación.
Proporcione la contraseña del usuario sudo cuando sea requerida.  Así mismo, proporcione el usuario y la contraseña del usuario de git cuando sea requerido

<strong>1. Actualizar el servidor e instalar git</strong>
```
sudo apt-get -y update
sudo apt-get -y install git
```
    
<strong>2. Instalar el código fuente de la aplicación</strong>
```
cd ~
mkdir conversor_app
cd conversor_app
git clone --branch produccion https://github.com/MISW-4204-ComputacionEnNube/Proyecto-Grupo7-202120.git && cd Proyecto-Grupo7-202120/flaskr
```

<strong>3. Instalar los componentes iniciales necesarios para la instalación</strong>
```
sudo apt-get -y install pip
sudo apt-get -y install postgresql postgresql-contrib libpq-dev
sudo apt-get -y install redis
sudo apt-get -y install ffmpeg
sudo apt-get -y install uwsgi
sudo apt-get -y install python3-venv
sudo apt-get -y install gunicorn
sudo apt-get -y install nginx
sudo pip install wheel
pip install gunicorn
```
<strong>4. Crear el usuario y la base de datos en postgresql</strong>
```
sudo -i -u postgres psql -c "CREATE USER conversor WITH PASSWORD 'conversor1' CREATEDB;"
sudo -i -u postgres psql -c "CREATE DATABASE conversordb OWNER conversor"
```
<strong>5. Crear el ambiente virtual de ejecución de la aplicación</strong>

##### 5.1 Ambiente virtual
```python3 -m venv venv
source venv/bin/activate
#5.2 Paquetes de python requeridos
pip install -r requirements.txt
```

#### 5.2 Habilitar el puerto de la aplicación Flask
```
sudo ufw allow 5000
```

#### 5.3 Probar la aplicación sobre el servidor HTTP en ambiente virtual
```
gunicorn --bind 0.0.0.0:5000 wsgi:app
```

#### 5.4 Desactivar el ambiente virtual
```
deactivate
```

<strong>6. Gunicorn y nginx</strong>

#### 6.1. Configurar la aplicación para ejecución en Gunicorn
```
sudo tee -a /etc/systemd/system/conversion_app.service > /dev/null <<EOT
[Unit]
Description=Gunicorn instance to serve APP
After=network.target

[Service]
User=estudiante
Group=estudiante
WorkingDirectory=${HOME}/conversor_app/Proyecto-Grupo7-202120/flaskr
Environment="PATH=${HOME}/conversor_app/Proyecto-Grupo7-202120/flaskr/venv/bin/"
ExecStart=${HOME}/conversor_app/Proyecto-Grupo7-202120/flaskr/venv/bin/gunicorn --workers 4 --bind unix:conversion_app.sock -m 007 wsgi:app

[Install]
WantedBy=multi-user.target
EOT

sudo usermod estudiante -a -G www-data
sudo systemctl start conversion_app
sudo systemctl enable conversion_app
```

#### 6.2. Configurar la aplicación para ejecución en nginx
```
sudo ufw app list
sudo ufw allow 'Nginx HTTP'
```

#### 6.2.1 Comprobar el estado de ejecución de nginx
```
sudo systemctl status nginx


sudo tee -a /etc/nginx/sites-available/conversion_app > /dev/null <<EOT
server {
    listen 8080;
    server_name 172.23.66.142;

    location / {
        include proxy_params;
        proxy_pass http://unix:${HOME}/conversor_app/Proyecto-Grupo7-202120/flaskr/conversion_app.sock;
    }
}
EOT
```

#### 6.2.2 Aplicar configuraciones de nginx
```
sudo ln -s /etc/nginx/sites-available/conversion_app /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
sudo ufw delete allow 5000
sudo ufw allow 'Nginx Full'
```

#### 6.2.3 Comprobar nuevamente el estado de ejecución de nginx
```
sudo systemctl status nginx
```

<strong>7. Configuración de variables de ambiente en sesión de usuario</strong>
```
echo '' >> ~/.bashrc
echo 'CONVERSOR_APP_HOME=~/conversor_app/Proyecto-Grupo7-202120' >> ~/.bashrc
echo 'export CONVERSOR_APP_HOME' >> ~/.bashrc

echo '' >> ~/.bashrc
echo 'CONVERSOR_APP_LOGS=~/conversion_logs' >> ~/.bashrc
echo 'export CONVERSOR_APP_LOGS' >> ~/.bashrc

echo '' >> ~/.bashrc
echo 'CONVERSOR_CELERY_LOG_LEVEL=CRITICAL' >> ~/.bashrc
echo 'export CONVERSOR_CELERY_LOG_LEVEL' >> ~/.bashrc

echo '' >> ~/.bashrc
echo 'PATH=$PATH:$CONVERSOR_APP_HOME' >> ~/.bashrc
echo 'export PATH' >> ~/.bashrc

CONVERSOR_APP_HOME=~/conversor_app/Proyecto-Grupo7-202120
export CONVERSOR_APP_HOME

CONVERSOR_APP_LOGS=~/conversion_logs
export CONVERSOR_APP_LOGS

CONVERSOR_CELERY_LOG_LEVEL=CRITICAL
export CONVERSOR_CELERY_LOG_LEVEL

PATH=$PATH:$CONVERSOR_APP_HOME
export PATH
```
<strong>8. Creación de los directorios requeridos para el manejo de archivos de la aplicación</strong>
```
cd ~
mkdir conversion_files
cd conversion_files
mkdir processed
mkdir uploads
cp ~/conversor_app/Proyecto-Grupo7-202120/sample_files/* ~/conversion_files/uploads
cd ~
mkdir conversion_logs
```

## Directorios y archivos
<ul>
<li><code>$HOME/conversion_logs</code>: logs de la aplicación.  Estos son los siguientes:</li>
<ol>
<li><code>$HOME/conversion_logs/conv_celery.log</code>: log de ejecución de Celery.</li>
<li><code>$HOME/conversion_logs/celery_process_id.txt</code>: Process ID (PID) del proceso Unix de Celery.</li>
</ol>
<li><code>$HOME/conversion_files</code>: directorio dónde se encuentran cargados los archivos de audio a convertir y los ya procesados por la aplicación.</li>
<ol>
<li><code>$HOME/conversion_files/uploads</code>: se encuentran los archivos de audio a convertir.  Existen los siguientes archivos ya pre-cargados para efecto de pruebas:</li>
<ol>
<li><code>base_file.mp3</code>: archivo de audio en formato MP3.</li>
<li><code>base_file.acc</code>: archivo de audio en formato ACC.</li>
<li><code>base_file.ogg</code>: archivo de audio en formato OGG.</li>
<li><code>base_file.wav</code>: archivo de audio en formato WAV.</li>
<li><code>base_file.wma</code>: archivo de audio en formato WMA.</li>
</ol>
<li><code>$HOME/conversion_logs/processed</code>: se encuentran los archivos de audio ya procesados por la aplicación.  Siguen la siguiente convención de nombre: <code>[nombre de archivo original]-[ID de la tarea de conversión].[extensión del tipo de archivo de audio de destino]</code>.  Ejemplo: <code>base_file-1.ogg</code>.</li>
</ol>
<li><code>$HOME/conversor_app/Proyecto-Grupo7-202120/conversor.sh</code>: script de ejecución de la aplicación.  Básicamente se encarga de subir y bajar los procesos del servidor de Flask y Celery de la aplicación.</li>
<li><code>$HOME/conversor_app/Proyecto-Grupo7-202120/flaskr/config_app/config_app.py</code>: contiene parámetros generales de configuración de la aplicación.  Son de mayor interés los asociados al manejo de los correos electrónicos de notificación al usuario:</li>
<ol>
<li><code>EMAIL_ENABLED</code>: un valor de 1 indica que la aplicación debe enviar correos electrónicos de notificación al usuario.  Otro valor, deshabilita el envió de dichos correos electrónicos.</li>
<li><code>EMAIL_ATTACHMENT_ENABLED</code>: un valor de 1 indica que la aplicación debe enviar el archivo procesado como adjunto en el correo electrónico de notificación al usuario.  Otro valor, indica que no debe enviarse el archivo adjunto.</li>
</ol>
</ul>

## Script de ejecución de la aplicación

<p>Con la aplicación instalada en el servidor, es posible ejecutar el script de ejecución <code>conversor.sh</code>, sin parámetros con lo que se obtendrá una salida como la siguiente:</p>

```
$ conversor.sh
Uso: conversor.sh start|stop|restart|status
```
<p>Esto presenta las posibles opciones que permiten gestionar la ejecución de la aplicación:</p>

<p><strong>1. Subir la aplicación: <code>conversor.sh start</code></strong></p>
<p><strong>2. Conocer el estado de ejecución de la aplicación: <code>conversor.sh status</code></strong></p>
<p><strong>3. Reiniciar la aplicación: <code>conversor.sh restart</code></strong></p>
<p><strong>4. Bajar la aplicación: <code>conversor.sh stop</code></strong></p>
