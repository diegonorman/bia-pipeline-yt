#!/bin/bash

# Diretórios de origem e destino
SRC_DIR="/var/log/glog/"
DEST_DIR="/var/log/zipglog/"
ARCHIVE_NAME="glog_backup_$(date +%Y%m%d%H%M%S).tgz"
REPORT_FILE="/var/log/backup_report_$(date +%Y%m%d%H%M%S).txt"

# Função para registrar mensagens no relatório
log_message() {
  echo "$(date +'%Y-%m-%d %H:%M:%S') - $1" | tee -a "$REPORT_FILE"
}

# Verifica se o diretório de destino existe, se não, cria
if [ ! -d "$DEST_DIR" ]; then
  mkdir -p "$DEST_DIR"
fi

# Inicia o relatório
log_message "Início do processo de backup"

# Compactar a pasta de logs
tar -czvf "${DEST_DIR}${ARCHIVE_NAME}" -C "$SRC_DIR" .

# Verificar se a compactação foi bem-sucedida
if [ $? -eq 0 ]; then
  log_message "Arquivos compactados com sucesso em ${DEST_DIR}${ARCHIVE_NAME}"

  # Enviar para o bucket S3 usando Intelligent-Tiering
  aws s3 cp "${DEST_DIR}${ARCHIVE_NAME}" s3://axon-glog-us-east-1/ --region us-east-1 --storage-class INTELLIGENT_TIERING

  if [ $? -eq 0 ]; then
    log_message "Arquivo enviado para o S3 com sucesso"

    # Deletar os arquivos compactados da pasta de destino
    rm -f "${DEST_DIR}${ARCHIVE_NAME}"
    if [ $? -eq 0 ]; then
      log_message "Arquivos compactados deletados da pasta ${DEST_DIR}"
    else
      log_message "Erro ao deletar os arquivos compactados da pasta ${DEST_DIR}"
    fi

    # Deletar os arquivos antigos da pasta de origem (mais antigos que 7 dias)
    find "$SRC_DIR" -type f -mtime +7 -exec rm -f {} \;
    if [ $? -eq 0 ]; then
      log_message "Arquivos mais antigos que 7 dias deletados da pasta ${SRC_DIR}"
    else
      log_message "Erro ao deletar arquivos mais antigos que 7 dias na pasta ${SRC_DIR}"
    fi
  else
    log_message "Erro ao enviar o arquivo para o S3"
  fi
else
  log_message "Erro ao compactar os arquivos"
fi

log_message "Fim do processo de backup"
