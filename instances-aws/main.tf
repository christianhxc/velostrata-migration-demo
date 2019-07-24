provider "aws" {
  region = "us-west-2"
  shared_credentials_file = "${pathexpand("/home/christianhxc/.aws/credentials_autonetdeploy")}"
}

data "aws_vpc" "default" {
  id = "vpc-0a26321f01c6d3181"
}

data "aws_subnet_ids" "all" {
  vpc_id = "${data.aws_vpc.default.id}"
}

resource "aws_security_group" "allow_http" {
  name        = "eqx-apache"
  description = "Allow HTTP inbound traffic"
  vpc_id      = "${data.aws_vpc.default.id}"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    cidr_blocks     = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "apache" {
  ami           = "ami-07b4f3c02c7f83d59" // Ubuntu 18.04 LTS
  instance_type = "t2.micro"

  subnet_id     = "subnet-0072479d8e8bcc093"
  security_groups = ["${aws_security_group.allow_http.id}"]
  associate_public_ip_address = true

  tags = {
    "Name"     = "eqx-eps-apache-${count.index}"
    "Env"      = "Private"
    "Migrate"  = "Yes"
  }

  key_name = "eqx-eps-velostrata"

  user_data = <<-EOT
    #! /bin/bash
    sudo apt-get update
    sudo apt-get install -y apache2
    sudo systemctl start apache2
    sudo systemctl enable apache2
    echo "<h1>Hello, I'm Server # ${count.index}! Where am I?</h1>" | sudo tee /var/www/html/index.html

    wget https://storage.googleapis.com/velostrata-release/V4.2.0/Latest/velostrata-prep_4.2.0.deb
    sudo dpkg -i velostrata-prep_4.2.0.deb
    sudo apt-get install -f -y

    sudo sed -i -E 's/(GRUB_CMDLINE_LINUX)="(.+)"/\1="\2 cloud-init=disabled"/' /etc/default/grub
    sudo update-grub
    sudo shutdown -r now
  EOT

  count = 1

}
