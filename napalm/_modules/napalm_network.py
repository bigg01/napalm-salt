# -*- coding: utf-8 -*-
'''
NAPALM Network
===============

Basic methods for interaction with the network device through the virtual proxy 'napalm'.

:codeauthor: Mircea Ulinic <mircea@cloudflare.com> & Jerome Fleury <jf@cloudflare.com>
:maturity:   new
:depends:    napalm
:platform:   unix

Dependencies
------------

- :mod:`napalm proxy minion <salt.proxy.napalm>`

.. versionadded:: Carbon
'''

from __future__ import absolute_import

# Import python lib
import logging
log = logging.getLogger(__name__)

# salt libs
from salt.ext import six

try:
    # will try to import NAPALM
    # https://github.com/napalm-automation/napalm
    # pylint: disable=W0611
    from napalm_base import get_network_driver
    # pylint: enable=W0611
    HAS_NAPALM = True
except ImportError:
    HAS_NAPALM = False

# ----------------------------------------------------------------------------------------------------------------------
# module properties
# ----------------------------------------------------------------------------------------------------------------------

__virtualname__ = 'net'
__proxyenabled__ = ['napalm']
# uses NAPALM-based proxy to interact with network devices

# ----------------------------------------------------------------------------------------------------------------------
# property functions
# ----------------------------------------------------------------------------------------------------------------------


def __virtual__():

    '''
    NAPALM library must be installed for this module to work.
    Also, the key proxymodule must be set in the __opts___ dictionary.
    '''

    if HAS_NAPALM and 'proxy' in __opts__:
        return __virtualname__
    else:
        return (False, 'The module NET (napalm_network) cannot be loaded: \
                napalm or proxy could not be loaded.')

# ----------------------------------------------------------------------------------------------------------------------
# helper functions -- will not be exported
# ----------------------------------------------------------------------------------------------------------------------


def _filter_list(input_list, search_key, search_value):

    '''
    Filters a list of dictionary by a set of key-value pair.

    :param input_list:   is a list of dictionaries
    :param search_key:   is the key we are looking for
    :param search_value: is the value we are looking for the key specified in search_key
    :return:             filered list of dictionaries
    '''

    output_list = list()

    for dictionary in input_list:
        if dictionary.get(search_key) == search_value:
            output_list.append(dictionary)

    return output_list


def _filter_dict(input_dict, search_key, search_value):

    '''
    Filters a dictionary of dictionaries by a key-value pair.

    :param input_dict:    is a dictionary whose values are lists of dictionaries
    :param search_key:    is the key in the leaf dictionaries
    :param search_values: is the value in the leaf dictionaries
    :return:              filtered dictionary
    '''

    output_dict = dict()

    for key, key_list in six.iteritems(input_dict):
        key_list_filtered = _filter_list(key_list, search_key, search_value)
        if key_list_filtered:
            output_dict[key] = key_list_filtered

    return output_dict


def _config_logic(loaded_result, test=False, commit_config=True):

    '''
    Builds the config logic for `load_config` and `load_template` functions.
    '''

    loaded_result['already_configured'] = False

    _compare = compare_config()
    if _compare.get('result', False):
        loaded_result['diff'] = _compare.get('out')
        loaded_result.pop('out', '')  # not needed

    _loaded_res = loaded_result.get('result', False)

    if not _loaded_res or test:
        # if unable to load the config (errors / warnings)
        # or in testing mode,
        # will discard the config
        if loaded_result['comment']:
            loaded_result['comment'] += '\n'
        if not len(loaded_result.get('diff', '')) > 0:
            loaded_result['already_configured'] = True
        _discarded = discard_config()
        if not _discarded.get('result', False):
            loaded_result['comment'] += _discarded['comment'] if _discarded['comment'] else 'Unable to discard config.'
            loaded_result['result'] = False
            # make sure it notifies
            # that something went wrong
            return loaded_result

        loaded_result['comment'] += 'Configuration discarded.'
        # loaded_result['result'] = False not necessary
        # as the result can be true when test=True
        return loaded_result

    if not test and commit_config:
        if len(loaded_result.get('diff', '')) > 0:
            # if not testing mode
            # and also the user wants to commit (default)
            # and there are changes to commit
            _commit = commit()  # calls the function commit, defined below
            if not _commit.get('result', False):
                loaded_result['comment'] += _commit['comment'] if _commit['comment'] else 'Unable to commit config.'
                loaded_result['result'] = False
                _discarded = discard_config()  # unable to commit, discard config
                loaded_result['comment'] +=  '\n'
                loaded_result['comment'] += _discarded['comment'] if _discarded['comment'] else 'Unable to discard config.'

        else:
            # would like to commit, but there's no change
            # need to call discard_config() to release the config DB
            _discarded = discard_config()
            if not _discarded.get('result', False):
                loaded_result['comment'] += _discarded['comment'] if _discarded['comment'] else 'Unable to discard config.'
                loaded_result['result'] = False
                # notify if anything goes wrong
                return loaded_result
            loaded_result['already_configured'] = True
            loaded_result['comment'] = 'Already configured.'

    return loaded_result


# ----------------------------------------------------------------------------------------------------------------------
# callable functions
# ----------------------------------------------------------------------------------------------------------------------


def connected():
    '''
    Specifies if the proxy succeeded to connect to the network device.

    CLI Example:

    .. code-block:: bash

        salt '*' net.connected
    '''

    return {
        'out': __proxy__['napalm.ping']()
    }


def facts():
    '''
    Returns characteristics of the network device.
    :return: a dictionary with the following keys:

        * uptime - Uptime of the device in seconds.
        * vendor - Manufacturer of the device.
        * model - Device model.
        * hostname - Hostname of the device
        * fqdn - Fqdn of the device
        * os_version - String with the OS version running on the device.
        * serial_number - Serial number of the device
        * interface_list - List of the interfaces of the device

    CLI Example:

    .. code-block:: bash

        salt '*' net.facts

    Example output:

    .. code-block:: python

        {
            'os_version': u'13.3R6.5',
            'uptime': 10117140,
            'interface_list': [
                'lc-0/0/0',
                'pfe-0/0/0',
                'pfh-0/0/0',
                'xe-0/0/0',
                'xe-0/0/1',
                'xe-0/0/2',
                'xe-0/0/3',
                'gr-0/0/10',
                'ip-0/0/10'
            ],
            'vendor': u'Juniper',
            'serial_number': u'JN131356FBFA',
            'model': u'MX480',
            'hostname': u're0.edge05.syd01',
            'fqdn': u're0.edge05.syd01'
        }
    '''

    return __proxy__['napalm.call'](
        'get_facts',
        **{
        }
    )


def environment():
    '''
    Returns the environment of the device.

    CLI Example:

    .. code-block:: bash

        salt '*' net.environment


    Example output:

    .. code-block:: python

        {
            'fans': {
                'Bottom Rear Fan': {
                    'status': True
                },
                'Bottom Middle Fan': {
                    'status': True
                },
                'Top Middle Fan': {
                    'status': True
                },
                'Bottom Front Fan': {
                    'status': True
                },
                'Top Front Fan': {
                    'status': True
                },
                'Top Rear Fan': {
                    'status': True
                }
            },
            'memory': {
                'available_ram': 16349,
                'used_ram': 4934
            },
            'temperature': {
               'FPC 0 Exhaust A': {
                    'is_alert': False,
                    'temperature': 35.0,
                    'is_critical': False
                }
            },
            'cpu': {
                '1': {
                    '%usage': 19.0
                },
                '0': {
                    '%usage': 35.0
                }
            }
        }
    '''

    return __proxy__['napalm.call'](
        'get_environment',
        **{
        }
    )


def cli(*commands):

    '''
    Returns a dictionary with the raw output of all commands passed as arguments.

    :param commands: list of commands to be executed on the device
    :return: a dictionary with the mapping between each command and its raw output

    CLI Example:

    .. code-block:: bash

        salt '*' net.cli "show version" "show chassis fan"

    Example output:

    .. code-block:: python

        {
            u'show version and haiku':  u'Hostname: re0.edge01.arn01
                                          Model: mx480
                                          Junos: 13.3R6.5
                                            Help me, Obi-Wan
                                            I just saw Episode Two
                                            You're my only hope
                                         ',
            u'show chassis fan' :   u'Item                      Status   RPM     Measurement
                                      Top Rear Fan              OK       3840    Spinning at intermediate-speed
                                      Bottom Rear Fan           OK       3840    Spinning at intermediate-speed
                                      Top Middle Fan            OK       3900    Spinning at intermediate-speed
                                      Bottom Middle Fan         OK       3840    Spinning at intermediate-speed
                                      Top Front Fan             OK       3810    Spinning at intermediate-speed
                                      Bottom Front Fan          OK       3840    Spinning at intermediate-speed
                                     '
        }
    '''

    return __proxy__['napalm.call'](
        'cli',
        **{
            'commands': list(commands)
        }
    )
    # thus we can display the output as is
    # in case of errors, they'll be catched in the proxy


def traceroute(destination, source='', ttl=0, timeout=0):

    '''
    Calls the method traceroute from the NAPALM driver object and returns a dictionary with the result of the traceroute
    command executed on the device.

    :param destination: Hostname or address of remote host
    :param source: Source address to use in outgoing traceroute packets
    :param ttl: IP maximum time-to-live value (or IPv6 maximum hop-limit value)
    :param timeout: Number of seconds to wait for response (seconds)

    CLI Example:

    .. code-block:: bash

        salt '*' net.traceroute 8.8.8.8
        salt '*' net.traceroute 8.8.8.8 source=127.0.0.1 ttl=5 timeout=1
    '''

    return __proxy__['napalm.call'](
        'traceroute',
        **{
            'destination': destination,
            'source': source,
            'ttl': ttl,
            'timeout': timeout
        }
    )


def ping(destination, source='', ttl=0, timeout=0, size=0, count=0):

    '''
    Executes a ping on the network device and returns a dictionary as a result.

    :param destination: Hostname or IP address of remote host
    :param source: Source address of echo request
    :param ttl: IP time-to-live value (IPv6 hop-limit value) (1..255 hops)
    :param timeout: Maximum wait time after sending final packet (seconds)
    :param size: Size of request packets (0..65468 bytes)
    :param count: Number of ping requests to send (1..2000000000 packets)

    CLI Example:

    .. code-block:: bash

        salt '*' net.ping 8.8.8.8
        salt '*' net.ping 8.8.8.8 ttl=3 size=65468
        salt '*' net.ping 8.8.8.8 source=127.0.0.1 timeout=1 count=100
    '''

    return __proxy__['napalm.call'](
        'ping',
        **{
            'destination': destination,
            'source': source,
            'ttl': ttl,
            'timeout': timeout,
            'size': size,
            'count': count
        }
    )


def arp(interface='', ipaddr='', macaddr=''):

    '''
    NAPALM returns a list of dictionaries with details of the ARP entries.

    :param interface: interface name to filter on
    :param ipaddr: IP address to filter on
    :param macaddr: MAC address to filter on
    :return: List of the entries in the ARP table

    CLI Example:

    .. code-block:: bash

        salt '*' net.arp
        salt '*' net.arp macaddr='5c:5e:ab:da:3c:f0'

    Example output:

    .. code-block:: python

        [
            {
                'interface' : 'MgmtEth0/RSP0/CPU0/0',
                'mac'       : '5c:5e:ab:da:3c:f0',
                'ip'        : '172.17.17.1',
                'age'       : 1454496274.84
            },
            {
                'interface': 'MgmtEth0/RSP0/CPU0/0',
                'mac'       : '66:0e:94:96:e0:ff',
                'ip'        : '172.17.17.2',
                'age'       : 1435641582.49
            }
        ]
    '''

    proxy_output = __proxy__['napalm.call'](
        'get_arp_table',
        **{
        }
    )

    if not proxy_output.get('result'):
        return proxy_output

    arp_table = proxy_output.get('out')

    if interface:
        arp_table = _filter_list(arp_table, 'interface', interface)

    if ipaddr:
        arp_table = _filter_list(arp_table, 'ip', ipaddr)

    if macaddr:
        arp_table = _filter_list(arp_table, 'mac', macaddr)

    proxy_output.update({
        'out': arp_table
    })

    return proxy_output


def ipaddrs():

    '''
    Returns IP addresses configured on the device.


    :return:   A dictionary with the IPv4 and IPv6 addresses of the interfaces.\
    Returns all configured IP addresses on all interfaces as a dictionary of dictionaries.\
    Keys of the main dictionary represent the name of the interface.\
    Values of the main dictionary represent are dictionaries that may consist of two keys\
    'ipv4' and 'ipv6' (one, both or none) which are themselvs dictionaries witht the IP addresses as keys.\

    CLI Example:

    .. code-block:: bash

        salt '*' net.ipaddrs

    Example output:

    .. code-block:: python

        {
            u'FastEthernet8': {
                u'ipv4': {
                    u'10.66.43.169': {
                        'prefix_length': 22
                    }
                }
            },
            u'Loopback555': {
                u'ipv4': {
                    u'192.168.1.1': {
                        'prefix_length': 24
                    }
                },
                u'ipv6': {
                    u'1::1': {
                        'prefix_length': 64
                    },
                    u'2001:DB8:1::1': {
                        'prefix_length': 64
                    },
                    u'FE80::3': {
                        'prefix_length': u'N/A'
                    }
                }
            }
        }
    '''

    return __proxy__['napalm.call'](
        'get_interfaces_ip',
        **{
        }
    )


def interfaces():

    '''
    Returns details of the interfaces on the device.

    :return: Returns a dictionary of dictionaries. \
    The keys for the first dictionary will be the interfaces in the devices.

    CLI Example:

    .. code-block:: bash

        salt '*' net.interfaces

    Example output:

    .. code-block:: python

        {
            u'Management1': {
                'is_up': False,
                'is_enabled': False,
                'description': u'',
                'last_flapped': -1,
                'speed': 1000,
                'mac_address': u'dead:beef:dead',
            },
            u'Ethernet1':{
                'is_up': True,
                'is_enabled': True,
                'description': u'foo',
                'last_flapped': 1429978575.1554043,
                'speed': 1000,
                'mac_address': u'beef:dead:beef',
            }
        }
    '''

    return __proxy__['napalm.call'](
        'get_interfaces',
        **{
        }
    )


def lldp(interface=''):

    '''
    Returns a detailed view of the LLDP neighbors.

    :param interface: interface name to filter on
    :return:          A dictionary with the LLDL neighbors.\
    The keys are the interfaces with LLDP activated on.

    CLI Example:

    .. code-block:: bash

        salt '*' net.lldp
        salt '*' net.lldp interface='TenGigE0/0/0/8'

    Example output:

    .. code-block:: python

        {
            'TenGigE0/0/0/8': [
                {
                    'parent_interface': u'Bundle-Ether8',
                    'interface_description': u'TenGigE0/0/0/8',
                    'remote_chassis_id': u'8c60.4f69.e96c',
                    'remote_system_name': u'switch',
                    'remote_port': u'Eth2/2/1',
                    'remote_port_description': u'Ethernet2/2/1',
                    'remote_system_description': u'Cisco Nexus Operating System (NX-OS) Software 7.1(0)N1(1a)
                          TAC support: http://www.cisco.com/tac
                          Copyright (c) 2002-2015, Cisco Systems, Inc. All rights reserved.',
                    'remote_system_capab': u'B, R',
                    'remote_system_enable_capab': u'B'
                }
            ]
        }
    '''

    proxy_output = __proxy__['napalm.call'](
        'get_lldp_neighbors_detail',
        **{
        }
    )

    if not proxy_output.get('result'):
        return proxy_output

    lldp_neighbors = proxy_output.get('out')

    if interface:
        lldp_neighbors = {interface: lldp_neighbors.get(interface)}

    proxy_output.update({
        'out': lldp_neighbors
    })

    return proxy_output


def mac(address='', interface='', vlan=0):

    '''
    Returns the MAC Address Table on the device.

    :param address:   MAC address to filter on
    :param interface: Interface name to filter on
    :param vlan:      VLAN identifier
    :return:          A list of dictionaries representing the entries in the MAC Address Table

    CLI Example:

    .. code-block:: bash

        salt '*' net.mac
        salt '*' net.mac vlan=10

    Example output:

    .. code-block:: python

        [
            {
                'mac'       : '00:1c:58:29:4a:71',
                'interface' : 'xe-3/0/2',
                'static'    : False,
                'active'    : True,
                'moves'     : 1,
                'vlan'      : 10,
                'last_move' : 1454417742.58
            },
            {
                'mac'       : '8c:60:4f:58:e1:c1',
                'interface' : 'xe-1/0/1',
                'static'    : False,
                'active'    : True,
                'moves'     : 2,
                'vlan'      : 42,
                'last_move' : 1453191948.11
            }
        ]
    '''

    proxy_output = __proxy__['napalm.call'](
        'get_mac_address_table',
        **{
        }
    )

    if not proxy_output.get('result'):
        # if negative, leave the output unchanged
        return proxy_output

    mac_address_table = proxy_output.get('out')

    if vlan and isinstance(vlan, int):
        mac_address_table = _filter_list(mac_address_table, 'vlan', vlan)

    if address:
        mac_address_table = _filter_list(mac_address_table, 'mac', address)

    if interface:
        mac_address_table = _filter_list(mac_address_table, 'interface', interface)

    proxy_output.update({
        'out': mac_address_table
    })

    return proxy_output


# <---- Call NAPALM getters --------------------------------------------------------------------------------------------

# ----- Configuration specific functions ------------------------------------------------------------------------------>


def load_config(filename=None, text=None, test=False, commit=True):

    '''
    Populates the candidate configuration. It can be loaded from a file or from a string. If you send both a
    filename and a string containing the configuration, the file takes precedence.
    If you use this method the existing configuration will be merged with the candidate configuration once
    you commit the changes.
    Be aware that by default this method will commit the configuration. If there are no changes, it does not commit and
    the flag `already_configured` will be set as `True` to point this out.

    :param filename: Path to the file containing the desired configuration. By default is None.
    :param text: String containing the desired configuration.
    :param test: Dry run? If set as True, will apply the config, discard and return the changes. Default: False
    and will commit the changes on the device.
    :param commit: Commit? (default: True) Sometimes it is not needed to commit the config immediately
                   after loading the changes. E.g.: a state loads a couple of parts (add / remove / update)
                   and would not be optimal to commit after each operation.
                   Also, from the CLI when the user needs to apply the similar changes before committing,
                   can specify commit=False and will not discard the config.

    :raise MergeConfigException: If there is an error on the configuration sent.

    :return a dictionary having the following keys:

        * result (bool): if the config was applied successfully. It is `False` only in case of failure. In case
        there are no changes to be applied and successfully performs all operations it is still `True` and so will be
        the `already_configured` flag (example below)
        * comment (str): a message for the user
        * already_configured (bool): flag to check if there were no changes applied
        * diff (str): returns the config changes applied

    CLI Example:

    .. code-block:: bash

        salt '*' net.load_config text='ntp peer 192.168.0.1'
        salt '*' net.load_config filename='/absolute/path/to/your/file'
        salt '*' net.load_config filename='/absolute/path/to/your/file' test=True
        salt '*' net.load_config filename='/absolute/path/to/your/file' commit=False

    Example output:

    .. code-block:: python

        {
            'comment': 'Configuration discarded.',
            'already_configured': False,
            'result': True,
            'diff': '[edit interfaces xe-0/0/5]\n+   description "Adding a description";'
        }
    '''

    _loaded = __proxy__['napalm.call'](
        'load_merge_candidate',
        **{
            'filename': filename,
            'config': text
        }
    )

    return _config_logic(_loaded, test=test, commit_config=commit)


def load_template(template_name,
                  template_source=None,
                  template_path=None,
                  test=False,
                  commit=True,
                  **template_vars):

    '''
    Renders a configuration template (Jinja) and loads the result on the device.
    By default will commit the changes. To force a dry run, set `test=True`.

    :param template_name: Identifies the template name.
    :param template_source (optional): Inline config template to be rendered and loaded on the device.
    :param template_path (optional): Specifies the absolute path to a different directory for the configuration \
    templates. If not specified, by default will use the default templates defined in NAPALM.
    :param test: Dry run? If set to True, will apply the config, discard and return the changes. Default: False and
    will commit the changes on the device.
    :param commit: Commit? (default: True) Sometimes it is not needed to commit the config immediately
                   after loading the changes. E.g.: a state loads a couple of parts (add / remove / update)
                   and would not be optimal to commit after each operation.
                   Also, from the CLI when the user needs to apply the similar changes before committing,
                   can specify commit=False and will not discard the config.
    :param template_vars: Dictionary with the arguments to be used when the template is rendered.

    :return a dictionary having the following keys:

        * result (bool): if the config was applied successfully. It is `False` only in case of failure. In case
        there are no changes to be applied and successfully performs all operations it is still `True` and so will be
        the `already_configured` flag (example below)
        * comment (str): a message for the user
        * already_configured (bool): flag to check if there were no changes applied
        * diff (str): returns the config changes applied

    The template can use variables from the ``grains``, ``pillar`` or ``opts```, for example:

    .. code-block:: jinja

        {% set router_model = grains.get('model') -%}
        {% set router_vendor = grains.get('vendor') -%}
        {% set hostname = pillar.get('proxy', {}).get('host') -%}
        {% if router_vendor|lower == 'juniper' %}
        system {
            host-name {{hostname}};
        }
        {% endif %}

    CLI Example:

    .. code-block:: bash

        salt '*' net.load_template ntp_peers peers=[192.168.0.1]  # uses NAPALM default templates
        salt '*' net.load_template set_hostname template_source='system {\n\tdomain-name {{domain_name}};}' \
        domain_name='test.com'
        salt '*' net.load_template my_template template_path='/tmp/tpl/' my_param='aaa'  # will commit
        salt '*' net.load_template my_template template_path='/tmp/tpl/' my_param='aaa' test=True  # dry run

    Example output:

    .. code-block:: python

        {
            'comment': '',
            'already_configured': False,
            'result': True,
            'diff': '[edit system]\n+  host-name edge01.bjm01;''
        }
    '''

    load_templates_params = template_vars.copy()  # to leave the template_vars unchanged
    load_templates_params.update(
        {
            'template_name': template_name,
            'template_source': template_source,  # inline template
            'template_path': template_path,
            'pillar': __pillar__,  # inject pillar content, accessible as `pillar`
            'grains': __grains__,  # inject grains, accessible as `grains`
            'opts': __opts__  # inject opts, accessible as `opts`
        }
    )

    _loaded = __proxy__['napalm.call']('load_template',
                                       **load_templates_params
                                       )

    return _config_logic(_loaded,
                         test=test,
                         commit_config=commit)


def commit():

    '''
    Commits the configuration changes made on the network device.

    CLI Example:

    .. code-block:: bash

        salt '*' net.commit
    '''

    return __proxy__['napalm.call'](
        'commit_config',
        **{}
    )


def discard_config():

    """
    Discards the changes applied.

    CLI Example:

    .. code-block:: bash

        salt '*' net.discard_config
    """

    return __proxy__['napalm.call'](
        'discard_config',
        **{}
    )


def compare_config():

    '''
    Returns the difference between the running config and the candidate config.

    CLI Example:

    .. code-block:: bash

        salt '*' net.compare_config
    '''

    return __proxy__['napalm.call'](
        'compare_config',
        **{}
    )


def rollback():

    '''
    Rollbacks the configuration.

    CLI Example:

    .. code-block:: bash

        salt '*' net.rollback
    '''

    return __proxy__['napalm.call'](
        'rollback',
        **{}
    )


def config_changed():

    '''
    Will prompt if the configuration has been changed.

    :return: A tuple with a boolean that specifies if the config was changed on the device.\
    And a string that provides more details of the reason why the configuration was not changed.

    CLI Example:

    .. code-block:: bash

        salt '*' net.config_changed
    '''

    is_config_changed = False
    reason = ''
    try_compare = compare_config()

    if try_compare.get('result'):
        if try_compare.get('out'):
            is_config_changed = True
        else:
            reason = 'Configuration was not changed on the device.'
    else:
        reason = try_compare.get('comment')

    return is_config_changed, reason


def config_control():

    '''
    Will check if the configuration was changed.
    If differences found, will try to commit.
    In case commit unsuccessful, will try to rollback.

    :return: A tuple with a boolean that specifies if the config was changed/commited/rollbacked on the device.\
    And a string that provides more details of the reason why the configuration was not commited properly.

    CLI Example:

    .. code-block:: bash

        salt '*' net.config_control
    '''

    result = True
    comment = ''

    changed, not_changed_reason = config_changed()
    if not changed:
        return (changed, not_changed_reason)

    # config changed, thus let's try to commit
    try_commit = commit()
    if not try_commit.get('result'):
        result = False
        comment = 'Unable to commit the changes: {reason}.\n\
        Will try to rollback now!'.format(
            reason=try_commit.get('comment')
        )
        try_rollback = rollback()
        if not try_rollback.get('result'):
            comment += '\nCannot rollback! {reason}'.format(
                reason=try_rollback.get('comment')
            )

    return result, comment

# <---- Configuration specific functions -------------------------------------------------------------------------------
