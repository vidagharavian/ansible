import shutil

from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory.host import Host
from ansible.parsing.dataloader import DataLoader
from ansible.playbook import Play
from ansible.plugins.callback import CallbackBase
import json
import ansible.constants as C
from ansible.vars.manager import VariableManager


from inventories.config import Config
from inventories.create_inventory import create_inventory


class ResultsCollectorJSONCallback(CallbackBase):
    """A sample callback plugin used for performing an action as results come in.

    If you want to collect all results into a single object for processing at
    the end of the execution, look into utilizing the ``json`` callback plugin
    or writing your own custom callback plugin.
    """

    def __init__(self, *args, **kwargs):
        super(ResultsCollectorJSONCallback, self).__init__(*args, **kwargs)
        self.host_ok = {}
        self.host_unreachable = {}
        self.host_failed = {}

    def v2_runner_on_unreachable(self, result):
        host = result._host
        self.host_unreachable[host.get_name()] = result

    def v2_runner_on_ok(self, result, *args, **kwargs):
        """Print a json representation of the result.

        Also, store the result in an instance attribute for retrieval later
        """
        host = result._host
        self.host_ok[host.get_name()] = result
        print(json.dumps({host.name: result._result}, indent=4))

    def v2_runner_on_failed(self, result, *args, **kwargs):
        host = result._host
        self.host_failed[host.get_name()] = result

class PackageInstallerTask():
    #: Name of the task.
    name = 'PackageInstallerTask'

    def __init__(self,host_dict):
        self.package = None
        self.connection_type = None
        self.connection_port = None
        self.connection_user = None
        self.ansible_password=None
        self.loader=self.get_loader()
        self.variable_manager=VariableManager(loader=self.loader)
        self.inventory=create_inventory(host_dict,self.variable_manager,self.loader,self.ansible_password)


    def get_loader(self,base_dir='../playbooks'):
        loader = DataLoader()  # Takes care of finding and reading yml, json and ini files
        loader.set_basedir(base_dir)
        return loader
    def variable_manager_initialization(self,ip_address):
        for host in self.inventory._inventory.hosts.values():
            for group in host.groups:
                if group.name == 'ubuntu':
                            self.variable_manager.set_host_variable(host, 'ansible_connection', self.connection_type)
                            self.variable_manager.set_host_variable(host, 'ansible_host', ip_address)
                            self.variable_manager.set_host_variable(host, 'ansible_port', self.connection_port)
                            self.variable_manager.set_host_variable(host, 'ansible_user', self.connection_user)
                            self.variable_manager.set_host_variable(host, 'ansible_ssh_private_key_file',
                                                               '/home/ansible/.ssh/id_rsa')
                            self.variable_manager.set_host_variable(host,'ansible_become_user',self.connection_user)
                            self.variable_manager.set_host_variable(host,'ansible_become','yes')
                            self.variable_manager.set_host_variable(host,'ansible_become_password','Mp3b27')
                if group.name == 'windows':
                            self.variable_manager.set_host_variable(host, 'ansible_user',self.connection_user)
                            self.variable_manager.set_host_variable(host, 'ansible_password', self.ansible_password)
                            self.variable_manager.set_host_variable(host, 'ansible_port', self.connection_port)
                            self.variable_manager.set_host_variable(host, 'ansible_username', self.connection_user)
                            self.variable_manager.set_host_variable(host, 'ansible_connection', 'winrm')
                            self.variable_manager.set_host_variable(host, 'ansible_winrm_transport', 'ntlm')
                            self.variable_manager.set_host_variable(host, 'ansible_winrm_server_cert_validation', 'ignore')

    def _install(self,ip_address):
        # initialize needed objects
        # self.variable_manager_initialization(ip_address)
        host_list = [ip_address]
        hosts = ','.join(host_list)
        if len(host_list) == 1:
            hosts += ','

        package = [self.package]
        # create data structure that represents our play
        # including tasks, this is basically what our YAML loader does internally.

        print(f'hosts : {ip_address} \n roles : {package}')

        play_source = {
            'hosts': hosts,
            'gather_facts': True,
            'become':True,
            'become_user':'root',
            'become_method':'sudo',
            'roles': package
        }
        passwords = dict()
        results_callback = ResultsCollectorJSONCallback()
        tqm = TaskQueueManager(
            inventory=self.inventory,
            variable_manager=self.variable_manager,
            loader=self.loader,
            passwords=passwords,
            stdout_callback=results_callback,
        )

        # Create play object, playbook objects use .load instead of init or new methods,
        # this will also automatically create the task objects from the info provided in play_source
        play = Play().load(play_source, variable_manager=self.variable_manager, loader=self.loader,vars={'ansible_become_pass':'Mp3b27'})

        # Actually run it
        try:
            result = tqm.run(play)  # most interesting data for a play is actually sent to the callback's methods
        finally:
            # we always need to cleanup child procs and the structures we use to communicate with them
            tqm.cleanup()
            if self.loader:
                self.loader.cleanup_all_tmp_files()
        shutil.rmtree(C.DEFAULT_LOCAL_TMP, True)
        print("UP ***********")
        for host, result in results_callback.host_ok.items():
            print('{0} >>> {1}'.format(host, result._result))

        print("FAILED *******")
        for host, result in results_callback.host_failed.items():
            print('{0} >>> {1}'.format(host, result._result['msg']))

        print("DOWN *********")
        for host, result in results_callback.host_unreachable.items():
            print('{0} >>> {1}'.format(host, result._result['msg']))


    def run(self, ip_address, package,
            connection_type, connection_user,
            connection_port,ansible_password):

        print(f'ip: {ip_address}, connection_user: {connection_user}')

        self.package = package
        self.connection_type = connection_type
        self.connection_port = connection_port
        self.connection_user = connection_user
        self.ansible_password=ansible_password
        self._install(ip_address)
host=Config['ubuntu'][0]
PackageInstallerTask(Config).run(ip_address=host['host_ip'],package='rm_ssh_key',connection_type=host['connection_type'],connection_user=host['username'],connection_port=host['connection_port'],ansible_password=host['password'])