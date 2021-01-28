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

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import (
    is_str, to_bool, to_default_int
)


def prepare_node_dependencies(node_names, prepared_node_dict):
  result = dict()
  error_msgs = list()

  try:
    for node_name in (node_names or []):
      error_msgs_node = []

      try:
        node_dependencies = dict()
        prepared_node = prepared_node_dict.get(node_name)
        dependencies = prepared_node.get('dependencies')
        local = to_bool(prepared_node.get('local'))
        origin_hosts_amount = prepared_node.get('amount') or 1
        active_hosts_amount = len(prepared_node.get('active_hosts') or [])
        active_hosts_amount = active_hosts_amount if (not local) else (
            active_hosts_amount
            if (active_hosts_amount > 0)
            else 1
        )

        if dependencies:
          for dependency_name in sorted(list(dependencies.keys())):
            dependency = dependencies.get(dependency_name)
            target_local = False
            error_msgs_dependency = []

            if is_str(dependency) or isinstance(dependency, list):
              dependency = dict(
                  type='url',
                  host=dependency,
              )

            dependency_type = dependency.get('type')

            allowed_props_map = dict(
                node=[
                    'type',
                    'required_amount',
                    'node_ip_type',
                    'limit',
                    'host',
                    'protocol',
                    'port',
                ],
                ip=[
                    'type',
                    'required_amount',
                    'limit',
                    'host',
                    'protocol',
                    'port',
                ],
                url=[
                    'type',
                    'required_amount',
                    'limit',
                    'host',
                    'protocol',
                    'port',
                ],
            )

            allowed_props = allowed_props_map.get(dependency_type)

            for key in sorted(list(dependency.keys())):
              if key not in allowed_props:
                error_msgs_dependency += [[
                    str('property: ' + key),
                    'msg: invalid property for this node dependency type',
                    'allowed properties: ',
                    allowed_props,
                ]]

            required_props = ['type', 'host']

            for key in sorted(required_props):
              if dependency.get(key) is None:
                error_msgs_dependency += [[
                    str('property: ' + key),
                    'msg: required property not specified for this node dependency',
                ]]

            dependency_hosts = dependency.get('host')

            if is_str(dependency_hosts):
              dependency_hosts = [dependency_hosts]

            if dependency_hosts and (dependency_type == 'node'):
              target_node_names = dependency_hosts
              dependency_hosts = []

              for target_node_name in (target_node_names or []):
                target_prepared_node = prepared_node_dict.get(target_node_name)

                if not target_prepared_node:
                  error_msgs_dependency += [[
                      str('target node: ' + str(target_node_name or '')),
                      'msg: invalid target node',
                  ]]
                else:
                  dependency_hosts += target_prepared_node.get(
                      'active_hosts'
                  ) or []
                  target_local = target_prepared_node.get('local')

            if not error_msgs_dependency:
              dependency_limit = dependency.get('limit')
              dependency_limit = int(
                  dependency_limit
                  if (dependency_limit is not None)
                  else 1
              )
              dependency_required_amount = to_default_int(
                  dependency.get('required_amount'), 0
              )
              dependency_real_limit = (
                  len(dependency_hosts)
                  if (dependency_limit == -1)
                  else min(dependency_limit, len(dependency_hosts))
              )

              if dependency_limit < -1:
                error_msgs_dependency += [[
                    str('dependency limit: ' + str(dependency_limit)),
                    'msg: dependency limit should be -1, 0, or a positive integer',
                ]]
              elif (dependency_required_amount != 0) and dependency_limit == 0:
                error_msgs_dependency += [[
                    str(
                        'dependency required amount: '
                        + str(dependency_required_amount)
                    ),
                    'msg: dependency limit is defined as 0, but is required',
                ]]
              elif (dependency_required_amount != 0) and dependency_real_limit == 0:
                error_msgs_dependency += [[
                    str(
                        'dependency required amount: '
                        + str(dependency_required_amount)
                    ),
                    'msg: dependency is required, but number of hosts defined is 0',
                ]]

                if dependency_type == 'node':
                  error_msgs_dependency += [[
                      'tip: take a look at the "amount" property of the target node(s)',
                      'target node(s): ' + str(dependency.get('host') or ''),
                  ]]
              elif (
                  (dependency_required_amount != -1)
                  and
                  (dependency_real_limit < dependency_required_amount)
              ):
                error_msgs_dependency += [[
                    str(
                        'dependency required amount: '
                        + str(dependency_required_amount)
                    ),
                    str(
                        'target host amount: '
                        + str(dependency_real_limit)
                    ),
                    'msg: dependency real limit is less than the required amount',
                ]]

              result_item = dict(
                  type=dependency_type,
                  origin_amount=origin_hosts_amount,
                  required_amount=dependency_required_amount,
                  limit=dependency_real_limit,
                  node_ip_type=dependency.get('node_ip_type'),
                  hosts=dependency_hosts,
                  protocol=dependency.get('protocol'),
                  port=dependency.get('port'),
                  local=target_local,
              )

              result_item_keys = list(result_item.keys())

              for key in result_item_keys:
                if result_item.get(key) is None:
                  result_item.pop(key, None)

              node_dependencies[dependency_name] = result_item

            for value in error_msgs_dependency:
              new_value = [
                  str('dependency name: ' + dependency_name),
                  str('dependency type: ' + dependency_type),
              ] + value
              error_msgs_node += [new_value]

        result[node_name] = dict(
            active_hosts_amount=active_hosts_amount,
            local=local,
            dependencies=node_dependencies,
        )
      except Exception as error:
        error_msgs_node += [[
            'msg: error when trying to prepare the node dependency',
            'error type: ' + str(type(error)),
            'error details: ',
            traceback.format_exc(),
        ]]

      for value in error_msgs_node:
        new_value = [str('node name: ' + (node_name or ''))] + value
        error_msgs += [new_value]

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        'msg: error when trying to prepare the nodes dependencies',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_host_dependencies(node_dependencies, hosts_data, instance_type, instance_index):
  result = dict()
  error_msgs = list()

  try:
    instance_index = int(instance_index)

    for node_name in sorted(list((node_dependencies or {}).keys())):
      error_msgs_node = list()
      node_result = dict()

      try:
        node_dependency_info = node_dependencies.get(node_name)
        local = node_dependency_info.get('local')

        if (instance_type == node_name) or (local and not instance_type):
          single_node_dependencies = node_dependency_info.get('dependencies')

          # host (instance_index) - start
          error_msgs_host = list()
          dependency_result = dict()

          try:
            for dependency_name in sorted(list((single_node_dependencies or {}).keys())):
              error_msgs_dependency = list()

              try:
                node_dependency = single_node_dependencies.get(
                    dependency_name
                )
                dependency_type = node_dependency.get('type')
                dependency_hosts = node_dependency.get('hosts')
                dependency_limit = node_dependency.get('limit')
                required_amount = int(node_dependency.get('required_amount'))
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
                        node_ip_type_prop = (
                            'private_ip'
                            if (node_ip_type == 'private')
                            else node_ip_type
                        )
                        new_dependency_host = dependency_host_data.get(
                            node_ip_type_prop
                        )
                        local_target = to_bool(
                            dependency_host_data.get('local')
                        )

                        if not new_dependency_host:
                          if local_target:
                            new_dependency_host = dependency_host
                          else:
                            error_msgs_dependency += [[
                                str('node_ip_type: ' + str(node_ip_type)),
                                'msg: dependency host has no property for the node ip type',
                            ]]

                        new_dependency_hosts += [new_dependency_host or '']
                      elif required_amount == -1:
                        error_msgs_dependency += [[
                            str('dependency_host: ' + str(dependency_host)),
                            'msg: dependency host not defined',
                        ]]

                    dependency_hosts = new_dependency_hosts

                  hosts_amount = len(dependency_hosts)
                  result_host_idx = 0
                  initial_idx = 0
                  final_idx_next = 0
                  single_host_included = True

                  if hosts_amount > 0:
                    result_host_idx = (instance_index - 1) % hosts_amount

                    initial_idx = min(
                        (result_host_idx * dependency_limit) % hosts_amount,
                        hosts_amount
                    )
                    final_idx_next = min(
                        initial_idx + dependency_limit,
                        hosts_amount
                    )
                    final_idx_next_round = 0

                    if final_idx_next == hosts_amount:
                      final_idx_next_round = min(
                          dependency_limit - (final_idx_next - initial_idx),
                          initial_idx
                      )

                    if initial_idx < final_idx_next:
                      result_hosts = dependency_hosts[initial_idx:final_idx_next]

                    if final_idx_next_round:
                      result_hosts += dependency_hosts[0:final_idx_next_round]

                    if result_hosts:
                      single_host_included = (
                          (initial_idx <= result_host_idx)
                          and
                          (result_host_idx < final_idx_next)
                      ) or (
                          result_host_idx < final_idx_next_round
                      )

                  real_hosts_amount = len(result_hosts)

                  if required_amount == -1:
                    if real_hosts_amount < dependency_limit:
                      error_msgs_dependency += [[
                          str('required amount: ' + str(required_amount)),
                          str('amount found: ' + str(real_hosts_amount)),
                          str('amount expected: ' + str(dependency_limit)),
                          'msg: required amount is defined to require all hosts',
                          str('initial_idx: ' + str(initial_idx)),
                          str('final_idx_next: ' + str(final_idx_next)),
                          result_hosts,
                      ]]
                  elif required_amount > 0:
                    if real_hosts_amount < required_amount:
                      error_msgs_dependency += [[
                          str('required amount: ' + str(required_amount)),
                          str('amount found: ' + str(real_hosts_amount)),
                          'msg: the number of hosts is less than the required amount',
                      ]]

                  result_hosts_aux = result_hosts
                  result_hosts = []

                  for host_aux in result_hosts_aux:
                    host_aux = fill_host(host_aux, protocol, port)
                    result_hosts += [host_aux]

                  if result_hosts:
                    result_host = dependency_hosts[result_host_idx]
                    result_host = fill_host(result_host, protocol, port)

                  if required_amount == -1:
                    required_amount = real_hosts_amount

                  dependency_result[dependency_name] = dict(
                      original_type=dependency_type,
                      host=result_host,
                      host_list=result_hosts,
                      single_host_included=single_host_included,
                      required_amount=required_amount,
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

            node_result = dependency_result
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

          # host (instance_index) - end

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


def fill_host(host, protocol, port):
  if host:
    if protocol:
      host = protocol + "://" + host

    if port:
      host += ":" + port

  return host
