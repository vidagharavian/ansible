import json
import shutil

from ansible import constants
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory.host import Host
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.playbook import Play
from ansible.plugins.callback import CallbackBase
from ansible.vars.manager import VariableManager
from inventories.config import Config


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

    def __init__(self):
        self.ip_address = None
        self.package = None
        self.connection_type = None
        self.connection_port = None
        self.connection_user = None

    def _install(self):
        # initialize needed objects
        loader = DataLoader()  # Takes care of finding and reading yml, json and ini files
        loader.set_basedir('../playbooks')

        # create inventory, use path to host config file as source or hosts in a comma separated string
        host_list = [self.ip_address]
        hosts = ','.join(host_list)
        if len(host_list) == 1:
            hosts += ','

        passwords = dict()

        host = Host(name=self.ip_address)
        inventory = InventoryManager(loader=loader,sources=hosts)
        # inventory.add_host(host.get_name())

        results_callback = ResultsCollectorJSONCallback()


        # variable manager takes care of merging all the different sources
        # to give you a unified view of variables available in each context
        variable_manager = VariableManager(loader=loader, inventory=inventory)
        variable_manager.set_host_variable(host, 'ansible_connection', self.connection_type)
        # variable_manager.set_host_variable(host, 'ansible_host', self.ip_address)
        variable_manager.set_host_variable(host, 'ansible_port', self.connection_port)
        variable_manager.set_host_variable(host, 'ansible_user', self.connection_user)
        # variable_manager.set_host_variable(host, 'ansible_ssh_private_key_file', finders.find('provider/ansible.pem'))



        package = [self.package]
        # create data structure that represents our play
        # including tasks, this is basically what our YAML loader does internally.

        print(f'hosts : {hosts} \n roles : {package}')

        play_source = {
            'hosts': hosts,
            'gather_facts': True,
            'roles': package
        }

        tqm = TaskQueueManager(
            inventory=inventory,
            variable_manager=variable_manager,
            loader=loader,
            passwords=passwords,
            stdout_callback=results_callback,
        )

        # Create play object, playbook objects use .load instead of init or new methods,
        # this will also automatically create the task objects from the info provided in play_source
        play = Play().load(play_source, variable_manager=variable_manager, loader=loader)

        # Actually run it
        try:
            result = tqm.run(play)  # most interesting data for a play is actually sent to the callback's methods
        finally:
            # we always need to cleanup child procs and the structures we use to communicate with them
            tqm.cleanup()
            if loader:
                loader.cleanup_all_tmp_files()

        print("UP ***********")
        for host, result in results_callback.host_ok.items():
            print('{0} >>> {1}'.format(host, result._result['stdout']))

        print("FAILED *******")
        for host, result in results_callback.host_failed.items():
            print('{0} >>> {1}'.format(host, result._result['msg']))

        print("DOWN *********")
        for host, result in results_callback.host_unreachable.items():
            print('{0} >>> {1}'.format(host, result._result['msg']))


    def run(self, ip_address, package,
            connection_type, connection_user,
            connection_port):

        print(f'ip: {ip_address}, connection_user: {connection_user}')

        self.ip_address = ip_address
        self.package = package
        self.connection_type = connection_type
        self.connection_port = connection_port
        self.connection_user = connection_user
        self._install()
PackageInstallerTask().run(ip_address=Config['ubuntu_hosts'][0],package='ansible-role-ping',connection_type='ssh',connection_user='administrator',connection_port=22,)