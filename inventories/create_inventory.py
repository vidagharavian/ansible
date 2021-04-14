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
            data.set_variable(key, 'ansible_winrm_server_cert_validation', 'ignore')
        else:
            data.set_variable(key, 'ansible_connection', 'ssh')
        for host in hosts:
            data.add_host(host, group=key)
            # data.set_variable(host, 'ansible_become_user','administrator')
            # data.set_variable(host, 'ansible_become', 'yes')
            # data.set_variable(host, 'ansible_become_password', 'Mp3b27')
    data.reconcile_inventory()
    inventory = InventoryManager(loader=loader)
    inventory._inventory = data
    variable_manager.set_inventory(inventory)
    return inventory

