output "resource_group_name" {
  description = "Nombre del grupo de recursos en Azure (para el workflow desplegar.yml)."
  value       = azurerm_resource_group.m2.name
}

output "m2_api_url" {
  description = "URL pública HTTPS de la API de M2 Clientes (para pruebas y k6)."
  value       = "https://${azurerm_container_app.m2_api.ingress[0].fqdn}"
}

output "m2_front_url" {
  description = "URL pública HTTPS del Frontend de M2 Clientes."
  value       = "https://${azurerm_container_app.m2_front.ingress[0].fqdn}"
}

output "keycloak_url" {
  description = "URL pública HTTPS de Keycloak (usuario: cliente-demo / pass: ds2026, admin: admin / pass: ds2026)."
  value       = "https://${azurerm_container_app.keycloak.ingress[0].fqdn}"
}
