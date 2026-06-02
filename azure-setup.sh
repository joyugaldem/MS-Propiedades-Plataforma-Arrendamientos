#!/bin/bash
# =============================================================
# Azure infrastructure setup — MS Propiedades
# Ejecutar: bash azure-setup.sh
# Requiere: az login hecho previamente
# =============================================================

# ---- Valores desplegados (NO cambiar salvo recrear infraestructura) ----
RESOURCE_GROUP="rg-plataforma-arrendamientos"
LOCATION="westus3"                  # eastus no soporta PG; westus3 sí
PG_SERVER="pgprop-53383"            # nombre global único generado
PG_ADMIN="pgadmin"
PG_PASSWORD="Arr3nd@Xpwu18Ml!"     # guardar en lugar seguro
PG_DB="propiedades_db"
APP_SERVICE_PLAN="asp-propiedades"
APP_NAME="ms-propiedades-yfeovp"    # https://ms-propiedades-yfeovp.azurewebsites.net
# -----------------------------------------------------------------------

echo ">>> Creando Resource Group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

echo ">>> Creando PostgreSQL Flexible Server..."
az postgres flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name $PG_SERVER \
  --location $LOCATION \
  --admin-user $PG_ADMIN \
  --admin-password "$PG_PASSWORD" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 16 \
  --public-access 0.0.0.0

echo ">>> Creando base de datos..."
az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $PG_SERVER \
  --database-name $PG_DB

echo ">>> Habilitando extensión uuid-ossp..."
az postgres flexible-server parameter set \
  --resource-group $RESOURCE_GROUP \
  --server-name $PG_SERVER \
  --name azure.extensions \
  --value uuid-ossp

echo ">>> Creando App Service Plan (Linux, B1)..."
az appservice plan create \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --is-linux \
  --sku B1

echo ">>> Creando Web App..."
az webapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --runtime "PYTHON:3.12"

echo ">>> Configurando variables de entorno en App Service..."
PG_HOST="${PG_SERVER}.postgres.database.azure.com"
DATABASE_URL="postgresql+asyncpg://${PG_ADMIN}:${PG_PASSWORD}@${PG_HOST}:5432/${PG_DB}?ssl=require"

az webapp config appsettings set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    DATABASE_URL="$DATABASE_URL" \
    ALLOWED_ORIGINS="http://localhost:5173,https://agreeable-ground-0b1436910.6.azurestaticapps.net" \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true

echo ">>> Configurando startup command..."
az webapp config set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --startup-file "gunicorn app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"

echo ""
echo "=== Setup completado ==="
echo "App URL:  https://${APP_NAME}.azurewebsites.net"
echo "Health:   https://${APP_NAME}.azurewebsites.net/health"
echo "Docs:     https://${APP_NAME}.azurewebsites.net/docs"
echo ""
echo "Para hacer deploy: git push azure main"
echo "O configura GitHub Actions con el workflow incluido."
