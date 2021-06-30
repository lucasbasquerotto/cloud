#!/usr/bin/python

# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=import-error

# pyright: reportUnusedImport=true
# pyright: reportUnusedVariable=true
# pyright: reportMissingImports=false

from __future__ import absolute_import, division, print_function

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import error_text
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_node_dependencies import (
    prepare_host_dependencies
)
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_params_mixer import mix

from ansible.errors import AnsibleError
from ansible.module_utils._text import to_text


class FilterModule(object):
  def filters(self):
    return {
        'node_dict_dependencies': self.node_dict_dependencies,
        'node_dns_service_info': self.node_dns_service_info,
        'params_mixer': self.params_mixer,
        'simple_to_list': self.simple_to_list,
        'simple_dict_prop': self.simple_dict_prop,
        'simple_dict_prop_list': self.simple_dict_prop_list,
        'validate_connection': self.validate_connection,
    }

  def node_dict_dependencies(
      self,
      node_dict_dependencies,
      hosts_data,
      instance_type,
      instance_index,
      ignore_unknown_nodes=None,
  ):
    info = prepare_host_dependencies(
        node_dict_dependencies=node_dict_dependencies,
        hosts_data=hosts_data,
        instance_type=instance_type,
        instance_index=instance_index,
        ignore_unknown_nodes=ignore_unknown_nodes,
    )

    result = info.get('result')
    error_msgs = info.get('error_msgs')

    if error_msgs:
      raise AnsibleError(to_text(error_text(error_msgs, 'params_mixer')))

    return result

  def node_dns_service_info(self, dns_service, active_host, state):
    ipv4 = active_host.get('public_ipv4') or ''
    ipv6 = active_host.get('public_ipv6') or ''
    ip_map = dict(A=ipv4, AAAA=ipv6)

    def prepare_item(item):
      value = ip_map.get(item.get('dns_type'))

      if (state != 'absent') and not value:
        return None

      if item.get('value'):
        raise AnsibleError(
            'the dns record value is defined explicitly for the '
            + 'node dns service record in the parameters list (should empty '
            + 'to be be defined later based on the node ip)'
        )

      item['value'] = value
      return item

    skip_info = dict(skip=True, service=dict())

    if not dns_service:
      return skip_info

    if not state:
      raise AnsibleError(
          'the state is not defined for the node dns service'
      )
    elif state not in ['present', 'absent']:
      raise AnsibleError(
          'the state defined for the node dns service is invalid'
      )

    if not isinstance(dns_service, dict):
      dns_service = dict(name=dns_service)

    if (state == 'absent') and (not dns_service.get('can_destroy')):
      return skip_info

    params = dns_service.get('params') or dict()

    if params.get('dns_type'):
      raise AnsibleError(
          'the dns type is defined explicitly for the node dns service '
          + 'record (should be let empty to be defined later)'
      )

    if params.get('value'):
      raise AnsibleError(
          'the dns record value is defined explicitly for the '
          + 'node dns service record (should empty to be be defined later '
          + 'based on the node ip)'
      )

    params_list_aux = [
        prepare_item(item)
        for item in (params.get('list') or [])
    ]
    params_list = [i for i in params_list_aux if i is not None]

    params['list'] = params_list

    result_service = dns_service.copy()
    result_service['params'] = params

    return dict(skip=False, service=result_service)

  def params_mixer(self, params_args):
    info = mix(params_args)

    result = info.get('result')
    error_msgs = info.get('error_msgs')

    if error_msgs:
      raise AnsibleError(to_text(error_text(error_msgs, 'params_mixer')))

    return result

  def simple_to_list(self, simple_list):
    if simple_list is None:
      return []

    if isinstance(simple_list, list):
      return simple_list

    return [simple_list]

  def simple_dict_prop(self, simple_dict, prop):
    if simple_dict is None:
      return None

    if isinstance(simple_dict, dict):
      return simple_dict

    result = dict()
    result[prop] = simple_dict

    return result

  def simple_dict_prop_list(self, input_list, prop):
    if input_list is None:
      return None

    if not isinstance(input_list, list):
      raise AnsibleError(
          '[simple_dict_prop_list] value should be a list, '
          + 'found: ' + str(type(input_list))
      )

    result_list = map(
        lambda item: self.simple_dict_prop(item, prop),
        input_list
    )

    return result_list

  def validate_connection(self, node, env_info):
    node_name = node.get('name')
    local_node = node.get('local')

    local_connection = env_info.get('local_connection')
    instance_type = env_info.get('instance_type')
    env_node_name = env_info.get('env_node')

    valid = (
        (
            (local_node and local_connection)
            or
            (
                (not local_node)
                and
                (node_name == instance_type)
            )
        )
        and
        ((not env_node_name) or (env_node_name == node_name))
    )

    return valid
