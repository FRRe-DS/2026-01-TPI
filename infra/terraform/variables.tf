variable "subscription_id" {
  description = "ID de la suscripción de Azure (az account show --query id -o tsv)."
  type        = string
}

variable "grupo" {
  description = "Identificador del grupo para nombrar los recursos en Azure."
  type        = string
  default     = "g01"
}

variable "region" {
  description = "Región de Azure permitida en tu suscripción de estudiante (por ejemplo: brazilsouth, eastus, eastus2, southcentralus, chilecentral)."
  type        = string
  default     = "brazilsouth"
}

variable "m2_api_image" {
  description = "Imagen de la API de M2 publicada en GHCR."
  type        = string
  default     = "ghcr.io/frre-ds/2026-01-tpi-api:desarrollo-m2"
}

variable "m2_front_image" {
  description = "Imagen del Frontend de M2 publicada en GHCR."
  type        = string
  default     = "ghcr.io/frre-ds/2026-01-tpi-front:desarrollo-m2"
}

variable "m6_image" {
  description = "Imagen publicada en GHCR del Módulo 6 (Viajes) con el que se integra M2 (Grupo 12 soporta RS256/Keycloak)."
  type        = string
  default     = "ghcr.io/frre-ds/m6-viajes-g12:sha-37db0f6"
}

variable "m6_puerto" {
  description = "Puerto en el que escucha el contenedor de M6 (Grupo 12 usa 3006)."
  type        = number
  default     = 3006
}

variable "m2_min_replicas" {
  description = "Mínimo de réplicas para M2 API (1 para pruebas sin escalado; 2+ para alta disponibilidad)."
  type        = number
  default     = 1
}

variable "m2_max_replicas" {
  description = "Máximo de réplicas para M2 API (1 para pruebas sin réplicas; 5 para mostrar auto-escalado bajo carga con k6)."
  type        = number
  default     = 3
}

variable "m2_http_concurrency_scale" {
  description = "Cantidad de peticiones HTTP concurrentes por réplica a partir de la cual Azure Container Apps escala horizontalmente M2 API."
  type        = number
  default     = 50
}

# --- Variables de OpenTelemetry (Grafana Cloud / OTLP) ---

variable "otel_service_name" {
  description = "Nombre del servicio en Grafana / OpenTelemetry."
  type        = string
  default     = "m2-clientes-grupo01"
}

variable "otel_exporter_otlp_endpoint" {
  description = "Endpoint OTLP de Grafana Cloud (ej: https://otlp-gateway-prod-sa-east-1.grafana.net/otlp)."
  type        = string
  default     = "https://otlp-gateway-prod-sa-east-1.grafana.net/otlp"
}

variable "otel_exporter_otlp_headers" {
  description = "Header Authorization para Grafana Cloud OTLP (Authorization=Basic ...). Se pasa en terraform.tfvars (no se sube a Git)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "otel_resource_attributes" {
  description = "Atributos extra del recurso OpenTelemetry."
  type        = string
  default     = "grupo=grupo01"
}
