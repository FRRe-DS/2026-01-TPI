# Infraestructura en Azure Container Apps — M2 Clientes (Grupo 1)

Despliega el ecosistema de M2 Clientes en **Azure Container Apps** dentro de una misma red privada (`azurerm_container_app_environment`):

| Recurso | Imagen | Visibilidad | Rol |
|---|---|---|---|
| `aci-mongodb-g01` (`mongodb` + `postgres-m6`) | `mongo:7.0` + `postgres:16.15` | TCP `27017` y `5432` | Bases de datos de M2 Clientes (MongoDB) y M6 Viajes (PostgreSQL) |
| `keycloak` | `quay.io/keycloak/keycloak:23.0.6` | Externa (HTTPS -> `8080`) | Login y emisión de tokens (`ds-2026-realm.json` preconfigurado) |
| `m6-viajes` | `ghcr.io/frre-ds/m6-viajes-g12:sha-37db0f6` (`var.m6_image`) | Externa (HTTPS -> `3006`) | Microservicio M6 Viajes (Grupo 12, con validación RS256 contra Keycloak y panel web en `/`) |
| `m2-api` | `ghcr.io/frre-ds/2026-01-tpi-api` | Externa (HTTPS -> `8000`) | API de M2 con auto-escalado HTTP y OpenTelemetry hacia Grafana Cloud |
| `m2-front` | `ghcr.io/frre-ds/2026-01-tpi-front` | Externa (HTTPS -> `80`) | Frontend React de M2 conectado a `m2-api` y `keycloak` |

Además crea un **Log Analytics Workspace** asociado al entorno para recolectar métricas de CPU, RAM y cantidad de réplicas en **Azure Monitor** (visualizables en Grafana).

---

## 1. Preparación (una sola vez)

1. Iniciar sesión en Azure CLI:
   ```powershell
   az login
   ```
2. Registrar los proveedores necesarios en la suscripción de estudiante:
   ```powershell
   az provider register --namespace Microsoft.App
   az provider register --namespace Microsoft.OperationalInsights
   az provider register --namespace Microsoft.ContainerService
   ```
3. Copiar el archivo de variables de ejemplo y completar `subscription_id` y `otel_exporter_otlp_headers`:
   ```powershell
   cd infra/terraform
   cp terraform.tfvars.example terraform.tfvars
   ```

---

## 2. Crear o actualizar la infraestructura

```powershell
terraform init
terraform plan
terraform apply
```

Al terminar, Terraform muestra las 3 URLs públicas:
* `m2_front_url`: para abrir el Frontend en el navegador (usuario de prueba: `cliente-demo` / contraseña: `ds2026`, u operador: `operador-demo` / `ds2026`).
* `m2_api_url`: URL de la API (`/docs` para Swagger, `/health` para estado, y destino de las pruebas de estrés con **k6**).
* `keycloak_url`: consola y servidor de identidad.

---

## 3. Actualización continua desde GitHub Actions (`desplegar.yml`)

Una vez creada la infraestructura con Terraform, cada push a `desarrollo-m2` o `main` que pase `CI` y `Publicar imagen en GHCR` dispara automáticamente `.github/workflows/desplegar.yml`, que actualiza las imágenes de `m2-api` y `m2-front` en Azure Container Apps.

También se puede ejecutar manualmente desde la pestaña **Actions → Desplegar en Azure Container Apps → Run workflow**, eligiendo el tag de la imagen y la cantidad de réplicas (`min_replicas` y `max_replicas`) para comparar pruebas de k6 con **1 réplica fija** vs. **auto-escalado horizontal**.

### Secreto requerido en GitHub

En el repositorio (`Settings → Secrets and variables → Actions`), crear el secreto **`AZURE_CREDENTIALS`** con permisos acotados únicamente al grupo de recursos `rg-m2-g01`:

```powershell
az ad sp create-for-rbac --name "sp-github-m2-g01" --role contributor --scopes /subscriptions/<TU_SUBSCRIPTION_ID>/resourceGroups/rg-m2-g01 --sdk-auth
```

*(Si el secreto `AZURE_CREDENTIALS` no está definido o el entorno en Azure está apagado con `terraform destroy`, el workflow `desplegar.yml` omite el despliegue sin marcar error en los pushes).*

---

## 4. Cuidar el crédito de Azure for Students

Cuando no se esté usando el entorno, se puede destruir por completo con:

```powershell
terraform destroy
```

y volver a recrear en ~3 minutos con `terraform apply` antes de la demostración.
