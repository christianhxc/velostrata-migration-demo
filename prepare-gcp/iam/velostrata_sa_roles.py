#!/usr/bin/env python3
# coding=utf-8

import argparse
import io
import json
import re
import subprocess
import sys


class GcloudException(Exception):
    def __init__(self, created_id, message=""):
        self.created_id = created_id
        self.message = message

    def is_resource_already_exists(self):
        return 'already exists' in self.message


class Gcloud(object):
    google_apis = ['iam.googleapis.com',
                   'cloudresourcemanager.googleapis.com',
                   'compute.googleapis.com',
                   'storage-component.googleapis.com']

    mgmt_role_id = 'velos_manager'
    mgmt_role_desc = 'Velostrata Manager'
    mgmt_role_title = 'Velostrata Manager'

    ce_role_id = 'velos_ce'
    ce_role_desc = 'Velostrata Storage Access'
    ce_role_title = 'Velostrata Storage Access'

    mgmt_sa_id = 'velos-manager'
    mgmt_sa_name = 'Velostrata Manager'

    ce_sa_id = 'velos-cloud-extension'
    ce_sa_name = 'Velostrata Cloud Extension'

    def __init__(self, deployment_name, project_id, org_id, ignore_iam_failures):
        self.deployment_name = deployment_name
        self.project_id = project_id
        self.org_id = org_id
        self.ignore_iam_failures = ignore_iam_failures

        self.mgmt_role_id += '_' + self.deployment_name
        self.mgmt_role_title += ' ' + self.deployment_name
        self.mgmt_sa_id += '-' + self.deployment_name
        self.mgmt_sa_name += ' ' + self.deployment_name

        self.ce_role_id += '_' + self.deployment_name
        self.ce_role_title += ' ' + self.deployment_name
        self.ce_sa_id += '-' + self.deployment_name
        self.ce_sa_name += ' ' + self.deployment_name

        with open(sys.path[0] + '/iam.json') as f:
            self.iam = json.load(f)

    def _get_project(self):
        return 'project ' + self.project_id

    def enable_apis(self):
        for api in self.iam['apis']:
            result = subprocess.run(['gcloud', 'services', 'enable', api, '--project', self.project_id],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if self.ignore_iam_failures is False and result.returncode is not 0:
                raise Exception('Failed to enable API: ' + api + '. ' + result.stderr.decode('utf-8'))

    def create_manager_role(self):
        if self.org_id is not None:
            parent_flag = '--organization'
            parent_id = self.org_id
            parent = 'organization ' + self.org_id
        else:
            parent_flag = '--project'
            parent_id = self.project_id
            parent = self._get_project()

        return self._create_role(parent_flag, parent_id, self.mgmt_role_desc, self.mgmt_role_id,
                                 self.iam['mgmt']['permissions'], self.mgmt_role_title, parent)

    def create_ce_role(self):
        return self._create_role('--project', self.project_id, self.ce_role_desc, self.ce_role_id,
                                 self.iam['ce']['permissions'], self.ce_role_title, self._get_project())

    def create_manager_sa(self):
        already_exists = None
        try:
            result = self._create_sa(self.mgmt_sa_id, self.mgmt_sa_name, self.mgmt_role_id, self.iam['mgmt']['roles'],
                                     self.org_id is not None)
        except GcloudException as e:
            if not e.is_resource_already_exists():
                raise e
            else:
                already_exists = e

        full_sa_id = self.to_full_sa_id(self.mgmt_sa_id)
        token_creator_result = subprocess.run(
            ['gcloud', 'iam', 'service-accounts', 'add-iam-policy-binding', full_sa_id,
             '--member=serviceAccount:' + full_sa_id,
             '--role=roles/iam.serviceAccountTokenCreator',
             '--project', self.project_id,
             '-q'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if token_creator_result.returncode is not 0:
            raise GcloudException('', token_creator_result.stderr.decode('utf-8'))

        if already_exists is not None:
            raise already_exists

        return result

    def create_ce_sa(self):
        return self._create_sa(self.ce_sa_id, self.ce_sa_name, self.ce_role_id, self.iam['ce']['roles'])

    def _create_sa(self, sa_id, sa_name, role_id, roles, org=False):
        already_exists = None

        try:
            self._inner_create_sa(sa_id, sa_name)
        except GcloudException as e:
            if not e.is_resource_already_exists():
                raise e
            else:
                already_exists = e

        if org:
            roles.append('organizations/' + self.org_id + '/roles/' + role_id)
            self._add_policy_binding(sa_id, roles, org=True)
        else:
            roles.append('projects/' + self.project_id + '/roles/' + role_id)
            self._add_policy_binding(sa_id, roles)

        if already_exists is not None:
            raise already_exists

        return self.to_full_sa_id(sa_id)

    def _create_role(self, parent_flag, parent_id, role_desc, role_id, role_permissions, role_title, parent_str):
        result = subprocess.run(
            ['gcloud', 'iam', 'roles', 'create', '-q', role_id,
             parent_flag, parent_id,
             '--description', role_desc,
             '--stage', 'GA',
             '--title', role_title,
             '--permissions', ','.join(role_permissions)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        created_id = '{0} in: {1}'.format(role_id, parent_str)
        if result.returncode is not 0:
            raise GcloudException(created_id, result.stderr.decode('utf-8'))

        return created_id

    def _inner_create_sa(self, sa_id, sa_name):
        result = subprocess.run(
            ['gcloud', 'iam', 'service-accounts', 'create', sa_id, '-q',
             '--display-name', sa_name, '--project', self.project_id],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        created_id = '{0} in: {1}'.format(sa_id, self._get_project())
        if result.returncode is not 0:
            raise GcloudException(created_id, result.stderr.decode('utf-8'))

        return created_id

    def _add_policy_binding(self, sa_id, roles, org=False):
        full_sa_id = self.to_full_sa_id(sa_id)

        if org:
            level = 'organizations'
            level_id = self.org_id
        else:
            level = 'projects'
            level_id = self.project_id

        for role in roles:
            command = ['gcloud', level, 'add-iam-policy-binding', level_id,
                       '--member=serviceAccount:' + full_sa_id,
                       '--role=' + role]

            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if result.returncode is not 0:
                raise GcloudException('', result.stderr.decode('utf-8'))

    def to_full_sa_id(self, sa_id):
        return sa_id + '@' + self.project_id + '.iam.gserviceaccount.com'


class Creator(object):

    def __init__(self, gcloud):
        self.gcloud = gcloud

    def _create(self, obj_name, creator_method):
        try:
            print('Created ' + obj_name + ': ' + creator_method())
        except GcloudException as e:
            if e.is_resource_already_exists():
                print(obj_name + ': ' + e.created_id + ' already exists')
            else:
                print('Failed creating ' + obj_name + '. ' + e.message)
                exit(-1)
        except Exception as e:
            print(e.message)
            exit(-1)

    def create(self):
        self.gcloud.enable_apis()

        self._create('Velostrata Manager role', self.gcloud.create_manager_role)
        self._create('Velostrata Storage Access role', self.gcloud.create_ce_role)
        self._create('Velostrata Manager service account', self.gcloud.create_manager_sa)
        self._create('Velostrata Cloud Extension service account', self.gcloud.create_ce_sa)


def deployment_name_type(s, pat=re.compile(r"^[a-z0-9]{1,8}$")):
    if not pat.match(s):
        raise argparse.ArgumentTypeError(
            'Deployment name can be 1-8 characters long and can only contain lowercase characters and numbers')
    return s


def main():
    example_text = '''Examples:

1. Creation of service Accounts for migration into multiple projects under the same Org
	./velostrata_sa_roles.py -d deployment1 -p my-project-id -o 123451234   
2. Creation of service Accounts for migration into single GCP Project
    ./velostrata_sa_roles.py -d deployment1 -p my-project-id'''

    parser = argparse.ArgumentParser(
        description='''*** Creating Velostrata GCP Roles and Service Accounts - Automation Script ***

This script will create the required Service Accounts with the Velostrata roles for Velostrata deployment.
The output is Service Accounts for the Velostrata Manager and Service Account for Velostrata Cloud Extension.

The script supports the following migration scenarios:
1. Migration of VMs into multiple GCP Project under the same GCP Org.
2. Migration of VMs into a single GCP Project

You will need to provide the created Service Accounts to the Velostrata marketplace deployment form
https://pantheon.corp.google.com/marketplace/details/click-to-deploy-images/velostrata''',
        epilog=example_text,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    optional = parser._action_groups.pop()

    required_named = parser.add_argument_group('required named arguments')
    required_named.add_argument('-d', '--deployment-name',
                                help="The deployment's suffix that will be appended to Service Account and Role names. Must be less than 8 characters and can only contain lowercase letters and numbers.",
                                required=True,
                                type=deployment_name_type)
    required_named.add_argument('-p', '--project-id', help='The ID of the GCP project will host your migration.',
                                required=True)

    optional.add_argument('-o', '--org-id', help='Takes a numeric GCP organization ID.', required=False)
    optional.add_argument('-i', '--ignore-iam-failures', help=argparse.SUPPRESS, required=False, action='store_true')

    parser._action_groups.append(optional)

    args = parser.parse_args()

    gcloud = Gcloud(args.deployment_name, args.project_id, args.org_id, args.ignore_iam_failures)
    Creator(gcloud).create()


if __name__ == "__main__":
    main()
