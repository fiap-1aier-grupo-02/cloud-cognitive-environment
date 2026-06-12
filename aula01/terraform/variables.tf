variable "location" {
  type    = string
  default = "eastus2"
}

variable "resource_group_name" {
  type    = string
  default = "rg-iac-aula01"
}

variable "vm_size" {
  type    = string
  default = "Standard_D2s_v3"
}

variable "admin_username" {
  type    = string
  default = "azureuser"
}

variable "ssh_public_key_path" {
  type    = string
  default = "~/.ssh/id_rsa.pub"
}

# [3.1 - item 1] IP autorizado no SSH (curl -s ifconfig.me); aplicado como ${var.meu_ip}/32 no NSG
variable "meu_ip" {
  type = string

  validation {
    condition     = can(regex("^([0-9]{1,3}\\.){3}[0-9]{1,3}$", var.meu_ip))
    error_message = "meu_ip deve ser um IPv4 válido, ex.: 200.123.45.67 (sem /32)."
  }
}