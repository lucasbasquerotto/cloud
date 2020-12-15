#!/usr/bin/python

# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=import-error

from __future__ import absolute_import, division, print_function

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import error_text
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_content import prepare_content
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_ctx import prepare_services
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_params_mixer import mix

from ansible.errors import AnsibleError
from ansible.module_utils._text import to_text


class FilterModule(object):
  def filters(self):
    return {
        'content': self.content,
        'params_mixer': self.params_mixer,
        'services': self.services,
        'validate_connection': self.validate_connection,
    }

  def content(self, content, env_data, env, custom_dir, validate):
    info = prepare_content(
        content,
        env=env,
        custom_dir=custom_dir,
        env_data=env_data,
        validate=validate if (validate is not None) else True
    )

    result = info.get('result')
    error_msgs = info.get('error_msgs')

    if error_msgs:
      raise AnsibleError(to_text(error_text(error_msgs, 'content')))

    return result

  def params_mixer(self, params_args):
    info = mix(params_args)

    result = info.get('result')
    error_msgs = info.get('error_msgs')

    if error_msgs:
      raise AnsibleError(to_text(error_text(error_msgs, 'params_mixer')))

    return result

  def services(self, services, env_data, validate):
    info = prepare_services(services, env_data, validate, top=True)

    result = info.get('result')
    error_msgs = info.get('error_msgs')

    if error_msgs:
      raise AnsibleError(to_text(error_text(error_msgs, 'services')))

    return result

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
            ((not local_node) and (not local_connection)
             and (node_name == instance_type))
        )
        and
        ((not env_node_name) or (env_node_name == node_name))
    )

    return valid
