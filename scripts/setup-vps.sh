#!/usr/bin/env bash
# AppMedica — preparación inicial del VPS (Ubuntu 24.04 LTS)
# Ejecutar como root o con sudo: bash scripts/setup-vps.sh

set -euo pipefail

echo "=========================================="
echo " AppMedica — setup del servidor VPS"
echo "=========================================="

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: Ejecutá este script como root o con sudo."
  exit 1
fi

DEPLOY_USER="${SUDO_USER:-${USER}}"
if [[ "${DEPLOY_USER}" == "root" ]]; then
  DEPLOY_USER="root"
fi

echo ""
echo "[1/6] Actualizando paquetes del sistema..."
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
echo "    OK — sistema actualizado."

echo ""
echo "[2/6] Instalando Docker (repositorio oficial)..."
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
fi

ARCH="$(dpkg --print-architecture)"
CODENAME="$(. /etc/os-release && echo "${VERSION_CODENAME}")"
echo \
  "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl start docker
echo "    OK — Docker instalado y habilitado al inicio."

if [[ "${DEPLOY_USER}" != "root" ]]; then
  usermod -aG docker "${DEPLOY_USER}"
  echo "    Usuario '${DEPLOY_USER}' agregado al grupo docker (cerrá sesión SSH para aplicar)."
fi

echo ""
echo "[3/6] Instalando Nginx..."
apt-get install -y nginx
systemctl enable nginx
systemctl start nginx
echo "    OK — Nginx instalado."

echo ""
echo "[4/6] Instalando Certbot (Let's Encrypt + plugin Nginx)..."
apt-get install -y certbot python3-certbot-nginx
echo "    OK — Certbot instalado."

echo ""
echo "[5/6] Creando directorio de despliegue..."
mkdir -p /opt/appmedica
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" /opt/appmedica 2>/dev/null || true
echo "    OK — /opt/appmedica listo."

echo ""
echo "[6/6] Configurando firewall UFW..."
apt-get install -y ufw
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable
ufw status verbose || true
echo "    OK — UFW activo (SSH + Nginx Full)."

echo ""
echo "=========================================="
echo " Setup completado."
echo " Próximo paso: clonar el repo en /opt/appmedica"
echo " y seguir docs/DEPLOY.md"
echo "=========================================="
