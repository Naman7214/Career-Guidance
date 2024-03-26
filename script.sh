#!/bin/bash
sudo systemctl stop guido
sudo systemctl start guido
sudo systemctl enable guido
sudo systemctl restart nginx

echo "EC2 restarted successfully!!!!!!!"
