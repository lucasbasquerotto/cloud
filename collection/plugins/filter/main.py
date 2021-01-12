#!/usr/bin/python

# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=import-error

from __future__ import absolute_import, division, print_function

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import error_text
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_params_mixer import mix

from ansible.errors import AnsibleError
from ansible.module_utils._text import to_text


class FilterModule(object):
  def filters(self):
    return {
        'params_mixer': self.params_mixer,
        'simple_to_list': self.simple_to_list,
        'simple_dict_prop': self.simple_dict_prop,
        'simple_dict_prop_list': self.simple_dict_prop_list,
        'validate_connection': self.validate_connection,
    }

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
      raise AnsibleError('[simple_dict_prop_list] value should be a list, ' +
                         'found: ' + str(type(input_list)))

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
                (not local_connection)
                and
                (node_name == instance_type)
            )
        )
        and
        ((not env_node_name) or (env_node_name == node_name))
    )

    return valid
