#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=import-error
# pylint: disable=too-many-lines

from __future__ import absolute_import, division, print_function
__metaclass__ = type # pylint: disable=invalid-name

import os

from ansible.module_utils.lrd_utils import merge_dicts, load_yaml_file, default, is_empty, to_bool
from ansible.module_utils.lrd_util_params_mixer import mix
from ansible.module_utils.lrd_util_schema import validate

schema_dict = dict()

def load_schema(schema_file):
  if schema_file in schema_dict:
    return schema_dict.get(schema_file)

  schema = load_yaml_file(schema_file)
  schema_dict[schema_file] = schema

  return schema

def prepare_service(service_info, service_names, env_data, validate_ctx, top):
  result = dict()
  error_msgs = []
  env = env_data.get('env')

  service_info_dict = service_info if isinstance(service_info, dict) else dict()

  service_name = default(service_info_dict.get('name'), service_info)
  service_key = default(service_info_dict.get('key'), service_name)
  service_description = (
      (service_name + ' (' + service_key + ')')
      if service_name != service_key
      else service_name
  )

  if not service_name:
    error_msgs += [['msg: service name not specified']]
    return dict(result=result, error_msgs=error_msgs)

  if service_name in service_names:
    error_msgs += [[
        'service_name: ' + service_name,
        'msg: duplicate service name',
    ]]
    return dict(result=result, error_msgs=error_msgs)
  else:
    service_names.add(service_name)

  result['name'] = service_name
  result['key'] = service_key
  result['description'] = service_description

  services_dict = env.get('services')

  if service_key not in services_dict:
    error_msgs += [[
        'service: ' + service_description,
        'msg: no service specified for the environment',
        'existing_keys:',
        sorted(list(services_dict.keys())),
    ]]
  else:
    service = services_dict.get(service_key)

    result_aux_info = dict()
    error_msgs_aux = []

    is_list = service.get('list')

    absent = to_bool(service_info_dict.get('absent'))
    result['absent'] = absent
    service_info_dict.pop('absent', None)

    if top:
      result['tmp'] = to_bool(service_info_dict.get('tmp'))
      service_info_dict.pop('tmp', None)
      result['can_destroy'] = to_bool(service_info_dict.get('can_destroy'))
      service_info_dict.pop('can_destroy', None)

    if is_list:
      allowed_keys = [
          'name',
          'key',
          'single',
          'absent',
      ]

      for key in sorted(list(service_info_dict.keys())):
        if key not in allowed_keys:
          error_msgs_aux += [[
              'property: ' + key,
              'msg: invalid service info property for a service list',
              'allowed properties:',
              sorted(list(allowed_keys)),
          ]]

      allowed_keys = [
          'list',
          'services',
      ]

      for key in sorted(list(service.keys())):
        if key not in allowed_keys:
          error_msgs_aux += [[
              'property: ' + key,
              'msg: invalid service property for a service list',
              'allowed properties:',
              sorted(list(allowed_keys)),
          ]]
    else:
      allowed_keys = [
          'name',
          'key',
          'single',
          'absent',
          'params',
          'group_params',
          'shared_params',
          'shared_group_params',
      ]

      for key in sorted(list(service_info_dict.keys())):
        if key not in allowed_keys:
          error_msgs_aux += [[
              'property: ' + key,
              'msg: invalid service info property for a non-list service',
              'allowed properties:',
              sorted(list(allowed_keys)),
          ]]

      allowed_keys = [
          'list',
          'base_dir',
          'task',
          'namespace',
          'credentials',
          'credentials_schema',
          'params_schema',
          'params',
          'group_params',
          'shared_params',
          'shared_group_params',
      ]

      for key in sorted(list(service.keys())):
        if key not in allowed_keys:
          error_msgs_aux += [[
              'property: ' + key,
              'msg: invalid service property for a non-list service',
              'allowed properties:',
              sorted(list(allowed_keys)),
          ]]

    for value in (error_msgs_aux or []):
      new_value = ['service: ' + service_description] + value
      error_msgs += [new_value]

    error_msgs_aux = []

    if not is_list:
      task = service.get('task')
      result['task'] = task
      result['namespace'] = service.get('namespace')

      base_dir_prefix = service.get('base_dir') + '/' if service.get('base_dir') else ''
      result['base_dir'] = service.get('base_dir')
      result['base_dir_prefix'] = base_dir_prefix

      if not task:
        error_msgs_aux += [[
            'property: task',
            'msg: property not defined',
        ]]

      if validate_ctx:
        task_file = base_dir_prefix + task

        if not os.path.exists(task_file):
          error_msgs_aux += [['task file not found: ' + task_file]]

      params_args = dict(
          group_params=service.get('credentials'),
          group_params_dict=env.get('credentials'),
      )

      service_params_info = mix(params_args)

      result_aux_credentials = service_params_info.get('result')
      error_msgs_aux_credentials = service_params_info.get('error_msgs')

      for value in (error_msgs_aux_credentials or []):
        new_value = ['context: service credentials'] + value
        error_msgs_aux += [new_value]

      if not error_msgs_aux_credentials:
        credentials = result_aux_credentials
        result['credentials'] = credentials

        if validate_ctx:
          schema_file = service.get('credentials_schema')

          if schema_file:
            schema_file = base_dir_prefix + schema_file

            if os.path.exists(schema_file):
              schema = load_schema(schema_file)
              error_msgs_aux_validate = validate(schema, credentials)

              for value in (error_msgs_aux_validate or []):
                new_value = ['context: validate service credentials'] + value
                error_msgs_aux += [new_value]
            else:
              error_msgs_aux += [[
                  'context: validate service credentials',
                  'msg: credentials schema file not found: ' + schema_file,
              ]]

      error_msgs_aux_params = []

      if isinstance(service_info, dict):
        params_args = dict(
            params=service_info_dict.get('params'),
            group_params=service_info_dict.get('group_params'),
            shared_params=service_info_dict.get('shared_params'),
            shared_group_params=service_info_dict.get('shared_group_params'),
            shared_group_params_dict=env.get('service_shared_group_params'),
            shared_params_dict=env.get('service_shared_params'),
            group_params_dict=env.get('service_group_params'),
        )

        service_params_info = mix(params_args)

        result_aux_info = service_params_info.get('result')
        error_msgs_aux_info = service_params_info.get('error_msgs')

        for value in (error_msgs_aux_info or []):
          new_value = ['context: service info params'] + value
          error_msgs_aux_params += [new_value]

      params_args = dict(
          params=service.get('params'),
          group_params=service.get('group_params'),
          shared_params=service.get('shared_params'),
          shared_group_params=service.get('shared_group_params'),
          shared_group_params_dict=env.get('service_shared_group_params'),
          shared_params_dict=env.get('service_shared_params'),
          group_params_dict=env.get('service_group_params'),
      )

      service_params_info = mix(params_args)

      result_aux_service = service_params_info.get('result')
      error_msgs_aux_service = service_params_info.get('error_msgs')

      for value in (error_msgs_aux_service or []):
        new_value = ['context: service params'] + value
        error_msgs_aux_params += [new_value]

      error_msgs_aux += error_msgs_aux_params

      if not error_msgs_aux_params:
        service_params = merge_dicts(result_aux_service, result_aux_info)
        result['params'] = service_params

        if validate_ctx:
          schema_file = service.get('params_schema')

          if schema_file:
            schema_file = base_dir_prefix + schema_file

            if os.path.exists(schema_file):
              schema = load_schema(schema_file)
              error_msgs_aux_validate = validate(schema, service_params)

              for value in (error_msgs_aux_validate or []):
                new_value = ['context: validate service params'] + value
                error_msgs_aux += [new_value]
            else:
              error_msgs_aux += [[
                  'context: validate service params',
                  'msg: params schema file not found: ' + schema_file,
              ]]

      for value in (error_msgs_aux or []):
        new_value = ['service: ' + service_description] + value
        error_msgs += [new_value]
    else:
      single = service_info_dict.get('single')

      if single:
        error_msgs_aux += [[
            'msg: service should not be a list (single)',
        ]]

      for value in (error_msgs_aux or []):
        new_value = ['service: ' + service_description] + value
        error_msgs += [new_value]

      services = service.get('services')

      if services:
        if absent:
          for idx, service_info_aux in enumerate(services):
            if isinstance(service_info_aux, dict):
              service_info_aux['absent'] = True
            else:
              services[idx] = dict(name=service_info_aux, absent=True)

        info_children = prepare_services(
            services, env_data, validate_ctx, top=False, service_names=service_names)

        result_children = info_children.get('result')
        error_msgs_children = info_children.get('error_msgs')

        for value in (error_msgs_children or []):
          new_value = ['service (parent): ' + service_description] + value
          error_msgs += [new_value]

        if not error_msgs_children:
          result['is_list'] = True
          result['services'] = result_children

  return dict(result=result, error_msgs=error_msgs)

def prepare_services(services, env_data, validate_ctx, top=False, service_names=None):
  result = []
  error_msgs = []
  service_names = service_names if service_names is not None else set()
  env = env_data.get('env')

  if services:
    services_dict = env.get('services')

    if not services_dict:
      error_msgs += [['msg: no service specified for the environment']]
    else:
      for service_info in services:
        info = prepare_service(service_info, service_names, env_data, validate_ctx, top)

        result_aux = info.get('result')
        error_msgs_aux = info.get('error_msgs')

        if error_msgs_aux:
          error_msgs += error_msgs_aux
        else:
          service = result_aux
          is_list = service.get('is_list')

          if is_list:
            services_children = service.get('services')
            result += (services_children or [])
          else:
            result += [service]

  return dict(result=result, error_msgs=error_msgs)

def prepare_pod(pod_info, pod_ctx_info_dict, env_data, validate_ctx):
  result = dict()
  error_msgs = []
  env = env_data.get('env')
  ctx_dir = env_data.get('ctx_dir')

  pod_info_dict = pod_info if isinstance(pod_info, dict) else dict()

  pod_name = default(pod_info_dict.get('name'), pod_info)
  pod_key = default(pod_info_dict.get('key'), pod_name)
  pod_description = (pod_name + ' (' + pod_key + ')') if pod_name != pod_key else pod_name

  if not pod_name:
    error_msgs += [['msg: pod name not specified']]
    return dict(result=result, error_msgs=error_msgs)

  result['name'] = pod_name
  result['key'] = pod_key
  result['description'] = pod_description

  pods_dict = env.get('pods')

  if pod_key not in pods_dict:
    error_msgs += [[
        'pod: ' + pod_description,
        'existing_keys:',
        sorted(list(pods_dict.keys())),
        'msg: no pod specified for the environment'
    ]]
  else:
    pod = pods_dict.get(pod_key)
    error_msgs_aux = []

    repo = pod.get('repo')
    result['repo'] = repo
    env_repos = pod.get('env_repos')
    result['env_repos'] = env_repos


    repos = env.get('repos')

    if not repos:
      error_msgs += [['msg: no repositories in the environment dictionary']]
    elif not repos.get(repo):
      error_msgs_aux += [[
          'context: validate pod repo',
          'msg: repository not found: ' + repo,
      ]]

    for env_repo in (env_repos or []):
      if not repos.get(env_repo.get('repo')):
        error_msgs_aux += [[
            'context: validate pod env repo',
            'msg: repository not found: ' + env_repo.get('repo'),
        ]]

    result['env_files'] = pod.get('env_files')
    result['env_templates'] = pod.get('env_templates')
    result['base_dir'] = pod.get('base_dir')
    result['data_dir'] = pod.get('data_dir')
    result['tmp_dir'] = pod.get('tmp_dir')
    result['ctx'] = pod.get('ctx')
    result['root'] = to_bool(pod.get('root'))
    result['flat'] = to_bool(pod.get('flat'))
    result['fast_prepare'] = to_bool(pod.get('fast_prepare'))
    result['skip_unchanged'] = to_bool(pod.get('skip_unchanged'))

    local_dir = ctx_dir + '/pods/' + pod_name

    dev = env_data.get('dev')
    path_maps = env_data.get('path_map') or dict()
    dev_repo_path = path_maps.get(repo)

    if dev and dev_repo_path:
      local_dir = env_data.get('dev_repos_dir') + '/' + dev_repo_path

    result['local_dir'] = local_dir

    base_dir_prefix = local_dir + '/'
    pod_ctx_info = (pod_ctx_info_dict or dict()).get(pod_name)
    result_aux_ctx_info = dict()
    result_aux_info = dict()

    if validate_ctx:
      pod_ctx_file = pod.get('ctx')

      if pod_ctx_file:
        pod_ctx_file_full = base_dir_prefix + pod_ctx_file

        if not os.path.exists(pod_ctx_file_full):
          error_msgs_aux += [['pod ctx file not found: ' + pod_ctx_file]]

    params_args = dict(
        group_params=pod.get('credentials'),
        group_params_dict=env.get('credentials'),
    )

    pod_params_info = mix(params_args)

    result_aux_credentials = pod_params_info.get('result')
    error_msgs_aux_credentials = pod_params_info.get('error_msgs')

    for value in (error_msgs_aux_credentials or []):
      new_value = ['context: pod credentials'] + value
      error_msgs_aux += [new_value]

    if not error_msgs_aux_credentials:
      credentials = result_aux_credentials
      result['credentials'] = credentials

      if validate_ctx:
        schema_file = pod.get('credentials_schema')

        if schema_file:
          schema_file_full = base_dir_prefix + schema_file

          if os.path.exists(schema_file_full):
            schema = load_schema(schema_file_full)
            error_msgs_aux_validate = validate(schema, credentials)

            for value in (error_msgs_aux_validate or []):
              new_value = ['context: validate pod credentials'] + value
              error_msgs_aux += [new_value]
          else:
            error_msgs_aux += [[
                'context: validate pod credentials',
                'msg: credentials schema file not found: ' + schema_file,
            ]]

    error_msgs_aux_params = []

    if pod_ctx_info:
      params_args = dict(
          params=pod_ctx_info.get('params'),
          group_params=pod_ctx_info.get('group_params'),
          shared_params=pod_ctx_info.get('shared_params'),
          shared_group_params=pod_ctx_info.get('shared_group_params'),
          shared_group_params_dict=env.get('pod_shared_group_params'),
          shared_params_dict=env.get('pod_shared_params'),
          group_params_dict=env.get('pod_group_params'),
      )

      pod_params_info = mix(params_args)

      result_aux_ctx_info = pod_params_info.get('result')
      error_msgs_aux_ctx_info = pod_params_info.get('error_msgs')

      for value in (error_msgs_aux_ctx_info or []):
        new_value = ['context: pod ctx info params'] + value
        error_msgs_aux_params += [new_value]

    if isinstance(pod_info, dict):
      params_args = dict(
          params=pod_info.get('params'),
          group_params=pod_info.get('group_params'),
          shared_params=pod_info.get('shared_params'),
          shared_group_params=pod_info.get('shared_group_params'),
          shared_group_params_dict=env.get('pod_shared_group_params'),
          shared_params_dict=env.get('pod_shared_params'),
          group_params_dict=env.get('pod_group_params'),
      )

      pod_params_info = mix(params_args)

      result_aux_info = pod_params_info.get('result')
      error_msgs_aux_info = pod_params_info.get('error_msgs')

      for value in (error_msgs_aux_info or []):
        new_value = ['context: pod info params'] + value
        error_msgs_aux_params += [new_value]

    params_args = dict(
        params=pod.get('params'),
        group_params=pod.get('group_params'),
        shared_params=pod.get('shared_params'),
        shared_group_params=pod.get('shared_group_params'),
        shared_group_params_dict=env.get('pod_shared_group_params'),
        shared_params_dict=env.get('pod_shared_params'),
        group_params_dict=env.get('pod_group_params'),
    )

    pod_params_info = mix(params_args)

    result_aux_pod = pod_params_info.get('result')
    error_msgs_aux_pod = pod_params_info.get('error_msgs')

    for value in (error_msgs_aux_pod or []):
      new_value = ['context: pod params'] + value
      error_msgs_aux_params += [new_value]

    error_msgs_aux += error_msgs_aux_params

    if not error_msgs_aux_params:
      pod_params = merge_dicts(result_aux_pod, result_aux_info, result_aux_ctx_info)
      result['params'] = pod_params

      if validate_ctx:
        schema_file = pod.get('params_schema')

        if schema_file:
          schema_file_full = base_dir_prefix + schema_file

          if os.path.exists(schema_file_full):
            schema = load_schema(schema_file_full)
            error_msgs_aux_validate = validate(schema, pod_params)

            for value in (error_msgs_aux_validate or []):
              new_value = ['context: validate pod params'] + value
              error_msgs_aux += [new_value]
          else:
            error_msgs_aux += [[
                'context: validate pod params',
                'msg: params schema file not found: ' + schema_file,
            ]]

    for value in (error_msgs_aux or []):
      new_value = ['pod: ' + pod_description] + value
      error_msgs += [new_value]

  return dict(result=result, error_msgs=error_msgs)

def prepare_pods(pods, pod_ctx_info_dict, env_data, validate_ctx):
  result = []
  error_msgs = []
  pod_names = set()
  env = env_data.get('env')

  if pods:
    pods_dict = env.get('pods')

    if not pods_dict:
      error_msgs += [['msg: no pod specified for the environment']]
    else:
      for pod_info in pods:
        info = prepare_pod(pod_info, pod_ctx_info_dict, env_data, validate_ctx)

        result_aux = info.get('result')
        error_msgs_aux = info.get('error_msgs')

        if error_msgs_aux:
          error_msgs += error_msgs_aux
        else:
          pod_name = result_aux.get('name')

          if pod_name in pod_names:
            error_msgs += [[
                'pod_name: ' + pod_name,
                'msg: duplicate pod name',
            ]]
          else:
            pod_names.add(pod_name)
            result += [result_aux]

  return dict(result=result, error_msgs=error_msgs)

def prepare_node(node_info, env_data, validate_ctx):
  result = dict()
  error_msgs = []
  env = env_data.get('env')

  node_info_dict = node_info if isinstance(node_info, dict) else dict()

  node_name = default(node_info_dict.get('name'), node_info)
  node_key = default(node_info_dict.get('key'), node_name)
  node_description = (node_name + ' (' + node_key + ')') if node_name != node_key else node_name

  if not node_name:
    error_msgs += [['msg: node name not specified']]
    return dict(result=result, error_msgs=error_msgs)

  result['name'] = node_name
  result['key'] = node_key
  result['description'] = node_description

  nodes_dict = env.get('nodes')

  if node_key not in nodes_dict:
    error_msgs += [[
        'node: ' + node_description,
        'existing_keys:',
        sorted(list(nodes_dict.keys())),
        'msg: no node specified for the environment'
    ]]
  else:
    node = nodes_dict.get(node_key)

    result['tmp'] = to_bool(node_info_dict.get('tmp'))
    node_info_dict.pop('tmp', None)
    result['can_destroy'] = to_bool(node_info_dict.get('can_destroy'))
    node_info_dict.pop('can_destroy', None)

    result['absent'] = to_bool(node_info_dict.get('absent'))
    local = to_bool(node_info_dict.get('local'))
    result['local'] = local
    external = to_bool(node_info_dict.get('external'))
    result['external'] = external

    result['local_host_test'] = to_bool(node_info_dict.get('local_host_test'))
    result['local_host_test_error'] = node_info_dict.get('local_host_test_error')

    result_aux_info = dict()
    error_msgs_aux = []

    if (not local) and (not external):
      required_props = [
          'service',
          'base_dir',
          'credential',
      ]

      for key in required_props:
        if is_empty(node.get(key)):
          error_msgs += [[
              'node: ' + node_description,
              'property: ' + key,
              'msg: required property not found in node or is empty (non-local and non-external)'
          ]]

    if local and not env_data.get('dev'):
      error_msgs += [[
          'node: ' + node_description,
          'msg: local node should be defined only in development environments'
      ]]

    credential = node.get('credential')

    if credential:
      params_args = dict(
          group_params=dict(credential=credential),
          group_params_dict=env.get('credentials'),
      )

      node_params_info = mix(params_args)

      result_aux_credential = node_params_info.get('result')
      error_msgs_aux_credential = node_params_info.get('error_msgs')

      for value in (error_msgs_aux_credential or []):
        new_value = ['context: node credential'] + value
        error_msgs_aux += [new_value]

      if not error_msgs_aux_credential:
        credential = result_aux_credential.get('credential')
        result['credential'] = credential

        if validate_ctx:
          schema_file = 'schemas/node_credential.schema.yml'

          if os.path.exists(schema_file):
            schema = load_schema(schema_file)
            error_msgs_aux_validate = validate(schema, credential)

            for value in (error_msgs_aux_validate or []):
              new_value = ['context: validate node credentials'] + value
              error_msgs_aux += [new_value]
          else:
            error_msgs_aux += [[
                'context: validate node credentials',
                'msg: credentials schema file not found: ' + schema_file,
            ]]

    error_msgs_aux_params = []

    if isinstance(node_info, dict):
      params_args = dict(
          params=node_info_dict.get('params'),
          group_params=node_info_dict.get('group_params'),
          shared_params=node_info_dict.get('shared_params'),
          shared_group_params=node_info_dict.get('shared_group_params'),
          shared_group_params_dict=env.get('node_shared_group_params'),
          shared_params_dict=env.get('node_shared_params'),
          group_params_dict=env.get('node_group_params'),
      )

      node_params_info = mix(params_args)

      result_aux_info = node_params_info.get('result')
      error_msgs_aux_info = node_params_info.get('error_msgs')

      for value in (error_msgs_aux_info or []):
        new_value = ['context: node info params'] + value
        error_msgs_aux_params += [new_value]

    params_args = dict(
        params=node.get('params'),
        group_params=node.get('group_params'),
        shared_params=node.get('shared_params'),
        shared_group_params=node.get('shared_group_params'),
        shared_group_params_dict=env.get('node_shared_group_params'),
        shared_params_dict=env.get('node_shared_params'),
        group_params_dict=env.get('node_group_params'),
    )

    node_params_info = mix(params_args)

    result_aux_node = node_params_info.get('result')
    error_msgs_aux_node = node_params_info.get('error_msgs')

    for value in (error_msgs_aux_node or []):
      new_value = ['context: node params'] + value
      error_msgs_aux_params += [new_value]

    error_msgs_aux += error_msgs_aux_params

    if not error_msgs_aux_params:
      node_params = merge_dicts(result_aux_node, result_aux_info)
      result['params'] = node_params

      if validate_ctx:
        schema_file = 'schemas/node_params.schema.yml'
        error_msgs_aux_validate = []

        if os.path.exists(schema_file):
          schema = load_schema(schema_file)
          error_msgs_aux_validate = validate(schema, node_params)

          for value in (error_msgs_aux_validate or []):
            new_value = ['context: validate node params'] + value
            error_msgs_aux += [new_value]
        else:
          error_msgs_aux += [[
              'context: validate node params',
              'msg: params schema file not found: ' + schema_file,
          ]]

        if (not error_msgs_aux_validate) and (not local):
          required_props = ['host_test']

          for key in required_props:
            if is_empty(node_params.get(key)):
              error_msgs += [[
                  'node: ' + node_description,
                  'property: ' + key,
                  'context: validate node params (custom)',
                  'msg: required property not found in node params or is empty (non-local)'
              ]]

    service = node.get('service')
    dns_service = node.get('dns_service')
    dns_service_params_list = node_params.get('dns_service_params_list')

    if not service:
      if dns_service:
        error_msgs += [[
            'node: ' + node_description,
            'context: validate node (custom)',
            'msg: dns_service is defined, but service is undefined'
        ]]

      if dns_service_params_list:
        error_msgs += [[
            'node: ' + node_description,
            'context: validate node (custom)',
            'msg: dns_service_params_list is defined, but service is undefined'
        ]]
    else:
      instance_amount = int(node_info_dict.get('amount') or 1)
      instance_max_amount = int(node_info_dict.get('max_amount') or instance_amount)
      services_info = []

      for idx in range(1, instance_max_amount + 1):
        name_suffix = ('-' + str(idx)) if idx > 1 else ''
        service_info = dict(
            name=service + name_suffix,
            key=service,
            single=True,
            params=dict(
                name=(node_info_dict.get('hostname') or node_name) + name_suffix,
                state=None if idx <= instance_amount else 'absent',
            )
        )
        services_info += [service_info]

      if services_info:
        result['prepared_services'] = services_info.copy()

        if validate_ctx:
          service_result_info = prepare_services(services_info, env_data, validate_ctx, True)

          error_msgs_aux_service = service_result_info.get('error_msgs')

          for value in (error_msgs_aux_service or []):
            new_value = ['context: node service'] + value
            error_msgs_aux += [new_value]

      if not dns_service:
        if dns_service_params_list:
          error_msgs += [[
              'node: ' + node_description,
              'context: validate node (custom)',
              'msg: dns_service_params_list is defined, but dns_service is undefined'
          ]]
      elif instance_amount > 1:
        error_msgs += [[
            'node: ' + node_description,
            'msg: dns service defined for node with more than 1 replica'
        ]]
      elif not dns_service_params_list:
        error_msgs += [[
            'node: ' + node_description,
            'msg: dns service defined for node with dns_service_params_list undefined or empty'
        ]]
      else:
        services_info = []

        for idx, dns_service_params in enumerate(dns_service_params_list, start=1):
          for dns_type_name in ['ipv4', 'ipv6']:
            name_suffix = '-' + dns_type_name + (('-' + str(idx)) if idx > 1 else '')
            service_info = dict(
                name=dns_service + name_suffix,
                key=dns_service,
                params=dict(
                    record=dns_service_params.get('record'),
                    ttl=dns_service_params.get('ttl'),
                    dns_type='A' if dns_type_name == 'ipv4' else 'AAAA',
                )
            )
            services_info += [service_info]

        if services_info:
          result['prepared_dns_services'] = services_info.copy()

          if validate_ctx:
            service_result_info = prepare_services(services_info, env_data, validate_ctx, True)
            error_msgs_aux_service = service_result_info.get('error_msgs')

            for value in (error_msgs_aux_service or []):
              new_value = ['context: node dns service'] + value
              error_msgs_aux += [new_value]

    pods = node.get('pods')
    pod_ctx_info_dict = node_info_dict.get('pods')

    if pods:
      pods_info = prepare_pods(pods, pod_ctx_info_dict, env_data, validate_ctx)

      result_aux_pods = pods_info.get('result')
      error_msgs_aux_pods = pods_info.get('error_msgs')

      if error_msgs_aux_pods:
        error_msgs_aux += error_msgs_aux_pods
      else:
        result['pods'] = result_aux_pods

    for value in (error_msgs_aux or []):
      new_value = ['node: ' + node_description] + value
      error_msgs += [new_value]

  return dict(result=result, error_msgs=error_msgs)

def prepare_nodes(nodes, env_data, validate_ctx):
  result = []
  error_msgs = []
  node_names = set()
  env = env_data.get('env')

  if nodes:
    nodes_dict = env.get('nodes')

    if not nodes_dict:
      error_msgs += [['msg: no node specified for the environment']]
    else:
      for node_info in nodes:
        info = prepare_node(node_info, env_data, validate_ctx)

        result_aux = info.get('result')
        error_msgs_aux = info.get('error_msgs')

        if error_msgs_aux:
          error_msgs += error_msgs_aux
        else:
          node_name = result_aux.get('name')

          if node_name in node_names:
            error_msgs += [[
                'node_name: ' + node_name,
                'msg: duplicate node name',
            ]]
          else:
            node_names.add(node_name)
            result += [result_aux]

  return dict(result=result, error_msgs=error_msgs)

def prepare_ctx(ctx_name, env_data, validate_ctx):
  result = dict()
  error_msgs = []

  if not env_data:
    error_msgs += [['msg: env_data property not specified']]
    return dict(result=result, error_msgs=error_msgs)

  env = env_data.get('env')

  if not env:
    error_msgs += [['msg: environment dictionary not specified']]
  elif not ctx_name:
    error_msgs += [['msg: context name not specified']]
  else:
    main_dict = env.get('main')

    if not main_dict:
      error_msgs += [['msg: main environment dictionary not specified']]
    elif ctx_name not in main_dict:
      error_msgs += [['msg: context not in the main environment dictionary']]
    else:
      ctx = main_dict.get(ctx_name)
      repo = ctx.get('repo')
      result['repo'] = repo
      env_repos = ctx.get('env_repos')
      result['env_repos'] = env_repos

      repos = env.get('repos')

      if not repos:
        error_msgs += [['msg: no repositories in the environment dictionary']]
      elif not repos.get(repo):
        error_msgs += [[
            'context: validate ctx repo',
            'msg: repository not found: ' + repo,
        ]]

      for env_repo in (env_repos or []):
        if not repos.get(env_repo.get('repo')):
          error_msgs += [[
              'context: validate ctx env repo',
              'msg: repository not found: ' + env_repo.get('repo'),
          ]]

      params_args = dict(
          params=ctx.get('params'),
          group_params=ctx.get('group_params'),
          shared_params=ctx.get('shared_params'),
          shared_group_params=ctx.get('shared_group_params'),
          shared_group_params_dict=env.get('main_shared_group_params'),
          shared_params_dict=env.get('main_shared_params'),
          group_params_dict=env.get('main_group_params'),
      )

      ctx_params_info = mix(params_args)

      result_aux = ctx_params_info.get('result')
      error_msgs_aux = ctx_params_info.get('error_msgs')

      for value in (error_msgs_aux or []):
        new_value = ['context: ctx params'] + value
        error_msgs += [new_value]

      if not error_msgs_aux:
        ctx_params = result_aux
        result['params'] = ctx_params

        if validate_ctx:
          schema_file = 'schemas/ctx_params.schema.yml'

          if os.path.exists(schema_file):
            schema = load_schema(schema_file)
            error_msgs_aux = validate(schema, ctx_params)

            for value in (error_msgs_aux or []):
              new_value = ['context: validate ctx params'] + value
              error_msgs += [new_value]
          else:
            error_msgs_aux += [[
                'context: validate ctx params',
                'msg: params schema file not found: ' + schema_file,
            ]]

      ctx_initial_services = ctx.get('initial_services')

      if ctx_initial_services:
        services_info = prepare_services(ctx_initial_services, env_data, validate_ctx, top=True)

        result_aux = services_info.get('result')
        error_msgs_aux = services_info.get('error_msgs')

        for value in (error_msgs_aux or []):
          new_value = ['service context: initial services'] + value
          error_msgs += [new_value]

        if not error_msgs_aux:
          result['prepared_initial_services'] = result_aux

      ctx_nodes = ctx.get('nodes')

      if ctx_nodes:
        nodes_info = prepare_nodes(ctx_nodes, env_data, validate_ctx)

        result_aux = nodes_info.get('result')
        error_msgs_aux = nodes_info.get('error_msgs')

        if error_msgs_aux:
          error_msgs += error_msgs_aux
        else:
          result['nodes'] = result_aux

      ctx_final_services = ctx.get('final_services')

      if ctx_final_services:
        services_info = prepare_services(ctx_final_services, env_data, validate_ctx, top=True)

        result_aux = services_info.get('result')
        error_msgs_aux = services_info.get('error_msgs')

        for value in (error_msgs_aux or []):
          new_value = ['service context: final services'] + value
          error_msgs += [new_value]

        if not error_msgs_aux:
          result['prepared_final_services'] = result_aux

  return dict(result=result, error_msgs=error_msgs)
