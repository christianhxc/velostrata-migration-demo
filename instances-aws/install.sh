#! /bin/bash
sudo apt-get update
sudo apt-get install -y apache2
sudo systemctl start apache2
sudo systemctl enable apache2
echo "<h1>Hello! Where am I?</h1>" | sudo tee /var/www/html/index.html

wget https://storage.googleapis.com/velostrata-release/V4.2.0/Latest/velostrata-prep_4.2.0.deb
sudo dpkg -i velostrata-prep_4.2.0.deb
sudo apt-get install -f -y