from ansible.inventory.data import InventoryData
from ansible.inventory.manager import InventoryManager


def create_inventory(host_dict: dict, variable_manager, loader,ansible_password):
    """
    Returns an inventory object for playbook execution.
    Args:
      host_list (list): list of IP addresses or hostnames
      variable_manager (ansible.vars.manager.VariableManager): Ansible variable
          manager for PlaybookExecutor
      loader (ansible.parsing.dataloader.DataLoader): Ansible data loader for
          PlaybookExecutor
    Returns: ansible.inventory.manager.InventoryManager for PlaybookExecutor
    """
    # create inventory and pass to var manager
    data = InventoryData()
    for key, hosts in host_dict.items():
        data.add_group(key)
        if key == "windows":
            data.set_variable(key, 'ansible_connection', 'winrm')
            data.set_variable(key, 'ansible_winrm_transport', 'ntlm')
            data.set_variable(key,'ansible_winrm_scheme','http')
            data.set_variable(key,'ansible_winrm_operation_timeout_sec',40)
            data.set_variable(key,'ansible_winrm_read_timeout_sec',50)
            data.set_variable(key, 'ansible_winrm_server_cert_validation', 'ignore')
        else:
            data.set_variable(key, 'ansible_connection', 'ssh')
        for host in hosts:
            data.add_host(host['host_ip'], group=key,port=host['connection_port'])
            data.set_variable(host['host_ip'], 'user',host['username'])
            data.set_variable(host['host_ip'], 'ansible_password',host['password'])
            data.set_variable(host['host_ip'], 'ansible_user',host['username'])
            data.set_variable(host['host_ip'], 'ansible_become_password',host['password'])
    data.reconcile_inventory()
    inventory = InventoryManager(loader=loader)
    inventory._inventory = data
    variable_manager.set_inventory(inventory)
    return inventory

