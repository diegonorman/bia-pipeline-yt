import os
import subprocess
import logging
import boto3
import uuid
from datetime import datetime, timedelta

# Configurações
FOLDER_PATH = "/var/log/glog/"
BUCKET_NAME = "axon-glog-us-east-1"
DESTINATION_REGION = "us-east-1"
DESTINATION_FOLDER = "/var/log/"
LOG_FILE = "/var/log/backup_log_s3.log"

# Configurar logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(message)s')

def log_message(message):
    logging.info(message)
    print(message)

log_message("Iniciando backup e envio para o S3")

# Obter a data atual no formato YYYY-MM-DD-HH-MM
CURRENT_DATE = datetime.now().strftime("%Y-%m-%d-%H-%M")

# Gerar uma hash
HASH = str(uuid.uuid4())

# Nome do arquivo tgz com data, hora, minuto e hash
TGZ_FILENAME = f"{DESTINATION_FOLDER}{CURRENT_DATE}-{HASH}.tgz"

# Comprimir a pasta em formato tgz com alta prioridade
try:
    subprocess.run(["nice", "-n", "-20", "tar", "-czf", TGZ_FILENAME, "-C", FOLDER_PATH, "."], check=True, stderr=subprocess.PIPE)
except subprocess.CalledProcessError as e:
    log_message(f"Erro ao comprimir a pasta: {e.stderr.decode()}")
    raise

# Enviar o arquivo tgz para o bucket S3 na região us-east-1 com a opção Intelligent-Tiering
s3_client = boto3.client('s3', region_name=DESTINATION_REGION)

try:
    s3_client.upload_file(TGZ_FILENAME, BUCKET_NAME, os.path.basename(TGZ_FILENAME), ExtraArgs={'StorageClass': 'INTELLIGENT_TIERING'})
    log_message(f"Arquivo enviado com sucesso para o S3 na região {DESTINATION_REGION}: {TGZ_FILENAME}.")

    # Excluir o arquivo tgz após o upload
    os.remove(TGZ_FILENAME)

    # Excluir arquivos na pasta /var/log/glog com mais de 7 dias
    cutoff_date = datetime.now() - timedelta(days=7)
    for root, dirs, files in os.walk(FOLDER_PATH):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.getmtime(file_path) < cutoff_date.timestamp():
                os.remove(file_path)

    # Calcular o tamanho do arquivo enviado
    response = s3_client.head_object(Bucket=BUCKET_NAME, Key=os.path.basename(TGZ_FILENAME))
    file_size = response['ContentLength']

    # Calcular o checksum do arquivo enviado
    file_checksum = response['ETag'].strip('"')

    log_message(f"Tamanho do arquivo enviado: {file_size} bytes.")
    log_message(f"Checksum do arquivo no S3: {file_checksum}.")
except Exception as e:
    log_message(f"Erro ao enviar o arquivo para o S3 na região {DESTINATION_REGION}. O arquivo não será excluído: {TGZ_FILENAME}. Erro: {str(e)}")

log_message("Backup e envio para o S3 concluídos")
