# Networking

## Disable IPv6

```shell
sudo tee "/etc/sysctl.d/local-disable-ipv6.conf" >/dev/null <<EOF
net.ipv6.conf.all.disable_ipv6=1
net.ipv6.conf.default.disable_ipv6=1
EOF
# reload configs
sudo service procps force-reload
# verify
netplan status
```

# Set up DNS with Cloudflare, Google, Quad

!!! WARNING
    Not working properly.

<https://wiki.archlinux.org/title/systemd-resolved>
<https://man7.org/linux/man-pages/man5/resolved.conf.d.5.html>

```shell
sudo mkdir -p /etc/systemd/resolved.conf.d
sudo tee "/etc/systemd/resolved.conf.d/99-dns.conf" >/dev/null <<EOF
[Resolve]
DNS=1.1.1.1 1.0.0.1
FallbackDNS=8.8.8.8 8.8.4.4 9.9.9.9
# to prevent systemd-resolved from using the per-link DNS servers, if any of them set Domains=~. in the per-link configuration
Domains=~.
EOF
# reload configs
sudo service systemd-resolved restart
# verify
resolvectl status
netplan status

# set DNS via netplan
# currently disabled as we use systemd-resolved instead
#MAIN_INTERFACE=$(ip route get 8.8.8.8 | awk -- '{printf $5}')
#sudo netplan get network.ethernets.${MAIN_INTERFACE}
#set DNS for main interface
#sudo netplan set network.ethernets.${MAIN_INTERFACE}.nameservers.addresses=[1.1.1.1, 1.0.0.1]
```