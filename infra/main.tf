# LAB A/E — REMEDIATED STORAGE BASELINE (what the gates accept)
# Own Azure subscription only. Disposable lab resource (teardown tag).

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
    purpose  = "security-lab"
    owner    = "luis"
    teardown = "yes"
  }
}

resource "azurerm_storage_account" "good" {
  # Accepted risks for a disposable, data-free lab account. Each skip is a decision,
  # written down with its reason, not a silenced warning:
  #checkov:skip=CKV2_AZURE_1:No data stored; customer-managed keys need a Key Vault the lab does not justify
  #checkov:skip=CKV2_AZURE_33:No VNet in this lab; public network access is disabled instead
  #checkov:skip=CKV_AZURE_206:LRS is deliberate for a disposable lab account; production would use GRS/ZRS
  name                     = "${var.prefix}good01"
  resource_group_name      = azurerm_resource_group.lab.name
  location                 = azurerm_resource_group.lab.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  # CIS Azure storage public access / NIST SC-28 / NERC CIP-011-3 R1
  allow_nested_items_to_be_public = false
  public_network_access_enabled   = false

  # CIS Azure minimum TLS and secure transfer / NIST SC-8
  min_tls_version            = "TLS1_2"
  https_traffic_only_enabled = true

  # Identity-based access only (NIST IA-2): no account keys
  shared_access_key_enabled = false

  sas_policy {
    expiration_period = "01.00:00:00"
    expiration_action = "Log"
  }

  blob_properties {
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
  }

  queue_properties {
    logging {
      delete                = true
      read                  = true
      write                 = true
      version               = "1.0"
      retention_policy_days = 7
    }
  }

  tags = {
    purpose  = "security-lab"
    teardown = "yes"
  }
}
