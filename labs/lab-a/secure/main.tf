# LAB A — REMEDIATED BASELINE
# This one passes the policy gate and is safe to apply.
# Own Azure subscription only.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
}

variable "prefix" {
  type    = string
  default = "labasec"
}

variable "location" {
  type    = string
  default = "eastus"
}

resource "azurerm_resource_group" "lab" {
  name     = "${var.prefix}-rg"
  location = var.location
  tags = {
    purpose   = "security-lab"
    owner     = "luis"
    teardown  = "yes"
  }
}

resource "azurerm_storage_account" "good" {
  name                     = "${var.prefix}good01"
  resource_group_name      = azurerm_resource_group.lab.name
  location                 = azurerm_resource_group.lab.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  # CONTROL 1 — CIS Azure (storage public access) / NIST SC-28 / CIP-011 R1
  allow_nested_items_to_be_public = false

  # CONTROL 2 — CIS Azure (minimum TLS) / NIST SC-8
  min_tls_version = "TLS1_2"

  # CONTROL 3 — CIS Azure (secure transfer required) / NIST SC-8
  https_traffic_only_enabled = true

  tags = {
    purpose  = "security-lab"
    teardown = "yes"
  }
}
