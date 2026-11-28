# Infraestructura de Despliegue en Azure Container Apps — M2 Clientes (Grupo 1)
# Compatible con Azure Container Apps Express Environments (Azure for Students):
#   1. keycloak   (quay.io/keycloak/keycloak:23.0.6, ingress externo HTTP 8080, con ds-2026-realm.json inyectado en el arranque)
#   2. m6-viajes  (imagen de M6 publicada en GHCR, con postgres:16.15 como sidecar en el mismo pod localhost:5432)
#   3. m2-api     (ghcr.io/frre-ds/2026-01-tpi-api, con mongo:7.0 como sidecar en el mismo pod localhost:27017, auto-escalado y OTel)
#   4. m2-front   (ghcr.io/frre-ds/2026-01-tpi-front, ingress externo HTTP 80)

locals {
  prefijo = "m2-${var.grupo}"

  etiquetas = {
    proyecto = "tpi-devops-2026"
    modulo   = "m2-clientes"
    grupo    = var.grupo
    gestion  = "terraform"
  }
}

resource "azurerm_resource_group" "m2" {
  name     = "rg-${local.prefijo}"
  location = var.region
  tags     = local.etiquetas
}

# Log Analytics Workspace: recolecta métricas de contenedores y logs para Azure Monitor (conectado a Grafana)
resource "azurerm_log_analytics_workspace" "m2" {
  name                = "law-${local.prefijo}"
  location            = azurerm_resource_group.m2.location
  resource_group_name = azurerm_resource_group.m2.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.etiquetas
}

# Red y entorno compartido de Azure Container Apps
resource "azurerm_container_app_environment" "m2" {
  name                       = "cae-${local.prefijo}"
  location                   = azurerm_resource_group.m2.location
  resource_group_name        = azurerm_resource_group.m2.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.m2.id
  tags                       = local.etiquetas
}

# ---------------------------------------------------------------------------
# 1. Bases de datos (MongoDB para M2 + PostgreSQL para M6 en Azure Container Instances)
# ---------------------------------------------------------------------------
resource "azurerm_container_group" "mongodb" {
  name                = "aci-mongodb-${var.grupo}"
  location            = azurerm_resource_group.m2.location
  resource_group_name = azurerm_resource_group.m2.name
  ip_address_type     = "Public"
  os_type             = "Linux"
  restart_policy      = "Always"
  tags                = local.etiquetas

  container {
    name   = "mongodb"
    image  = "docker.io/library/mongo:7.0"
    cpu    = "0.5"
    memory = "1.0"

    environment_variables = {
      MONGO_INITDB_ROOT_USERNAME = var.mongo_user
    }

    secure_environment_variables = {
      MONGO_INITDB_ROOT_PASSWORD = var.mongo_password
    }

    ports {
      port     = 27017
      protocol = "TCP"
    }
  }

  container {
    name   = "postgres-m6"
    image  = "docker.io/library/postgres:16.15"
    cpu    = "0.5"
    memory = "1.0"

    environment_variables = {
      POSTGRES_USER = var.postgres_user
      POSTGRES_DB   = "m6"
    }

    secure_environment_variables = {
      POSTGRES_PASSWORD = var.postgres_password
    }

    ports {
      port     = 5432
      protocol = "TCP"
    }
  }
}

# ---------------------------------------------------------------------------
# 2. Keycloak (M1 Identidad - con realm ds-2026-realm preconfigurado)
# ---------------------------------------------------------------------------
resource "azurerm_container_app" "keycloak" {
  name                         = "keycloak"
  container_app_environment_id = azurerm_container_app_environment.m2.id
  resource_group_name          = azurerm_resource_group.m2.name
  revision_mode                = "Single"
  tags                         = local.etiquetas

  secret {
    name  = "realm-b64"
    value = base64encode(file("${path.module}/ds-2026-realm.json"))
  }

  secret {
    name  = "kc-admin-password"
    value = var.keycloak_admin_password
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name    = "keycloak"
      image   = "quay.io/keycloak/keycloak:23.0.6"
      cpu     = 0.75
      memory  = "1.5Gi"
      command = ["/bin/bash", "-c"]
      args = [
        "mkdir -p /opt/keycloak/data/import && echo \"$REALM_B64\" | base64 -d > /opt/keycloak/data/import/ds-2026-realm.json && exec /opt/keycloak/bin/kc.sh start-dev --import-realm"
      ]

      env {
        name        = "REALM_B64"
        secret_name = "realm-b64"
      }
      env {
        name  = "KEYCLOAK_ADMIN"
        value = var.keycloak_admin_user
      }
      env {
        name        = "KEYCLOAK_ADMIN_PASSWORD"
        secret_name = "kc-admin-password"
      }
      env {
        name  = "KC_PROXY"
        value = "edge"
      }
      env {
        name  = "KC_HOSTNAME_STRICT"
        value = "false"
      }
      env {
        name  = "KC_HOSTNAME_STRICT_HTTPS"
        value = "false"
      }
      env {
        name  = "KC_HTTP_ENABLED"
        value = "true"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8080
    transport        = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}

# ---------------------------------------------------------------------------
# 3. Módulo 6 (Viajes) — Imagen real publicada en GHCR (Grupo 12 con RS256/Keycloak)
# ---------------------------------------------------------------------------
resource "azurerm_container_app" "m6_viajes" {
  name                         = "m6-viajes"
  container_app_environment_id = azurerm_container_app_environment.m2.id
  resource_group_name          = azurerm_resource_group.m2.name
  revision_mode                = "Single"
  tags                         = local.etiquetas

  secret {
    name  = "database-url"
    value = "postgresql://${var.postgres_user}:${urlencode(var.postgres_password)}@${azurerm_container_group.mongodb.ip_address}:5432/m6?schema=public"
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "m6-viajes"
      image  = var.m6_image
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "PORT"
        value = tostring(var.m6_puerto)
      }
      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
      env {
        name  = "ENABLE_DEMO_AUTH"
        value = tostring(var.m6_enable_demo_auth)
      }
      env {
        name  = "AUTH_ISSUER"
        value = "https://${azurerm_container_app.keycloak.ingress[0].fqdn}/realms/ds-2026-realm"
      }
      env {
        name  = "AUTH_JWKS_URI"
        value = "https://${azurerm_container_app.keycloak.ingress[0].fqdn}/realms/ds-2026-realm/protocol/openid-connect/certs"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = var.m6_puerto
    transport        = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  depends_on = [
    azurerm_container_group.mongodb,
    azurerm_container_app.keycloak
  ]
}

# ---------------------------------------------------------------------------
# 4. M2 Clientes API (Grupo 1) + Auto-escalado + OTel
# ---------------------------------------------------------------------------
resource "azurerm_container_app" "m2_api" {
  name                         = "m2-api"
  container_app_environment_id = azurerm_container_app_environment.m2.id
  resource_group_name          = azurerm_resource_group.m2.name
  revision_mode                = "Single"
  tags                         = local.etiquetas

  secret {
    name  = "mongo-url"
    value = "mongodb://${var.mongo_user}:${urlencode(var.mongo_password)}@${azurerm_container_group.mongodb.ip_address}:27017/?authSource=admin"
  }

  secret {
    name  = "otel-headers"
    value = var.otel_exporter_otlp_headers != "" ? var.otel_exporter_otlp_headers : "Authorization=Basic none"
  }

  template {
    min_replicas = var.m2_min_replicas
    max_replicas = var.m2_max_replicas

    http_scale_rule {
      name                = "http-concurrency"
      concurrent_requests = tostring(var.m2_http_concurrency_scale)
    }

    container {
      name   = "m2-api"
      image  = var.m2_api_image
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "MONGO_URL"
        secret_name = "mongo-url"
      }
      env {
        name  = "MONGO_DB"
        value = "m2_clientes_db"
      }
      env {
        name  = "M6_URL"
        value = "https://${azurerm_container_app.m6_viajes.ingress[0].fqdn}"
      }
      env {
        name  = "JWKS_URL"
        value = "https://${azurerm_container_app.keycloak.ingress[0].fqdn}/realms/ds-2026-realm/protocol/openid-connect/certs"
      }
      env {
        name  = "CORS_ORIGINS"
        value = "https://m2-front.${azurerm_container_app_environment.m2.default_domain}"
      }

      # Variables de OpenTelemetry para Grafana Cloud
      env {
        name  = "OTEL_SERVICE_NAME"
        value = var.otel_service_name
      }
      env {
        name  = "OTEL_EXPORTER_OTLP_ENDPOINT"
        value = var.otel_exporter_otlp_endpoint
      }
      env {
        name        = "OTEL_EXPORTER_OTLP_HEADERS"
        secret_name = "otel-headers"
      }
      env {
        name  = "OTEL_RESOURCE_ATTRIBUTES"
        value = var.otel_resource_attributes
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  depends_on = [
    azurerm_container_group.mongodb,
    azurerm_container_app.keycloak,
    azurerm_container_app.m6_viajes
  ]
}

# ---------------------------------------------------------------------------
# 4. M2 Clientes Frontend (Grupo 1)
# ---------------------------------------------------------------------------
resource "azurerm_container_app" "m2_front" {
  name                         = "m2-front"
  container_app_environment_id = azurerm_container_app_environment.m2.id
  resource_group_name          = azurerm_resource_group.m2.name
  revision_mode                = "Single"
  tags                         = local.etiquetas

  template {
    min_replicas = 1
    max_replicas = 2

    container {
      name   = "m2-front"
      image  = var.m2_front_image
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "VITE_API_URL"
        value = "https://${azurerm_container_app.m2_api.ingress[0].fqdn}"
      }
      env {
        name  = "VITE_KEYCLOAK_URL"
        value = "https://${azurerm_container_app.keycloak.ingress[0].fqdn}"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 80
    transport        = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  depends_on = [
    azurerm_container_app.m2_api,
    azurerm_container_app.keycloak
  ]
}
