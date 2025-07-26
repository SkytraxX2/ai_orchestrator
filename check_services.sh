#!/bin/bash
for service in nginx apache2 mysql ssh; do
  echo -n "$service: "
  ps aux | grep -v grep | grep $service >/dev/null && echo "running" || echo "stopped"
done
