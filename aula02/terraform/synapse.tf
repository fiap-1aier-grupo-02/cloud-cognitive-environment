resource "azurerm_storage_account" "synapse" {
  name                     = "stsynapse${random_string.sufixo.result}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  is_hns_enabled = true

  tags = local.tags
}

resource "azurerm_storage_data_lake_gen2_filesystem" "synapse" {
  name               = "synapsefs"
  storage_account_id = azurerm_storage_account.synapse.id
}

resource "azurerm_synapse_workspace" "qc" {
  name                                 = "synapse-qc-${random_string.sufixo.result}"
  resource_group_name                  = azurerm_resource_group.rg.name
  location                             = azurerm_resource_group.rg.location
  storage_data_lake_gen2_filesystem_id = azurerm_storage_data_lake_gen2_filesystem.synapse.id

  sql_administrator_login          = "synadmin"
  sql_administrator_login_password = var.sql_admin_password

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

resource "azurerm_synapse_firewall_rule" "all_azure" {
  name                 = "AllowAllWindowsAzureIps"
  synapse_workspace_id = azurerm_synapse_workspace.qc.id
  start_ip_address     = "0.0.0.0"
  end_ip_address       = "0.0.0.0"
}

output "synapse_workspace_name" {
  value = azurerm_synapse_workspace.qc.name
}

output "synapse_storage_account_name" {
  value = azurerm_storage_account.synapse.name
}

output "synapse_filesystem_name" {
  value = azurerm_storage_data_lake_gen2_filesystem.synapse.name
}
