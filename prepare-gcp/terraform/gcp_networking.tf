/*
 * Copyright 2017 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */


/*
 * Terraform networking resources for GCP.
 */

resource "google_compute_network" "gcp-network" {
  name = "gcp-network"
  auto_create_subnetworks = "false"
}

resource "google_compute_subnetwork" "gcp-subnet1" {
  name          = "gcp-subnet1"
  ip_cidr_range = "${var.gcp_subnet1_cidr}"
  network       = "${google_compute_network.gcp-network.name}"
  region        = "${var.gcp_region}"
}

resource "google_compute_subnetwork" "gcp-subnet2" {
  name          = "gcp-subnet2"
  ip_cidr_range = "${var.gcp_subnet2_cidr}"
  network       = "${google_compute_network.gcp-network.name}"
  region        = "${var.gcp_region}"
}

/*
 * ----------VPN Connection----------
 */

resource "google_compute_address" "gcp-vpn-ip" {
  name   = "gcp-vpn-ip"
  region = "${var.gcp_region}"
}

resource "google_compute_vpn_gateway" "gcp-vpn-gw" {
  name    = "gcp-vpn-gw-${var.gcp_region}"
  network = "${google_compute_network.gcp-network.name}"
  region  = "${var.gcp_region}"
}

resource "google_compute_forwarding_rule" "fr_esp" {
  name        = "fr-esp"
  ip_protocol = "ESP"
  ip_address  = "${google_compute_address.gcp-vpn-ip.address}"
  target      = "${google_compute_vpn_gateway.gcp-vpn-gw.self_link}"
}

resource "google_compute_forwarding_rule" "fr_udp500" {
  name        = "fr-udp500"
  ip_protocol = "UDP"
  port_range  = "500-500"
  ip_address  = "${google_compute_address.gcp-vpn-ip.address}"
  target      = "${google_compute_vpn_gateway.gcp-vpn-gw.self_link}"
}

resource "google_compute_forwarding_rule" "fr_udp4500" {
  name        = "fr-udp4500"
  ip_protocol = "UDP"
  port_range  = "4500-4500"
  ip_address  = "${google_compute_address.gcp-vpn-ip.address}"
  target      = "${google_compute_vpn_gateway.gcp-vpn-gw.self_link}"
}

/*
resource "vmware_vpn_tunnel" "gcp-tunnel1" {
  name          = "vmware-tunnel1"
  peer_ip       = "${var.vmware_tunnel_address}"
  shared_secret = "${var.vmware_tunnel_preshared_key}"
  ike_version   = 1

  target_vpn_gateway = "${google_compute_vpn_gateway.gcp-vpn-gw.self_link}"

  router = "${google_compute_router.gcp-router1.name}"

  depends_on = [
    "google_compute_forwarding_rule.fr_esp",
    "google_compute_forwarding_rule.fr_udp500",
    "google_compute_forwarding_rule.fr_udp4500",
  ]
}
*/
