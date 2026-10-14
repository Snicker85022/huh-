#!/bin/bash
if ! dig +time=3 +tries=1 @192.168.2.102 google.com >/dev/null 2>&1; then
    logger -t taza-selfheal "dnsmasq failed live query test, restarting"
    systemctl restart dnsmasq
fi
