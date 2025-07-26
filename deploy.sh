#!/bin/bash
git pull origin main
pip install -r requirements.txt
systemctl restart myapp
echo "Deployment complete: $(date)"
