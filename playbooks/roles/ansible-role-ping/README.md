# Ansible Role: Ping

An ansible role to ping hosts to ensure they are reachable and satisfy required dependencies.

> **NOTE** This uses the native ping module bundled with ansible.

## Requirements

> This role has been tested on `Ubuntu 16.04` and `Ubuntu 16.10` only.

## Usage Example

```yaml
- hosts: all
  roles:
    - thedumbtechguy.ping
```


## License

MIT / BSD

## Author Information

This role was created by [TheDumbTechGuy](https://github.com/thedumbtechguy) ( [twitter](https://twitter.com/frostymarvelous) | [blog](https://thedumbtechguy.blogspot.com) | [galaxy](https://galaxy.ansible.com/thedumbtechguy/) )

## Credits