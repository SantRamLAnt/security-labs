# LAB J — an Electronic Security Perimeter (NERC CIP-005) drawn in Azure, as code.
# Three zones: corporate, an intermediate system (jump host subnet), and a control-centre
# zone that only the intermediate system may reach. SYNTHETIC; plan only, never applied.
terraform {
  required_providers { azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" } }
}
provider "azurerm" {
  features {}
  resource_provider_registrations = "none"
}

resource "azurerm_resource_group" "esp" {
  name     = "labj-esp-rg"
  location = "eastus"
  tags     = { teardown = "true", lab = "lab-j" }
}

resource "azurerm_virtual_network" "esp" {
  name                = "labj-vnet"
  resource_group_name = azurerm_resource_group.esp.name
  location            = azurerm_resource_group.esp.location
  address_space       = ["10.40.0.0/16"]
}

resource "azurerm_subnet" "corporate" {
  name                 = "corporate"
  resource_group_name  = azurerm_resource_group.esp.name
  virtual_network_name = azurerm_virtual_network.esp.name
  address_prefixes     = ["10.40.1.0/24"]
}

resource "azurerm_subnet" "intermediate" {
  name                 = "intermediate-system"
  resource_group_name  = azurerm_resource_group.esp.name
  virtual_network_name = azurerm_virtual_network.esp.name
  address_prefixes     = ["10.40.2.0/27"]
}

resource "azurerm_subnet" "control_centre" {
  name                 = "control-centre"
  resource_group_name  = azurerm_resource_group.esp.name
  virtual_network_name = azurerm_virtual_network.esp.name
  address_prefixes     = ["10.40.10.0/24"]
}

resource "azurerm_network_security_group" "control_centre" {
  name                = "labj-nsg-control-centre"
  resource_group_name = azurerm_resource_group.esp.name
  location            = azurerm_resource_group.esp.location
  tags                = { zone = "control-centre" }
}

resource "azurerm_network_security_rule" "cc_rdp_from_intermediate" {
  name                        = "allow-rdp-from-intermediate-system"
  description                 = "CIP-005 R2: interactive remote access only through the intermediate system, MFA enforced there"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "3389"
  source_address_prefix       = "10.40.2.0/27"
  destination_address_prefix  = "10.40.10.0/24"
  resource_group_name         = azurerm_resource_group.esp.name
  network_security_group_name = azurerm_network_security_group.control_centre.name
}

resource "azurerm_network_security_rule" "cc_deny_all_inbound" {
  name                        = "deny-all-inbound"
  description                 = "CIP-005 R1.3: deny by default; every allow above carries its reason"
  priority                    = 4096
  direction                   = "Inbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.esp.name
  network_security_group_name = azurerm_network_security_group.control_centre.name
}

resource "azurerm_subnet_network_security_group_association" "cc" {
  subnet_id                 = azurerm_subnet.control_centre.id
  network_security_group_id = azurerm_network_security_group.control_centre.id
}
