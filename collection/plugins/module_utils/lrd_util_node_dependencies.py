#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=import-error
# pylint: disable=broad-except

from __future__ import absolute_import, division, print_function
__metaclass__ = type  # pylint: disable=invalid-name

import traceback

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import to_bool


def prepare_host_dependencies(node_dependencies, hosts_data):
  result = dict()
  error_msgs = list()

  try:
    for node_name in sorted(list((node_dependencies or {}).keys())):
      error_msgs_node = list()
      node_result = list()

      try:
        node_dependency_info = node_dependencies.get(node_name)
        active_hosts_amount = int(
            node_dependency_info.get('active_hosts_amount')
        )
        single_node_dependencies = node_dependency_info.get('dependencies')

        for instance_index in range(1, active_hosts_amount + 1):
          error_msgs_host = list()
          dependency_result = dict()

          try:
            for dependency_name in sorted(list((single_node_dependencies or {}).keys())):
              error_msgs_dependency = list()

              try:
                node_dependency = single_node_dependencies.get(dependency_name)
                dependency_type = node_dependency.get('type')
                dependency_hosts = node_dependency.get('hosts')
                dependency_limit = node_dependency.get('limit')
                required_amount = int(node_dependency.get('required'))
                protocol = node_dependency.get('protocol')
                port = node_dependency.get('port')
                port = str(port) if (port is not None) else None

                result_host = None
                result_hosts = list()
                real_hosts_amount = 0

                if dependency_limit != 0:
                  if dependency_type == 'node':
                    node_ip_type = node_dependency.get(
                        'node_ip_type') or 'private'

                    new_dependency_hosts = []

                    for dependency_host in dependency_hosts:
                      dependency_host_data = hosts_data.get(dependency_host)

                      if dependency_host_data:
                        new_dependency_host = dependency_host_data.get(
                            node_ip_type
                        )
                        local_target = to_bool(
                            dependency_host_data.get('local'))
                        new_dependency_hosts += [new_dependency_host or '']

                        if (not local_target) and (not new_dependency_host):
                          error_msgs_dependency += [[
                              str('node_ip_type: ' + str(node_ip_type)),
                              'msg: dependency host has no property for the node ip type',
                          ]]
                      elif required_amount == -1:
                        error_msgs_dependency += [[
                            str('dependency_host: ' + str(dependency_host)),
                            'msg: dependency host not defined',
                        ]]

                    dependency_hosts = new_dependency_hosts

                  hosts_amount = len(dependency_hosts)
                  result_host_idx = 0
                  initial_idx = 0

                  if hosts_amount > 0:
                    result_host_idx = (instance_index - 1) % hosts_amount

                    half_limit = int(dependency_limit % 2)
                    initial_idx = max(result_host_idx - half_limit, 0)
                    final_idx_next = min(
                        initial_idx + dependency_limit, hosts_amount
                    )
                    result_hosts = (
                        dependency_hosts[initial_idx:final_idx_next] or []
                    )

                    real_hosts_amount = final_idx_next - initial_idx

                  if required_amount == -1:
                    if real_hosts_amount < dependency_limit:
                      error_msgs_dependency += [[
                          str('required amount: ' + str(required_amount)),
                          str('amount found: ' + str(real_hosts_amount)),
                          str('amount expected: ' + str(dependency_limit)),
                          'msg: required amount is defined to require all hosts',
                      ]]
                  elif required_amount > 0:
                    if real_hosts_amount < required_amount:
                      error_msgs_dependency += [[
                          str('required amount: ' + str(required_amount)),
                          str('amount found: ' + str(real_hosts_amount)),
                          'msg: the number of hosts is less than the required amount',
                      ]]

                  if dependency_type in ['node', 'ip']:
                    result_hosts_aux = result_hosts
                    result_hosts = []

                    for host_aux in result_hosts_aux:
                      if host_aux:
                        if protocol:
                          host_aux = protocol + "://" + host_aux

                        if port:
                          host_aux += ":" + port

                      result_hosts += [host_aux]

                  if result_hosts:
                    result_host = dependency_hosts[result_host_idx - initial_idx]

                  dependency_result[dependency_name] = dict(
                      type=dependency_type,
                      host=result_host,
                      host_list=result_hosts,
                  )
              except Exception as error:
                error_msgs_dependency += [[
                    'msg: error when trying to prepare the host dependency data',
                    'error type: ' + str(type(error)),
                    'error details: ',
                    traceback.format_exc(),
                ]]

              for value in error_msgs_dependency:
                new_value = [
                    str('dependency name: ' + (dependency_name or ''))
                ] + value
                error_msgs_host += [new_value]

            node_result += [dependency_result]
          except Exception as error:
            error_msgs_host += [[
                'msg: error when trying to prepare the host dependencies data',
                'error type: ' + str(type(error)),
                'error details: ',
                traceback.format_exc(),
            ]]

          for value in error_msgs_host:
            new_value = [
                str('instance index (host): ' + str(instance_index or ''))
            ] + value
            error_msgs_node += [new_value]

          if error_msgs_host:
            break

        result[node_name] = node_result
      except Exception as error:
        error_msgs_node += [[
            'msg: error when trying to prepare the node dependency data',
            'error type: ' + str(type(error)),
            'error details: ',
            traceback.format_exc(),
        ]]

      for value in error_msgs_node:
        new_value = [
            str('node name: ' + (node_name or ''))
        ] + value
        error_msgs += [new_value]

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        'msg: error when trying to prepare the nodes dependencies data',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)
