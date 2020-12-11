#!/usr/bin/python

# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

class FilterModule(object):
  def filters(self):
    return {'validate_connection': self.validate_connection}

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
            ((not local_node) and (not local_connection) and (node_name == instance_type))
        )
        and
        ((not env_node_name) or (env_node_name == node_name))
    )

    return valid
