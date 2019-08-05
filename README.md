# Migrating Workloads to GCP with Velostrata


## Setup for GCP.

### Creating GCP roles and service accounts via Cloud Shell

You have to have Python 3 installed.

```
cd ./prepare-gcp/iam
python3 velostrata_sa_roles.py -p [YOUR-PROJECT_ID] -d [DEPLOYMENT_NAME]
```

### Creating the GCP Network Connectivity via Terraform

You have to use Terraform 0.11

```
cd ./prepare-gcp/terraform
./gcp_set_credentials.sh exists
gcloud config set project [YOUR-PROJECT_ID]
./gcp_set_project.sh
terraform init
terraform validate
terraform plan
terraform apply
terraform output
terraform show
```

