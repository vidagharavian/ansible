import json
import yaml
from smtplib import SMTPServerDisconnected
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from identity.models import ProjectToken, UserResourceManagement
from identity.email import send_email
from provider.tasks.package_installer_task import PackageInstallerTask

from task_result.base_task import BaseTask
from provider.celery_clients import get_scoped_connection

from openstack.exceptions import ResourceFailure, ResourceTimeout

from provider.utils import internal_to_external_address
from utils.exceptions import ServiceUnavailable


class CreateInstanceTask():
    #: Name of the task.
    name = 'CreateInstanceTask'

    def __init__(self):
        self.client = None
        self.validated_data = None
        self.current_flavor = None
        self.user_id = None
        self.flavor = None
        self.ansible_keypair = None

    def _create_instance(self):
        image = self.client.compute.get_image(image=self.validated_data['image_id'])
        user_email = self.validated_data['email']
        volumes = self.validated_data.get('volumes', [])
        configure_data = self.validated_data.get('set_password', False)
        password = None

        servers = []
        for count in range(self.validated_data['count']):
            if self.validated_data['set_password']:
                # set ssh and console password for server
                password = 'alaki'

                # https://cloudinit.readthedocs.io/en/latest/topics/format.html#cloud-config-data
                config = {'password': password, 'chpasswd': '{ expire: True }', 'ssh_pwauth': True}
                # 'ssh_authorized_keys': [self.ansible_keypair.public_key]}
                # "#cloud-config" comment NEEDED to distinct script and configuration files
                configure_data = ("#cloud-config\n\n" + yaml.dump(config)).replace("'", "")

            instance_name = self.validated_data['name'] if self.validated_data['count'] == 1 else f"{self.validated_data['name']}-{count + 1}"
            created_instance = self.client.create_server(name=instance_name,
                                                         image=self.validated_data['image_id'],
                                                         flavor=self.validated_data['flavor_id'],
                                                         network=[{"id": self.validated_data['network']['id']}],
                                                         key_name=self.validated_data['key_name'],
                                                         userdata=configure_data,
                                                         config_drive=True)

            servers.append({"server": self.client.compute.get_server(server=created_instance.id), "password": password})
        try:
            email_contexts = []
            for server_dic in servers:
                server = server_dic['server']
                password = server_dic['password']
                self.client.compute.wait_for_server(server=server, wait=2700)

                for volume in volumes:
                    volume_created = self.client.create_volume(name=volume['name'],
                                                               size=volume['size'], wait=True)
                    # the volume is not deleted when the instance is terminated
                    self.client.compute.create_volume_attachment(server=server, volume_id=volume_created.id)

                external_ip, ssh_port = internal_to_external_address(next(iter(server.addresses.values()))[0]['addr'])

                if self.validated_data['package']:
                    # update server metadata
                    # todo package id
                    self.client.set_server_metadata(server.id, {"Package": str(self.validated_data['package'])})
                    # run package installer celery task
                    package_installer = PackageInstallerTask()
                    # define needed variables
                    _ip = next(iter(server.addresses.values()))[0]['addr']
                    _connection_user = image.metadata['os_admin_user']
                    # todo windows user
                    # todo move to develop
                    if image.metadata['os_distro'] == 'Windows Server':
                        _connection_type = 'winrm'
                        _connection_port = '5985'
                    else:
                        _connection_type = 'ssh'
                        _connection_port = '22'

                    package_installer.delay(ip_address=_ip, package=self.validated_data['package'],
                                            connection_type=_connection_type, connection_user=_connection_user,
                                            connection_port=_connection_port)

                email_contexts.append({
                    'instance_name': server.name,
                    'instance_internal_ip': next(iter(server.addresses.values()))[0]['addr'],
                    'instance_external_ip': external_ip,
                    'instance_ssh_port': ssh_port,
                    'instance_username': image.metadata['os_admin_user'],
                    'instance_password': password if self.validated_data['set_password'] else False,
                    'domain': settings.DOMAIN,
                    'static_domain': settings.STATIC_DOMAIN,
                    'help_email': settings.EMAIL_HELP_ADDRESS,
                })

            send_email(target=user_email, subject='Creating Server', template='server_creation.html',
                       context={"contexts": email_contexts})

        except (ResourceFailure, ResourceTimeout):
            raise Exception(_("Server transitioned to ERROR state"))
        except SMTPServerDisconnected:
            raise ServiceUnavailable(detail=_("Problem connecting to mail server"))

        return servers

    def _resource_manager(self):
        current_flavor = self.current_flavor
        validated_data = self.validated_data
        flavor = self.flavor

        resources = UserResourceManagement.objects.get(user__keystone_id=self.user_id)
        resources.cpu -= flavor['vcpus'] * validated_data['count'] - current_flavor['vcpus']
        resources.ram -= flavor['ram'] * validated_data['count'] - current_flavor['ram']
        resources.disk_server -= flavor['disk'] * validated_data['count'] - current_flavor['disk']
        resources.save()

    def run(self, project_token_id, validated_data, flavor, current_flavor, user_id, ansible_keypair):
        # ToDo: remove project_token_id and use get_superuser_scoped_connection
        project_token = ProjectToken.objects.get(pk=project_token_id)
        self.client = get_scoped_connection(project_token)
        self.validated_data = validated_data
        self.current_flavor = current_flavor
        self.user_id = user_id
        self.flavor = json.loads(flavor)
        self.ansible_keypair = ansible_keypair

        self._create_instance()
        self._resource_manager()
