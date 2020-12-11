#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=import-error
# pylint: disable=too-many-lines

from __future__ import absolute_import, division, print_function
__metaclass__ = type  # pylint: disable=invalid-name

import os

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import (
    default, is_empty, load_yaml_file, merge_dicts, to_bool
)
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_params_mixer import mix
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_schema import validate

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

  service_info_dict = service_info if isinstance(
      service_info, dict) else dict()

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

      base_dir_prefix = service.get(
          'base_dir') + '/' if service.get('base_dir') else ''
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

      info = mix(params_args)

      result_aux_credentials = info.get('result')
      error_msgs_aux_credentials = info.get('error_msgs')

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

        info = mix(params_args)

        result_aux_info = info.get('result')
        error_msgs_aux_info = info.get('error_msgs')

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

      info = mix(params_args)

      result_aux_service = info.get('result')
      error_msgs_aux_service = info.get('error_msgs')

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

        info = prepare_services(
            services, env_data, validate_ctx, top=False, service_names=service_names)

        result_children = info.get('result')
        error_msgs_children = info.get('error_msgs')

        for value in (error_msgs_children or []):
          new_value = ['service (parent): ' + service_description] + value
          error_msgs += [new_value]

        if not error_msgs_children:
          result['is_list'] = True
          result['services'] = result_children

  result_keys = list(result.keys())

  for key in result_keys:
    if result.get(key) is None:
      result.pop(key, None)

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
        info = prepare_service(service_info, service_names,
                               env_data, validate_ctx, top)

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


def prepare_pod(pod_info, parent_data):
  result = dict()
  error_msgs = []

  pod_ctx_info_dict = parent_data.get('pod_ctx_info_dict')
  local = parent_data.get('local')
  parent_base_dir = parent_data.get('base_dir')
  env_data = parent_data.get('env_data')
  validate_ctx = parent_data.get('validate_ctx')

  env = env_data.get('env')
  ctx_dir = env_data.get('ctx_dir')

  pod_info_dict = pod_info if isinstance(pod_info, dict) else dict()

  pod_name = default(pod_info_dict.get('name'), pod_info)
  pod_key = default(pod_info_dict.get('key'), pod_name)
  pod_description = (
      pod_name + ' (' + pod_key + ')') if pod_name != pod_key else pod_name

  if not pod_name:
    error_msgs += [['msg: pod name not specified']]
    return dict(result=result, error_msgs=error_msgs)

  result['name'] = pod_name
  result['key'] = pod_key
  result['description'] = pod_description
  result['parent_type'] = parent_data.get('parent_type')
  result['parent_description'] = parent_data.get('parent_description')

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

    pod_identifier = env.get('name') + '-' + \
        env_data.get('ctx_name') + '-' + pod_name
    result['identifier'] = pod_identifier

    local_dir = ctx_dir + '/pods/' + pod_name

    dev = env_data.get('dev')
    path_maps = env_data.get('path_map') or dict()
    dev_repo_path = path_maps.get(repo)

    if dev and dev_repo_path:
      local_dir = env_data.get('dev_repos_dir') + '/' + dev_repo_path

    result['local_dir'] = local_dir

    dev_repos_dir = env_data.get('dev_repos_dir')
    local_base_dir_relpath = os.path.relpath(dev_repos_dir, local_dir)

    dev_extra_repos_dir = env_data.get('dev_extra_repos_dir')
    extra_repos_dir_relpath = os.path.relpath(dev_extra_repos_dir, local_dir)

    flat = pod.get('flat')
    base_dir = pod.get('base_dir') or pod_name
    pod_dir = base_dir if flat else (base_dir + '/main')
    pod_dir = local_dir if local else (parent_base_dir + '/' + pod_dir)
    tmp_dir = (
        (dev_repos_dir + '/tmp/pods/' + pod_identifier)
        if local
        else (
            pod.get('tmp_dir')
            or (
                (parent_base_dir + '/.pods/' + pod_name + '/tmp')
                if flat
                else (parent_base_dir + '/' + base_dir + '/tmp')
            )
        )
    )
    data_dir = (
        (local_base_dir_relpath + '/data/' + pod_identifier)
        if local
        else (
            pod.get('data_dir')
            or (
                (parent_base_dir + '/.pods/' + pod_name + '/data')
                if flat
                else (parent_base_dir + '/' + base_dir + '/data')
            )
        )
    )

    result['env_files'] = pod.get('env_files')
    result['env_templates'] = pod.get('env_templates')
    result['base_dir'] = base_dir
    result['pod_dir'] = pod_dir
    result['tmp_dir'] = tmp_dir
    result['data_dir'] = data_dir
    result['extra_repos_dir_relpath'] = extra_repos_dir_relpath
    result['ctx'] = pod.get('ctx')
    result['local'] = to_bool(local)
    result['root'] = to_bool(pod.get('root'))
    result['flat'] = to_bool(pod.get('flat'))
    result['fast_prepare'] = to_bool(pod.get('fast_prepare'))
    result['skip_unchanged'] = to_bool(pod.get('skip_unchanged'))

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

    info = mix(params_args)

    result_aux_credentials = info.get('result')
    error_msgs_aux_credentials = info.get('error_msgs')

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

      info = mix(params_args)

      result_aux_ctx_info = info.get('result')
      error_msgs_aux_ctx_info = info.get('error_msgs')

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

      info = mix(params_args)

      result_aux_info = info.get('result')
      error_msgs_aux_info = info.get('error_msgs')

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

    info = mix(params_args)

    result_aux_pod = info.get('result')
    error_msgs_aux_pod = info.get('error_msgs')

    for value in (error_msgs_aux_pod or []):
      new_value = ['context: pod params'] + value
      error_msgs_aux_params += [new_value]

    error_msgs_aux += error_msgs_aux_params

    if not error_msgs_aux_params:
      pod_params = merge_dicts(
          result_aux_pod, result_aux_info, result_aux_ctx_info)
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

  result_keys = list(result.keys())

  for key in result_keys:
    if result.get(key) is None:
      result.pop(key, None)

  return dict(result=result, error_msgs=error_msgs)


def prepare_pods(pods, parent_data):
  result = []
  error_msgs = []
  pod_names = set()

  env_data = parent_data.get('env_data')
  env = env_data.get('env')

  if pods:
    pods_dict = env.get('pods')

    if not pods_dict:
      error_msgs += [['msg: no pod specified for the environment']]
    else:
      for pod_info in pods:
        info = prepare_pod(pod_info, parent_data)

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
  node_description = (node_name + ' (' + node_key +
                      ')') if node_name != node_key else node_name

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

    ctx_dir = env_data.get('ctx_dir')

    result_aux_info = dict()
    error_msgs_aux = []

    if not local:
      required_props = ['base_dir']

      for key in required_props:
        if is_empty(node.get(key)):
          error_msgs += [[
              'node: ' + node_description,
              'property: ' + key,
              'msg: required property not found in node or is empty (non-local)'
          ]]

    if (not local) and (not external):
      required_props = [
          'service',
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

    local_dir = ctx_dir + '/nodes/' + node_name
    result['local_dir'] = local_dir

    node_identifier = env.get('name') + '-' + env_data.get('ctx_name')
    result['identifier'] = node_identifier

    dev_repos_dir = env_data.get('dev_repos_dir')

    base_dir = None if local else node.get('base_dir')
    node_dir = local_dir if local else (
        node.get('node_dir') or (base_dir + '/.node'))
    tmp_dir = (
        (dev_repos_dir + '/tmp/nodes/' + node_identifier)
        if local
        else (node.get('tmp_dir') or (base_dir + '/.tmp'))
    )

    result['base_dir'] = base_dir
    result['node_dir'] = node_dir
    result['tmp_dir'] = tmp_dir
    result['local_host_test'] = to_bool(node_info_dict.get('local_host_test'))
    result['local_host_test_error'] = node_info_dict.get(
        'local_host_test_error')

    credential = node.get('credential')

    if credential:
      params_args = dict(
          group_params=dict(credential=credential),
          group_params_dict=env.get('credentials'),
      )

      info = mix(params_args)

      result_aux_credential = info.get('result')
      error_msgs_aux_credential = info.get('error_msgs')

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

      info = mix(params_args)

      result_aux_info = info.get('result')
      error_msgs_aux_info = info.get('error_msgs')

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

    info = mix(params_args)

    result_aux_node = info.get('result')
    error_msgs_aux_node = info.get('error_msgs')

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
      instance_max_amount = int(
          node_info_dict.get('max_amount') or instance_amount)
      services_info = []

      for idx in range(1, instance_max_amount + 1):
        name_suffix = ('-' + str(idx)) if idx > 1 else ''
        service_info = dict(
            name=service + name_suffix,
            key=service,
            single=True,
            params=dict(
                name=(node_info_dict.get('hostname')
                      or node_name) + name_suffix,
                state=None if idx <= instance_amount else 'absent',
            )
        )
        services_info += [service_info]

      if services_info:
        result['prepared_services'] = services_info.copy()

        if validate_ctx:
          info = prepare_services(services_info, env_data, validate_ctx, True)

          error_msgs_aux_service = info.get('error_msgs')

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
            name_suffix = '-' + dns_type_name + \
                (('-' + str(idx)) if idx > 1 else '')
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
            info = prepare_services(
                services_info, env_data, validate_ctx, True)
            error_msgs_aux_service = info.get('error_msgs')

            for value in (error_msgs_aux_service or []):
              new_value = ['context: node dns service'] + value
              error_msgs_aux += [new_value]

    pods = node.get('pods')
    pod_ctx_info_dict = node_info_dict.get('pods')

    if pods:
      node_data = dict(
          pod_ctx_info_dict=pod_ctx_info_dict,
          local=local,
          base_dir=base_dir,
          env_data=env_data,
          validate_ctx=validate_ctx,
          parent_type='node',
          parent_description=node_description,
      )
      info = prepare_pods(pods, node_data)

      prepared_pods = info.get('result')
      error_msgs_aux_pods = info.get('error_msgs')

      if error_msgs_aux_pods:
        error_msgs_aux += error_msgs_aux_pods
      else:
        pod_names = set()

        for pod in (prepared_pods or []):
          pod_names.add(pod.get('name'))

        pod_ctx_info_keys = sorted(list((pod_ctx_info_dict or dict()).keys()))

        for pod_ctx_info_key in pod_ctx_info_keys:
          if pod_ctx_info_key not in pod_names:
            error_msgs_aux += [[
                'pod: ' + pod_ctx_info_key,
                'msg: pod defined in the context for the node info,'
                + ' but the node doesn\'t have a pod with such name',
                'node pods: ',
                sorted(list(pod_names)),
            ]]

        if node_dir in pod_names:
          error_msgs_aux += [[
              'node_dir: ' + node_dir,
              'msg: there is a pod with the same name as the node directory',
          ]]

        result['pods'] = prepared_pods

    for value in (error_msgs_aux or []):
      new_value = ['node: ' + node_description] + value
      error_msgs += [new_value]

  result_keys = list(result.keys())

  for key in result_keys:
    if result.get(key) is None:
      result.pop(key, None)

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


def prepare_task(task_info_dict, env_data, validate_ctx):
  result = dict()
  error_msgs = []

  task_name = task_info_dict.get('name')

  if not task_name:
    error_msgs += [[
        'msg: task name not specified'
    ]]
    return dict(result=result, error_msgs=error_msgs)

  task_key = task_info_dict.get('key') or task_name
  task_description = task_name if (
      task_name == task_key) else task_name + ' (' + task_key + ')'

  env = env_data.get('env')
  tasks_dict = env.get('tasks')

  if not tasks_dict:
    error_msgs += [[
        'task: ' + task_description,
        'msg: no task specified for the environment'
    ]]
    return dict(result=result, error_msgs=error_msgs)

  task = tasks_dict.get(task_key)

  if task is None:
    error_msgs += [[
        'task: ' + task_description,
        'msg: task not specified in the environment dictionary'
    ]]
    return dict(result=result, error_msgs=error_msgs)

  result_aux_info = dict()
  error_msgs_aux = []

  task_type = task.get('type')
  task_target_origin = task.get('target_origin')

  task_target_origin = (
      task_target_origin or 'cloud') if task_type == 'task' else None

  result['name'] = task_name
  result['key'] = task_key
  result['description'] = task_description
  result['type'] = task_type
  result['target_origin'] = task_target_origin
  result['file'] = task.get('file')
  result['cmd'] = task.get('cmd')
  result['poll'] = task.get('poll')
  result['root'] = to_bool(task.get('root'))

  valid_task_types = ['skip', 'task', 'shell']

  if task_type not in valid_task_types:
    error_msgs_aux += [[
        'task_type: ' + task_type,
        'msg: invalid task type',
        'valid task types:',
        valid_task_types,
    ]]
  else:
    allowed_props_map = dict(
        task=list([
            'type',
            'target_origin',
            'file',
            'root',
            'params_schema',
            'credentials_schema',
            'credentials',
            'params',
            'group_params',
            'shared_params',
            'shared_group_params',
        ]),
        shell=list(['type', 'cmd', 'root', 'poll']),
        skip=list(['type']),
    )

    allowed_props = allowed_props_map.get(task_type)

    for key in sorted(list(task.keys())):
      if key not in allowed_props:
        error_msgs_aux += [[
            'task_type: ' + task_type,
            'property: ' + key,
            'msg: invalid property for this task type',
            'allowed properties: ',
            allowed_props,
        ]]

    required_props_map = dict(
        task=list(['type', 'file']),
        shell=list(['type', 'cmd']),
        skip=list(['type']),
    )

    required_props = required_props_map.get(task_type)

    for key in sorted(list(required_props)):
      if task.get(key) is None:
        error_msgs_aux += [[
            'task_type: ' + task_type,
            'property: ' + key,
            'msg: required property not specified',
        ]]
      elif not task.get(key):
        error_msgs_aux += [[
            'task_type: ' + task_type,
            'property: ' + key,
            'msg: required property is empty',
        ]]

  params_args = dict(
      group_params=task.get('credentials'),
      group_params_dict=env.get('credentials'),
  )

  info = mix(params_args)

  result_aux_credentials = info.get('result')
  error_msgs_aux_credentials = info.get('error_msgs')

  for value in (error_msgs_aux_credentials or []):
    new_value = ['context: task credentials'] + value
    error_msgs_aux += [new_value]

  if not error_msgs_aux_credentials:
    if task_type != 'task':
      if result_aux_credentials:
        error_msgs_aux += [[
            'task_type: ' + task_type,
            'msg: task type has no support for task credentials',
        ]]

    credentials = result_aux_credentials
    result['credentials'] = credentials

    schema_file = task.get('credentials_schema')
    result['credentials_schema'] = schema_file

    if validate_ctx and task_target_origin in ['cloud', 'env']:
      if schema_file:
        schema_file_full = (
            schema_file
            if (task_target_origin == 'cloud')
            else env_data.get('env_dir') + '/' + schema_file
        )

        if os.path.exists(schema_file_full):
          schema = load_schema(schema_file_full)
          error_msgs_aux_validate = validate(schema, credentials)

          for value in (error_msgs_aux_validate or []):
            new_value = ['context: validate task credentials'] + value
            error_msgs_aux += [new_value]
        else:
          error_msgs_aux += [[
              'context: validate task credentials',
              'target_origin: ' + task_target_origin,
              'msg: credentials schema file not found: ' + schema_file,
          ]]

  error_msgs_aux_params = []

  if isinstance(task_info_dict, dict):
    params_args = dict(
        params=task_info_dict.get('params'),
        group_params=task_info_dict.get('group_params'),
        shared_params=task_info_dict.get('shared_params'),
        shared_group_params=task_info_dict.get('shared_group_params'),
        shared_group_params_dict=env.get('task_shared_group_params'),
        shared_params_dict=env.get('task_shared_params'),
        group_params_dict=env.get('task_group_params'),
    )

    info = mix(params_args)

    result_aux_info = info.get('result')
    error_msgs_aux_info = info.get('error_msgs')

    for value in (error_msgs_aux_info or []):
      new_value = ['context: task info params'] + value
      error_msgs_aux_params += [new_value]

  params_args = dict(
      params=task.get('params'),
      group_params=task.get('group_params'),
      shared_params=task.get('shared_params'),
      shared_group_params=task.get('shared_group_params'),
      shared_group_params_dict=env.get('task_shared_group_params'),
      shared_params_dict=env.get('task_shared_params'),
      group_params_dict=env.get('task_group_params'),
  )

  info = mix(params_args)

  result_aux_task = info.get('result')
  error_msgs_aux_task = info.get('error_msgs')

  for value in (error_msgs_aux_task or []):
    new_value = ['context: task params'] + value
    error_msgs_aux_params += [new_value]

  error_msgs_aux += error_msgs_aux_params

  if not error_msgs_aux_params:
    if task_type != 'task':
      if result_aux_info:
        error_msgs_aux += [[
            'task_type: ' + task_type,
            'msg: task type has no support for task parameters (overwrite)',
        ]]

      if result_aux_task:
        error_msgs_aux += [[
            'task_type: ' + task_type,
            'msg: task type has no support for task parameters',
        ]]

    task_params = merge_dicts(result_aux_task, result_aux_info)
    result['params'] = task_params

    schema_file = task.get('params_schema')
    result['params_schema'] = schema_file

    if validate_ctx and task_target_origin in ['cloud', 'env']:
      if schema_file:
        schema_file_full = (
            schema_file
            if (task_target_origin == 'cloud')
            else env_data.get('env_dir') + '/' + schema_file
        )

        if os.path.exists(schema_file_full):
          schema = load_schema(schema_file_full)
          error_msgs_aux_validate = validate(schema, task_params)

          for value in (error_msgs_aux_validate or []):
            new_value = ['context: validate task params'] + value
            error_msgs_aux += [new_value]
        else:
          error_msgs_aux += [[
              'context: validate task params',
              'target_origin: ' + task_target_origin,
              'msg: params schema file not found: ' + schema_file,
          ]]

  for value in (error_msgs_aux or []):
    new_value = ['task: ' + task_description] + value
    error_msgs += [new_value]

  result_keys = list(result.keys())

  for key in result_keys:
    if result.get(key) is None:
      result.pop(key, None)

  return dict(result=result, error_msgs=error_msgs)


def prepare_run_stage_task(run_stage_task_info, run_stage_data):
  result = dict()
  error_msgs = []

  default_task_name = run_stage_data.get('default_task_name')
  prepared_nodes = run_stage_data.get('prepared_nodes')
  env_data = run_stage_data.get('env_data')
  validate_ctx = run_stage_data.get('validate_ctx')

  env = env_data.get('env')

  run_stage_task_name = None

  if isinstance(run_stage_task_info, dict):
    run_stage_task_name = default_task_name
    run_stage_task = run_stage_task_info

    if not run_stage_task_name:
      error_msgs += [['msg: run stage task default name not defined']]
      return dict(result=result, error_msgs=error_msgs)
  else:
    run_stage_task_name = run_stage_task_info

    if not run_stage_task_name:
      error_msgs += [['msg: run stage task name not defined']]
      return dict(result=result, error_msgs=error_msgs)

    run_stage_tasks_dict = env.get('run_stage_tasks')

    if not run_stage_tasks_dict:
      error_msgs += [[
          'run_stage_task: ' + run_stage_task_name,
          'msg: no run stage task specified for the environment'
      ]]
      return dict(result=result, error_msgs=error_msgs)

    run_stage_task = run_stage_tasks_dict.get(run_stage_task_name)

    if run_stage_task is None:
      error_msgs += [[
          'run_stage_task: ' + run_stage_task_name,
          'msg: run stage task not specified for the environment'
      ]]
      return dict(result=result, error_msgs=error_msgs)

  result['name'] = run_stage_task_name

  task_name = run_stage_task.get('name')

  if not task_name:
    error_msgs += [[
        'run_stage_task: ' + run_stage_task_name,
        'msg: task name relative to the run stage task not specified'
    ]]

  stage_node_task = run_stage_task.get('node_task')
  stage_pod_task = run_stage_task.get('pod_task')

  result['node_task'] = stage_node_task
  result['pod_task'] = stage_pod_task

  if (not stage_node_task) and (not stage_pod_task):
    error_msgs += [[
        'run_stage_task: ' + run_stage_task_name,
        'task_name: ' + task_name,
        'msg: please, specify if the task is for the nodes or pods',
        'additional info: node_task and pod_task are both false',
    ]]
  elif stage_node_task and stage_pod_task:
    error_msgs += [[
        'run_stage_task: ' + run_stage_task_name,
        'task_name: ' + task_name,
        'msg: the task must be for the nodes or pods, but not both'
        'additional info: node_task and pod_task are both true',
    ]]

  all_nodes = []
  node_map = dict()
  node_pod_map = dict()

  for node in (prepared_nodes or []):
    node_name = node.get('name')

    pods_aux = []
    pod_map = dict()

    if stage_pod_task:
      for pod in (node.get('pods') or []):
        pod_name = pod.get('name')

        pod_aux = dict(
            name=pod_name,
            description=pod.get('description'),
            pod_dir=pod.get('pod_dir'),
            tmp_dir=pod.get('tmp_dir'),
            data_dir=pod.get('data_dir'),
            local_dir=pod.get('local_dir'),
        )

        pods_aux += [pod_aux]
        pod_map[pod_name] = pod_aux

    node_aux = dict(
        name=node_name,
        description=node.get('description'),
        local=node.get('local'),
        node_dir=node.get('node_dir'),
        tmp_dir=node.get('tmp_dir'),
        local_dir=node.get('local_dir'),
        pods=pods_aux
    )

    all_nodes += [node_aux]
    node_map[node_name] = node_aux
    node_pod_map[node_name] = pod_map

  is_all_nodes = run_stage_task.get('all_nodes')
  nodes_to_run = []

  if is_all_nodes:
    nodes_to_run = all_nodes
  else:
    node_info_list = run_stage_task.get('nodes')

    for node_info in (node_info_list or []):
      node_name = node_info if isinstance(
          node_info, str) else node_info.get('name')

      node = node_map.get(node_name)

      if not node:
        error_msgs += [[
            'run_stage_task: ' + run_stage_task_name,
            'task_name: ' + task_name,
            'node_name: ' + node_name,
            'msg: node not found in the environment'
        ]]
      elif isinstance(node_info, str):
        nodes_to_run += [node]
      else:
        all_pods = node_info.get('all_pods')
        pods_names = node_info.get('pods')

        if (not all_pods) and (pods_names is None):
          error_msgs += [[
              'run_stage_task: ' + run_stage_task_name,
              'task_name: ' + task_name,
              'node_name: ' + node_name,
              'msg: all_pods must be true or pods must be defined'
          ]]
        elif (all_pods is not None) and (pods_names is not None):
          error_msgs += [[
              'run_stage_task: ' + run_stage_task_name,
              'task_name: ' + task_name,
              'node_name: ' + node_name,
              'msg: pods and all_pods specified for the node (specify only one)'
          ]]
        elif all_pods:
          nodes_to_run += [node]
        else:
          all_node_pods_names = map(
              lambda p: p.get('name'), node.get('pods') or [])

          for pod_name in (pods_names or []):
            if pod_name not in all_node_pods_names:
              error_msgs += [[
                  'run_stage_task: ' + run_stage_task_name,
                  'task_name: ' + task_name,
                  'node_name: ' + node_name,
                  'pod_name: ' + pod_name,
                  'msg: pod specified for the node task, but not specified in the node itself'
              ]]

          pod_map = node_pod_map.get(node_name)
          pods_to_add = [pod_map.get(pod_name) for pod_name in pods_names]

          node_to_add = node.copy()
          node_to_add['pods'] = pods_to_add
          nodes_to_run += [node_to_add]

  result['nodes'] = nodes_to_run

  if task_name:
    result['task_name'] = task_name

    info = prepare_task(run_stage_task, env_data, validate_ctx)

    result_aux = info.get('result')
    error_msgs_aux = info.get('error_msgs')

    if error_msgs_aux:
      for value in error_msgs_aux:
        new_value = ['run_stage_task: ' + run_stage_task_name] + value
        error_msgs += [new_value]
    else:
      task = result_aux

      task_description = task.get('description')
      task_type = task.get('type')
      task_target_origin = task.get('target_origin')
      task_file = task.get('file')

      if validate_ctx and (task_type == 'task'):
        error_msgs_aux = []

        if task_target_origin != 'pod':
          task_file_full = (
              task_file
              if (task_target_origin == 'cloud')
              else env_data.get('env_dir') + '/' + task_file
          )

          if not os.path.exists(task_file_full):
            error_msgs_aux += [['msg: task file not found: ' + task_file]]
        else:
          task_file_paths = set()

          if stage_node_task:
            error_msgs_aux += [['msg: node task with pod target_origin: ' + task_file]]

          for node in nodes_to_run:
            for pod in node.get('pods'):
              pod_local_dir = pod.get('local_dir')
              error_msgs_aux_pod = []

              schema_file = task.get('credentials_schema')

              if schema_file:
                schema_file_full = pod_local_dir + '/' + schema_file
                task_credentials = task.get('credentials')

                if os.path.exists(schema_file_full):
                  schema = load_schema(schema_file_full)
                  error_msgs_aux_validate = validate(schema, task_credentials)

                  for value in (error_msgs_aux_validate or []):
                    new_value = [
                        'context: validate pod task credentials'] + value
                    error_msgs_aux_pod += [new_value]
                else:
                  error_msgs_aux_pod += [[
                      'context: validate pod task credentials',
                      'msg: credentials schema file not found: ' + schema_file,
                  ]]

              schema_file = task.get('params_schema')

              if schema_file:
                schema_file_full = pod_local_dir + '/' + schema_file
                task_params = task.get('params')

                if os.path.exists(schema_file_full):
                  schema = load_schema(schema_file_full)
                  error_msgs_aux_validate = validate(schema, task_params)

                  for value in (error_msgs_aux_validate or []):
                    new_value = ['context: validate pod task params'] + value
                    error_msgs_aux_pod += [new_value]
                else:
                  error_msgs_aux_pod += [[
                      'context: validate pod task params',
                      'msg: params schema file not found: ' + schema_file,
                  ]]

              task_file_path = pod_local_dir + '/' + task_file

              if task_file_path not in task_file_paths:
                if not os.path.exists(task_file_path):
                  error_msgs_aux_pod += [[
                      'msg: pod task file not found: ' + task_file,
                  ]]

                task_file_paths.add(task_file_path)

              for value in error_msgs_aux_pod:
                new_value = [
                    'node_name: ' + node_name,
                    'pod_name: ' + pod_name,
                ] + value
                error_msgs_aux += [new_value]

        for value in error_msgs_aux:
          new_value = [
              'run_stage_task: ' + run_stage_task_name,
              'task: ' + task_description,
              'task_type: ' + task_type,
              'task_target_origin: ' + task_target_origin,
          ] + value
          error_msgs += [new_value]

      result['task'] = task

  result_keys = list(result.keys())

  for key in result_keys:
    if result.get(key) is None:
      result.pop(key, None)

  return dict(result=result, error_msgs=error_msgs)


def prepare_run_stage(run_stage_info, default_name, prepared_nodes, env_data, validate_ctx):
  result = dict()
  error_msgs = []

  env = env_data.get('env')

  run_stage_name = None
  run_stage_tasks_input = None

  if isinstance(run_stage_info, dict):
    run_stage_name = default_name

    if not run_stage_name:
      error_msgs += [['msg: run stage default name not defined']]
      return dict(result=result, error_msgs=error_msgs)

    run_stage_tasks_input = run_stage_info.get('tasks')

    if run_stage_tasks_input is None:
      error_msgs += [[
          'run_stage: ' + run_stage_name,
          'msg: run stage tasks not specified'
      ]]
      return dict(result=result, error_msgs=error_msgs)
  else:
    run_stage_name = run_stage_info

    if not run_stage_name:
      error_msgs += [['msg: run stage name not defined']]
      return dict(result=result, error_msgs=error_msgs)

    run_stages_dict = env.get('run_stages')

    if not run_stages_dict:
      error_msgs += [[
          'run_stage: ' + run_stage_name,
          'msg: no run stage specified for the environment'
      ]]
      return dict(result=result, error_msgs=error_msgs)

    run_stage_tasks_input = run_stages_dict.get(run_stage_name)

    if run_stage_tasks_input is None:
      error_msgs += [[
          'run_stage: ' + run_stage_name,
          'msg: run stage not specified for the environment'
      ]]
      return dict(result=result, error_msgs=error_msgs)

  result['name'] = run_stage_name

  hosts = set()
  run_stage_tasks = []
  run_stage_task_names = set()
  task_names = set()

  for idx, run_stage_task in enumerate(run_stage_tasks_input or []):
    default_task_name = str(idx + 1)
    run_stage_data = dict(
        default_task_name=default_task_name,
        prepared_nodes=prepared_nodes,
        env_data=env_data,
        validate_ctx=validate_ctx,
    )
    info = prepare_run_stage_task(
        run_stage_task,
        run_stage_data,
    )

    result_aux = info.get('result')
    error_msgs_aux = info.get('error_msgs')

    if error_msgs_aux:
      for value in (error_msgs_aux or []):
        new_value = ['run_stage: ' + run_stage_name] + value
        error_msgs += [new_value]
    else:
      run_stage_task = result_aux
      run_stage_task_name = run_stage_task.get('name')

      if run_stage_task_name in run_stage_task_names:
        error_msgs += [[
            'run_stage: ' + run_stage_name,
            'run_stage_task: ' + run_stage_task_name,
            'msg: duplicate run stage task name',
        ]]
      else:
        nodes = run_stage_task.get('nodes')
        hosts.update(map(lambda n: 'main' if n.get(
            'local') else n.get('name'), nodes or []))
        run_stage_task_names.add(run_stage_task_name)
        run_stage_tasks += [run_stage_task]

        task_name = run_stage_task.get('task_name')

        if task_name and (task_name in task_names):
          error_msgs += [[
              'run_stage: ' + run_stage_name,
              'run_stage_task: ' + run_stage_task_name,
              'task_name: ' + task_name,
              'msg: duplicate task name'
          ]]
        elif task_name:
          task_names.add(task_name)

  result['hosts'] = sorted(list(hosts))
  result['tasks'] = run_stage_tasks

  result_keys = list(result.keys())

  for key in result_keys:
    if result.get(key) is None:
      result.pop(key, None)

  return dict(result=result, error_msgs=error_msgs)


def prepare_run_stages(run_stages, prepared_nodes, env_data, validate_ctx):
  result = []
  error_msgs = []

  for idx, run_stage_info in enumerate(run_stages or []):
    default_name = str(idx + 1)
    info = prepare_run_stage(
        run_stage_info, default_name, prepared_nodes, env_data, validate_ctx)

    result_aux = info.get('result')
    error_msgs_aux = info.get('error_msgs')

    if error_msgs_aux:
      error_msgs += error_msgs_aux
    else:
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

      info = mix(params_args)

      result_aux = info.get('result')
      error_msgs_aux = info.get('error_msgs')

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
        info = prepare_services(ctx_initial_services,
                                env_data, validate_ctx, top=True)

        result_aux = info.get('result')
        error_msgs_aux = info.get('error_msgs')

        for value in (error_msgs_aux or []):
          new_value = ['service context: initial services'] + value
          error_msgs += [new_value]

        if not error_msgs_aux:
          result['prepared_initial_services'] = result_aux

      ctx_nodes = ctx.get('nodes')
      prepared_nodes = []
      nodes_errors = []

      if ctx_nodes:
        info = prepare_nodes(ctx_nodes, env_data, validate_ctx)

        result_aux = info.get('result')
        error_msgs_aux = info.get('error_msgs')

        if error_msgs_aux:
          nodes_errors = error_msgs_aux
          error_msgs += error_msgs_aux
        else:
          prepared_nodes = result_aux
          result['nodes'] = prepared_nodes

      ctx_final_services = ctx.get('final_services')

      if ctx_final_services:
        info = prepare_services(
            ctx_final_services, env_data, validate_ctx, top=True)

        result_aux = info.get('result')
        error_msgs_aux = info.get('error_msgs')

        for value in (error_msgs_aux or []):
          new_value = ['service context: final services'] + value
          error_msgs += [new_value]

        if not error_msgs_aux:
          result['prepared_final_services'] = result_aux

      run_stages = ctx.get('run_stages')

      if run_stages:
        if not prepared_nodes:
          if not nodes_errors:
            error_msgs += [[
                'context: ctx params - run stages',
                'msg: no node found (at least one node is needed when run_stages is defined)',
            ]]
        else:
          info = prepare_run_stages(
              run_stages, prepared_nodes, env_data, validate_ctx)

          result_aux = info.get('result')
          error_msgs_aux = info.get('error_msgs')

          if error_msgs_aux:
            error_msgs += error_msgs_aux
          else:
            result['run_stages'] = result_aux

  result_keys = list(result.keys())

  for key in result_keys:
    if result.get(key) is None:
      result.pop(key, None)

  return dict(result=result, error_msgs=error_msgs)
