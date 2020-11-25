#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=wrong-import-position
# pylint: disable=import-error

from __future__ import absolute_import, division, print_function
__metaclass__ = type # pylint: disable=invalid-name

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


import os

from ansible.module_utils.lrd_utils import merge_dicts, load_yaml_file, default
from ansible.module_utils.lrd_util_params_mixer import mix
from ansible.module_utils.lrd_util_schema import validate

schema_dict = dict()

def load_schema(schema_file):
  if schema_file in schema_dict:
    return schema_dict.get(schema_file)

  schema = load_yaml_file(schema_file)
  schema_dict[schema_file] = schema

  return schema

def prepare_service(service_info, service_names, env, validate_ctx, top):
  result = dict()
  error_msgs = []

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
    service_result = service.copy()
    service_result.pop('services', None)
    service_result.pop('credentials', None)
    service_result.pop('params', None)
    service_result.pop('group_params', None)
    service_result.pop('shared_params', None)
    service_result.pop('shared_group_params', None)
    result['service'] = service_result

    result_aux_info = dict()
    error_msgs_aux = []

    is_list = service.get('list')

    if top:
      result['tmp'] = service_info_dict.get('tmp')
      result['can_destroy'] = service_info_dict.get('can_destroy')
      service_info_dict.pop('tmp', None)
      service_info_dict.pop('can_destroy', None)

    if is_list:
      allowed_keys = [
          'name',
          'key',
          'single',
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
        'flat_list',
        'inverse_destroy',
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
          'type',
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
    base_dir_prefix = service.get('base_dir') + '/' if service.get('base_dir') else ''

    if not is_list:
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
              error_msgs_aux += [['credentials schema file not found: ' + schema_file]]

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
          error_msgs_aux += [new_value]

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
        error_msgs_aux += [new_value]

      if not error_msgs_aux:
        service_params = merge_dicts(result_aux_service, result_aux_info)
        result['service_params'] = service_params

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
              error_msgs_aux += [['params schema file not found: ' + schema_file]]

      for value in (error_msgs_aux or []):
        new_value = ['service: ' + service_description] + value
        error_msgs += [new_value]
    else:
      services = service.get('services')

      if services:
        info_children = prepare_services(
            services, env, validate_ctx, top=False, service_names=service_names)

        result_children = info_children.get('result')
        error_msgs_children = info_children.get('error_msgs')

        for value in (error_msgs_children or []):
          new_value = ['service (parent): ' + service_description] + value
          error_msgs += [new_value]

        if not error_msgs_children:
          result['is_list'] = True
          result['services'] = result_children

  return dict(result=result, error_msgs=error_msgs)

def prepare_services(services, env, validate_ctx, top = False, service_names = None):
  result = []
  error_msgs = []
  service_names = service_names if service_names is not None else set()

  if services:
    services_dict = env.get('services')

    if not services_dict:
      error_msgs += [['msg: no service specified for the environment']]
    else:
      for service_info in services:
        info = prepare_service(service_info, service_names, env, validate_ctx, top)

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

def prepare_pod(pod_info, pod_ctx_info_dict, env, validate_ctx):
  result = dict()
  error_msgs = []

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
        'name: ' + pod_name,
        'key: ' + pod_key,
        'existing_keys:',
        sorted(list(pods_dict.keys())),
        'msg: no pod specified for the environment'
    ]]
  else:
    pod = pods_dict.get(pod_key)
    pod_result = pod.copy()
    pod_result.pop('credentials', None)
    pod_result.pop('params', None)
    pod_result.pop('group_params', None)
    pod_result.pop('shared_params', None)
    pod_result.pop('shared_group_params', None)
    result['pod'] = pod_result

    base_dir_prefix = pod.get('base_dir') + '/' if pod.get('base_dir') else ''
    pod_ctx_info = (pod_ctx_info_dict or dict()).get(pod_name)
    result_aux_ctx_info = dict()
    result_aux_info = dict()
    error_msgs_aux = []

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
          schema_file = base_dir_prefix + schema_file

          if os.path.exists(schema_file):
            schema = load_schema(schema_file)
            error_msgs_aux_validate = validate(schema, credentials)

            for value in (error_msgs_aux_validate or []):
              new_value = ['context: validate pod credentials'] + value
              error_msgs_aux += [new_value]
          else:
            error_msgs_aux += [['credentials schema file not found: ' + schema_file]]

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
        error_msgs_aux += [new_value]

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
        error_msgs_aux += [new_value]

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
      error_msgs_aux += [new_value]

    if not error_msgs_aux:
      pod_params = merge_dicts(result_aux_pod, result_aux_info, result_aux_ctx_info)
      result['pod_params'] = pod_params

      if validate_ctx:
        schema_file = pod.get('params_schema')

        if schema_file:
          schema_file = base_dir_prefix + schema_file

          if os.path.exists(schema_file):
            schema = load_schema(schema_file)
            error_msgs_aux_validate = validate(schema, pod_params)

            for value in (error_msgs_aux_validate or []):
              new_value = ['context: validate pod params'] + value
              error_msgs_aux += [new_value]
          else:
            error_msgs_aux += [['params schema file not found: ' + schema_file]]

    for value in (error_msgs_aux or []):
      new_value = ['pod: ' + pod_description] + value
      error_msgs += [new_value]

  return dict(result=result, error_msgs=error_msgs)

def prepare_pods(pods, pod_ctx_info_dict, env, validate_ctx):
  result = []
  error_msgs = []
  pod_names = set()

  if pods:
    pods_dict = env.get('pods')

    if not pods_dict:
      error_msgs += [['msg: no pod specified for the environment']]
    else:
      for pod_info in pods:
        info = prepare_pod(pod_info, pod_ctx_info_dict, env, validate_ctx)

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

def prepare_node(node_info, env, validate_ctx):
  result = dict()
  error_msgs = []

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
        'name: ' + node_name,
        'key: ' + node_key,
        'existing_keys:',
        sorted(list(nodes_dict.keys())),
        'msg: no node specified for the environment'
    ]]
  else:
    node = nodes_dict.get(node_key)
    node_result = node.copy()
    node_result.pop('pods', None)
    node_result.pop('params', None)
    node_result.pop('group_params', None)
    node_result.pop('shared_params', None)
    node_result.pop('shared_group_params', None)
    result['node'] = node_result

    result_aux_info = dict()
    error_msgs_aux = []

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
              new_value = ['context: validate credentials'] + value
              error_msgs_aux += [new_value]
          else:
            error_msgs_aux += [['credential schema file not found: ' + schema_file]]

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
        error_msgs_aux += [new_value]

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
      error_msgs_aux += [new_value]

    if not error_msgs_aux:
      node_params = merge_dicts(result_aux_node, result_aux_info)
      result['node_params'] = node_params

      if validate_ctx:
        schema_file = 'schemas/node_params.schema.yml'

        if os.path.exists(schema_file):
          schema = load_schema(schema_file)
          error_msgs_aux_validate = validate(schema, node_params)

          for value in (error_msgs_aux_validate or []):
            new_value = ['context: validate node params'] + value
            error_msgs_aux += [new_value]
        else:
          error_msgs_aux += [['params schema file not found: ' + schema_file]]

    pods = node.get('pods')
    pod_ctx_info_dict = node_info_dict.get('pods')

    if pods:
      pods_info = prepare_pods(pods, pod_ctx_info_dict, env, validate_ctx)

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

def prepare_nodes(nodes, env, validate_ctx):
  result = []
  error_msgs = []
  node_names = set()

  if nodes:
    nodes_dict = env.get('nodes')

    if not nodes_dict:
      error_msgs += [['msg: no node specified for the environment']]
    else:
      for node_info in nodes:
        info = prepare_node(node_info, env, validate_ctx)

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

def prepare_ctx(ctx_name, env, validate_ctx):
  result = dict()
  error_msgs = []

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
      ctx_result = ctx.copy()
      ctx_result.pop('initial_services', None)
      ctx_result.pop('nodes', None)
      ctx_result.pop('final_services', None)
      ctx_result.pop('params', None)
      ctx_result.pop('group_params', None)
      ctx_result.pop('shared_params', None)
      ctx_result.pop('shared_group_params', None)
      result['ctx'] = ctx_result

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
        result['ctx_params'] = ctx_params

        if validate_ctx:
          schema_file = 'schemas/ctx_params.schema.yml'

          if os.path.exists(schema_file):
            schema = load_schema(schema_file)
            error_msgs_aux = validate(schema, ctx_params)

            for value in (error_msgs_aux or []):
              new_value = ['context: validate ctx params'] + value
              error_msgs += [new_value]
          else:
            error_msgs_aux += [['schema file not found: ' + schema_file]]

      ctx_initial_services = ctx.get('initial_services')

      if ctx_initial_services:
        services_info = prepare_services(ctx_initial_services, env, validate_ctx, top=True)

        result_aux = services_info.get('result')
        error_msgs_aux = services_info.get('error_msgs')

        for value in (error_msgs_aux or []):
          new_value = ['service context: initial services'] + value
          error_msgs += [new_value]

        if not error_msgs_aux:
          result['initial_services'] = result_aux

      ctx_nodes = ctx.get('nodes')

      if ctx_nodes:
        nodes_info = prepare_nodes(ctx_nodes, env, validate_ctx)

        result_aux = nodes_info.get('result')
        error_msgs_aux = nodes_info.get('error_msgs')

        if error_msgs_aux:
          error_msgs += error_msgs_aux
        else:
          result['nodes'] = result_aux

      ctx_final_services = ctx.get('final_services')

      if ctx_final_services:
        services_info = prepare_services(ctx_final_services, env, validate_ctx, top=True)

        result_aux = services_info.get('result')
        error_msgs_aux = services_info.get('error_msgs')

        for value in (error_msgs_aux or []):
          new_value = ['service context: final services'] + value
          error_msgs += [new_value]

        if not error_msgs_aux:
          result['final_services'] = result_aux

  return dict(result=result, error_msgs=error_msgs)
