import ffmpeg
import datetime
import pytz
import smtplib
import os
from os import remove
from celery import Celery
from celery.utils.log import get_task_logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from modelos import db, TareaConversion, EstadoProcesoConversion, Usuario
from email.mime.application import MIMEApplication
import boto3
import botocore

environment_vars = os.environ

## Conexión a la base de datos y generador de sesión
engine = create_engine(environment_vars['CONV_SQLALCHEMY_DATABASE_URI'])
Session = sessionmaker(bind=engine)

## Broker de mensajeria y worker
celery = Celery(__name__, broker=environment_vars['CONV_BROKER'])

## Para escritura de mensajes en el log
logger = get_task_logger(__name__)

boto3_session = boto3.Session(aws_access_key_id=environment_vars['AWS_ACCESS_KEY_ID'],
aws_secret_access_key=environment_vars['AWS_SECRET_ACCESS_KEY'])

s3 = boto3_session.resource('s3')

@celery.task(name='registrar_tarea')
def registrar_tarea(id_task):
    
    logger.info('Inicio de procesamiento')
    logger.info('Task ID: {}'.format(id_task))

    # Se abre sesión a la base de datos
    session = Session()
    
    # Se consulta tarea de conversión en la base de datos
    tarea = session.query(TareaConversion).filter_by(id=id_task).first()
    
    # Se procede sólo si la tarea tiene estado de cargado en el sistema
    if tarea.estado_conversion == EstadoProcesoConversion.UPLOADED:
        
        # Se marca la tarea para indicar que el procesamiento se está iniciando
        tarea.estado_conversion = EstadoProcesoConversion.PROCESSING
        session.commit()
        
        # Se realiza la conversión del archivo de audio
        error_conversion = False
        mensaje_error_conversion = ''
        try:
            
            # Se determinan las rutas de los archivos
            try:
                archivo_origen = tarea.nombre_archivo
                s3.Object(environment_vars['S3_BUCKET_NAME'], environment_vars['S3_UPLOAD_PREFIX'] + archivo_origen ).load()
                s3.download_file(environment_vars['S3_BUCKET_NAME'], environment_vars['S3_UPLOAD_PREFIX'] + archivo_origen, archivo_origen)
            except botocore.exceptions.ClientError as e:
                error_conversion = True
                mensaje_error_conversion = '¡ El archivo de audio origen no existe ! Se detiene el procesamiento'

            archivo_destino = '{}-{}.{}'.format(archivo_origen.rsplit('.')[0], id_task, tarea.extension_conversion)

            # Se ejecuta el proceso de conversión
            ffmpeg.input(archivo_origen).output(archivo_destino).global_args('-loglevel', environment_vars['CONV_FFMPEG_LOG_LEVEL']).global_args('-y').run()
            
            logger.info('Conversión realizada exitosamente')
        
        except Exception as ex:
            error_conversion = True
            mensaje_error_conversion = '¡ Se ha producido un error al intentar convertir el archivo de audio ! Se detiene el procesamiento'
            logger.info(ex)

        if error_conversion:
            logger.info(mensaje_error_conversion)
            # Se restablece el estado de la tarea
            tarea.estado_conversion = EstadoProcesoConversion.UPLOADED
            session.commit()
            session.close()
            return
        
        # Se envía el correo de notificacion al usuario sólo si la configuración de la aplicación lo permite
        if environment_vars['CONV_EMAIL_ENABLED'] == '1':
            
            #Se consulta el correo electrónico del usuario asociado a la tarea
            usuario = session.query(Usuario).filter_by(id=tarea.usuario).first()

            # Se envía el correo de notificacion al usuario sobre la conversión del archivo
            try:
                email_msg = MIMEMultipart('alternative')
                email_msg['From'] = environment_vars['CONV_EMAIL_FROM_USER']
                email_msg['To'] = usuario.email
                email_msg['Subject'] = environment_vars['CONV_EMAIL_SUBJECT'].format(id_task)
                
                email_text = MIMEText(environment_vars['CONV_EMAIL_BODY'].format(usuario.username, tarea.nombre_archivo, tarea.extension_conversion), 'html')
                email_msg.attach(email_text)

                
                if environment_vars['CONV_EMAIL_ATTACHMENT_ENABLED'] == '1':
                    logger.info('Cargando archivo convertido al correo electrónico...')
                    with open(archivo_destino, "rb") as attachment:
                        p = MIMEApplication(attachment.read(),)    
                        p.add_header('Content-Disposition', "attachment; filename= %s" % os.path.basename(archivo_destino))
                        email_msg.attach(p)

                smtp_server = smtplib.SMTP(environment_vars['CONV_EMAIL_HOST'], environment_vars['CONV_EMAIL_PORT'])
                smtp_server.starttls()
                smtp_server.ehlo()
                smtp_server.login(environment_vars['CONV_EMAIL_FROM_USER'], environment_vars['CONV_EMAIL_FROM_PASSWORD'])

                smtp_server.sendmail(environment_vars['CONV_EMAIL_FROM_USER'], usuario.email,
                email_msg.as_string())
                
                smtp_server.close()
                logger.info('Correo enviado al usuario exitosamente')
            except Exception as ex:
                logger.info('¡ Se ha producido un error al intentar enviar el correo electrónico al usuario !')
                logger.info(ex)
        
        # Se cambia el estado de la tarea de conversión a procesado y se actualiza la fecha de procesado
        tarea.estado_conversion = EstadoProcesoConversion.PROCESSED
        tarea.fecha_procesamiento = datetime.datetime.now(pytz.timezone('Etc/GMT+5'))
        session.commit()
        
        # Se cierra sesión a la base de datos
        session.close()

        logger.info('Fin de procesamiento')
