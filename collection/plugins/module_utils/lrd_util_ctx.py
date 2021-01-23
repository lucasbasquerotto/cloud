#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=import-error
# pylint: disable=too-many-lines
# pylint: disable=broad-except

from __future__ import absolute_import, division, print_function
__metaclass__ = type  # pylint: disable=invalid-name

import os
import traceback

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import (
    default, is_empty, is_str, load_cached_file, merge_dicts, to_bool
)
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_content import (
    load_content, prepare_content
)
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_node_dependencies import (
    prepare_node_dependencies
)
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_params_mixer import mix
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_pod_vars import load_vars
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_schema import validate_schema


def prepare_service(service_info, run_info, top, service_names=None):
  try:
    result = dict()
    error_msgs = []

    service_names = service_names if service_names is not None else set()

    env_data = run_info.get('env_data')
    validate_ctx = run_info.get('validate')

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
          str('service_name: ' + service_name),
          'msg: duplicate service name',
      ]]
      return dict(result=result, error_msgs=error_msgs)
    else:
      service_names.add(service_name)

    result['name'] = service_name
    result['key'] = service_key
    result['description'] = service_description

    try:
      services_dict = env.get('services')

      if service_key not in services_dict:
        error_msgs += [[
            str('service: ' + service_description),
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

        tmp = None
        can_destroy = None

        if top:
          tmp = to_bool(service_info_dict.get('tmp'))
          service_info_dict.pop('tmp', None)
          can_destroy = to_bool(service_info_dict.get('can_destroy'))
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
                  str('property: ' + key),
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
                  str('property: ' + key),
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
              'credentials',
              'contents',
              'params',
              'group_params',
              'shared_params',
              'shared_group_params',
          ]

          for key in sorted(list(service_info_dict.keys())):
            if key not in allowed_keys:
              error_msgs_aux += [[
                  str('property: ' + key),
                  'msg: invalid service info property for a non-list service',
                  'allowed properties:',
                  sorted(list(allowed_keys)),
              ]]

          allowed_keys = [
              'list',
              'base_dir',
              'task',
              'namespace',
              'schema',
              'credentials',
              'contents',
              'params',
              'group_params',
              'shared_params',
              'shared_group_params',
          ]

          for key in sorted(list(service.keys())):
            if key not in allowed_keys:
              error_msgs_aux += [[
                  str('property: ' + key),
                  'msg: invalid service property for a non-list service',
                  'allowed properties:',
                  sorted(list(allowed_keys)),
              ]]

        for value in (error_msgs_aux or []):
          new_value = [str('service: ' + service_description)] + value
          error_msgs += [new_value]

        error_msgs_aux = []

        if not is_list:
          result['tmp'] = tmp
          result['can_destroy'] = can_destroy

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
            task_file = (base_dir_prefix + task) or ''

            if not os.path.exists(task_file):
              error_msgs_aux += [[str('task file not found: ' + task_file)]]

          credentials_info_dict = service_info_dict.get('credentials')
          credentials_dict = service.get('credentials')
          credentials_env_dict = env.get('credentials')

          if credentials_info_dict:
            credentials_dict = merge_dicts(
                credentials_dict, credentials_info_dict)

          params_args = dict(
              group_params=credentials_dict,
              group_params_dict=credentials_env_dict,
          )

          info = mix(params_args)

          result_aux_credentials = info.get('result')
          error_msgs_aux_credentials = info.get('error_msgs') or list()

          for value in (error_msgs_aux_credentials or []):
            new_value = ['context: service credentials'] + value
            error_msgs_aux += [new_value]

          if not error_msgs_aux_credentials:
            credentials = result_aux_credentials
            result['credentials'] = credentials or None

          error_msgs_aux_params = []

          if isinstance(service_info, dict):
            params_args = dict(
                params=service_info_dict.get('params'),
                group_params=service_info_dict.get('group_params'),
                shared_params=service_info_dict.get('shared_params'),
                shared_group_params=service_info_dict.get(
                    'shared_group_params'),
                shared_group_params_dict=env.get(
                    'service_shared_group_params'),
                shared_params_dict=env.get('service_shared_params'),
                group_params_dict=env.get('service_group_params'),
            )

            info = mix(params_args)

            result_aux_info = info.get('result')
            error_msgs_aux_info = info.get('error_msgs') or list()

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
          error_msgs_aux_service = info.get('error_msgs') or list()

          for value in (error_msgs_aux_service or []):
            new_value = ['context: service params'] + value
            error_msgs_aux_params += [new_value]

          error_msgs_aux += error_msgs_aux_params

          if not error_msgs_aux_params:
            service_params = merge_dicts(result_aux_service, result_aux_info)
            result['params'] = service_params or None

          contents = service.get('contents')
          prepared_contents = dict()

          contents_info = service_info_dict.get('contents')

          if contents_info:
            contents = merge_dicts(contents, contents_info)

          for content_key in sorted(list((contents or dict()).keys())):
            content = contents.get(content_key)

            info = load_content(content, env=env, run_info=run_info)

            prepared_content = info.get('result')
            error_msgs_aux_content = info.get('error_msgs') or list()

            for value in (error_msgs_aux_content or []):
              new_value = [str('service content: ' + content_key)] + value
              error_msgs_aux += [new_value]

            if not error_msgs_aux_content:
              prepared_contents[content_key] = prepared_content

          result['contents'] = prepared_contents or None

          if validate_ctx and not error_msgs_aux:
            schema_file = service.get('schema')

            if schema_file:
              schema_file = base_dir_prefix + schema_file

            if schema_file:
              if os.path.exists(schema_file):
                schema = load_cached_file(schema_file)

                schema_data = dict()

                for key in ['params', 'credentials', 'contents']:
                  if result.get(key) is not None:
                    schema_data[key] = result.get(key)

                error_msgs_aux_validate = validate_schema(
                    schema, schema_data
                )

                for value in (error_msgs_aux_validate or []):
                  new_value = [
                      'context: validate service schema',
                      str('schema file: ' + schema_file),
                  ] + value
                  error_msgs_aux += [new_value]
              else:
                error_msgs_aux += [[
                    'context: validate service schema',
                    str('msg: schema file not found: ' + schema_file),
                ]]

          for value in (error_msgs_aux or []):
            new_value = [str('service: ' + service_description)] + value
            error_msgs += [new_value]
        else:
          single = service_info_dict.get('single')

          if single:
            error_msgs_aux += [[
                'msg: service should not be a list (single)',
            ]]

          for value in (error_msgs_aux or []):
            new_value = [str('service: ' + service_description)] + value
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
                services,
                run_info=run_info,
                top=False,
                service_names=service_names
            )

            result_children = info.get('result')
            error_msgs_children = info.get('error_msgs') or list()

            for value in (error_msgs_children or []):
              new_value = [
                  str('service (parent): ' + service_description)] + value
              error_msgs += [new_value]

            if not error_msgs_children:
              if result_children:
                for result_child in result_children:
                  result_child['tmp'] = tmp
                  result_child['can_destroy'] = can_destroy

              result['is_list'] = True
              result['services'] = result_children

      result_keys = list(result.keys())

      for key in result_keys:
        if result.get(key) is None:
          result.pop(key, None)

      return dict(result=result, error_msgs=error_msgs)
    except Exception as error:
      error_msgs = [[
          str('service: ' + service_description),
          'msg: error when trying to prepare service',
          'error type: ' + str(type(error)),
          'error details: ',
          traceback.format_exc(),
      ]]
      return dict(error_msgs=error_msgs)
  except Exception as error:
    error_msgs = [[
        'msg: error when trying to prepare unknown service',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_services(services, run_info, top=False, service_names=None):
  try:
    result = []
    error_msgs = []
    service_names = service_names if service_names is not None else set()

    env_data = run_info.get('env_data')
    env = env_data.get('env')

    if services:
      services_dict = env.get('services')

      if not services_dict:
        error_msgs += [['msg: no service specified for the environment']]
      else:
        for service_info in services:
          info = prepare_service(
              service_info,
              run_info=run_info,
              top=top,
              service_names=service_names
          )

          result_aux = info.get('result')
          error_msgs_aux = info.get('error_msgs') or list()

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
  except Exception as error:
    error_msgs = [[
        'msg: error when trying to prepare services',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_transfer_content(transfer_contents, context_title, prepare_info, input_params=None):
  try:
    result = list()
    error_msgs_aux = list()

    if not transfer_contents:
      return dict(result=result)

    current_content_dests = set()

    env = prepare_info.get('env')
    env_data = prepare_info.get('env_data')
    custom_dir = prepare_info.get('custom_dir')
    run_info = prepare_info.get('run_info')
    all_content_dests = prepare_info.get('all_content_dests')

    for idx, transfer_content in enumerate(transfer_contents or []):
      try:
        dest = transfer_content.get('dest')
        error_msgs_aux_item = list()

        if dest in current_content_dests:
          error_msgs_aux_item += [['msg: duplicate destination']]
        else:
          current_content_dests.add(dest)

          if dest not in all_content_dests:
            all_content_dests.add(dest)

            info = prepare_content(
                transfer_content.get('src'),
                env=env,
                run_info=run_info,
                additional_info=dict(
                    input_params=input_params,
                    custom_dir=custom_dir,
                ),
            )

          prepared_content = info.get('result')
          error_msgs_aux_content = info.get('error_msgs')

          if error_msgs_aux_content:
            error_msgs_aux_item += error_msgs_aux_content
          else:
            env_lax = env_data.get('lax')
            default_dir_mode = 777 if env_lax else 751
            default_file_mode = 666 if env_lax else 640
            default_file_mode = (
                default_dir_mode
                if to_bool(transfer_content.get('executable'))
                else default_file_mode
            )

            result_item = dict(
                src=prepared_content,
                dest=dest,
                user=transfer_content.get('user'),
                group=transfer_content.get(
                    'group') or transfer_content.get('user'),
                mode=transfer_content.get('mode') or default_file_mode,
                dir_mode=transfer_content.get('dir_mode') or default_dir_mode,
                when=to_bool(transfer_content.get('when')),
            )

            result_item_keys = sorted(list(result_item))

            for key in result_item_keys:
              if result_item.get(key) is None:
                result_item.pop(key, None)

            result += [result_item]

        for value in error_msgs_aux_item:
          new_value = [
              str('content: #' + str(idx + 1)),
              str('dest: ' + dest),
          ] + value
          error_msgs_aux += [new_value]
      except Exception as error:
        error_msgs_aux += [[
            str('content: #' + str(idx + 1)),
            str('dest: ' + dest),
            'msg: error when trying to prepare to transfer the content item',
            'error type: ' + str(type(error)),
            'error details: ',
            traceback.format_exc(),
        ]]

    error_msgs = list()

    for value in error_msgs_aux:
      new_value = [str('context: ' + (context_title or ''))] + value
      error_msgs += [new_value]

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs = [[
        str('context: ' + (context_title or '')),
        'msg: error when trying to prepare to transfer the contents',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_pod(pod_info, parent_data, run_info):
  try:
    result = dict()
    error_msgs = []

    pod_ctx_info_dict = parent_data.get('pod_ctx_info_dict')
    local = parent_data.get('local') or False
    parent_base_dir = parent_data.get('base_dir')
    dependencies = parent_data.get('dependencies')

    env_data = run_info.get('env_data')
    validate_ctx = run_info.get('validate')

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

    try:
      pods_dict = env.get('pods')

      if pod_key not in pods_dict:
        error_msgs += [[
            str('pod: ' + pod_description),
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
              str('msg: repository not found: ' + repo),
          ]]

        for env_repo in (env_repos or []):
          if not repos.get(env_repo.get('repo')):
            error_msgs_aux += [[
                'context: validate pod env repo',
                str('msg: repository not found: ' + env_repo.get('repo')),
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
        extra_repos_dir_relpath = os.path.relpath(
            dev_extra_repos_dir, local_dir)

        flat = pod.get('flat')
        base_dir = None if local else (
            pod.get('base_dir') or (parent_base_dir + '/' + pod_name))
        pod_dir_relpath = pod.get('pod_dir_relpath') or 'main'
        pod_dir = local_dir if local else (
            base_dir if flat else (base_dir + '/' + pod_dir_relpath)
        )
        tmp_dir = (
            (dev_repos_dir + '/tmp/pods/' + pod_identifier)
            if local
            else (
                pod.get('tmp_dir')
                or (
                    (parent_base_dir + '/.pods/' + pod_name + '/tmp')
                    if flat
                    else (base_dir + '/tmp')
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
                    else (base_dir + '/data')
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

        base_dir_prefix = local_dir + '/'
        pod_ctx_info = (pod_ctx_info_dict or dict()).get(pod_name)
        result_aux_ctx_info = dict()
        result_aux_info = dict()

        if validate_ctx:
          pod_ctx_file = pod.get('ctx')

          if pod_ctx_file:
            pod_ctx_file_full = (base_dir_prefix + pod_ctx_file) or ''

            if not os.path.exists(pod_ctx_file_full):
              error_msgs_aux += [[str('pod ctx file not found: ' + pod_ctx_file)]]

        all_content_dests = set()
        prepared_transfer = []

        prepare_transfer_info = dict(
            env=env,
            env_data=env_data,
            custom_dir=local_dir,
            run_info=run_info,
            all_content_dests=all_content_dests,
        )

        if pod_ctx_info:
          transfer_contents = pod_ctx_info.get('transfer')

          if transfer_contents:
            info = prepare_transfer_content(
                transfer_contents,
                context_title='prepare pod ctx info transfer contents',
                prepare_info=prepare_transfer_info,
            )

            prepared_transfer_aux = info.get('result')
            error_msgs_aux_transfer = info.get('error_msgs')

            if error_msgs_aux_transfer:
              error_msgs_aux += error_msgs_aux_transfer
            else:
              prepared_transfer += prepared_transfer_aux

        transfer_contents = pod_info_dict.get('transfer')

        if transfer_contents:
          info = prepare_transfer_content(
              transfer_contents,
              context_title='prepare pod info transfer contents',
              prepare_info=prepare_transfer_info,
          )

          prepared_transfer_aux = info.get('result')
          error_msgs_aux_transfer = info.get('error_msgs')

          if error_msgs_aux_transfer:
            error_msgs_aux += error_msgs_aux_transfer
          else:
            prepared_transfer += prepared_transfer_aux

        transfer_contents = pod.get('transfer')

        if transfer_contents:
          info = prepare_transfer_content(
              transfer_contents,
              context_title='prepare pod transfer contents',
              prepare_info=prepare_transfer_info,
          )

          prepared_transfer_aux = info.get('result')
          error_msgs_aux_transfer = info.get('error_msgs')

          if error_msgs_aux_transfer:
            error_msgs_aux += error_msgs_aux_transfer
          else:
            prepared_transfer += prepared_transfer_aux

        if prepared_transfer:
          result['prepared_transfer'] = prepared_transfer

        credentials_info_dict = pod_info_dict.get('credentials')
        credentials_dict = pod.get('credentials')
        credentials_env_dict = env.get('credentials')

        if credentials_info_dict:
          credentials_dict = merge_dicts(
              credentials_dict, credentials_info_dict)

        if pod_ctx_info:
          credentials_ctx_info_dict = pod_ctx_info.get('credentials')

          if credentials_ctx_info_dict:
            credentials_dict = merge_dicts(
                credentials_dict, credentials_ctx_info_dict)

        params_args = dict(
            group_params=credentials_dict,
            group_params_dict=credentials_env_dict,
        )

        info = mix(params_args)

        result_aux_credentials = info.get('result')
        error_msgs_aux_credentials = info.get('error_msgs') or list()

        for value in (error_msgs_aux_credentials or []):
          new_value = ['context: pod credentials'] + value
          error_msgs_aux += [new_value]

        if not error_msgs_aux_credentials:
          credentials = result_aux_credentials
          result['credentials'] = credentials or None

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
          error_msgs_aux_ctx_info = info.get('error_msgs') or list()

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
          error_msgs_aux_info = info.get('error_msgs') or list()

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
        error_msgs_aux_pod = info.get('error_msgs') or list()

        for value in (error_msgs_aux_pod or []):
          new_value = ['context: pod params'] + value
          error_msgs_aux_params += [new_value]

        error_msgs_aux += error_msgs_aux_params

        if not error_msgs_aux_params:
          pod_params = merge_dicts(
              result_aux_pod, result_aux_info, result_aux_ctx_info)
          result['params'] = pod_params or None

        contents = pod.get('contents')
        prepared_contents = dict()

        contents_info = pod_info_dict.get('contents')

        if contents_info:
          contents = merge_dicts(contents, contents_info)

        contents_ctx_info = (pod_ctx_info or dict()).get('contents')

        if contents_ctx_info:
          contents = merge_dicts(contents, contents_ctx_info)

        for content_key in sorted(list((contents or dict()).keys())):
          content = contents.get(content_key)

          info = load_content(
              content,
              env=env,
              custom_dir=local_dir,
              run_info=run_info,
          )

          prepared_content = info.get('result')
          error_msgs_aux_content = info.get('error_msgs') or list()

          for value in (error_msgs_aux_content or []):
            new_value = [str('pod content: ' + content_key)] + value
            error_msgs_aux += [new_value]

          if not error_msgs_aux_content:
            prepared_contents[content_key] = prepared_content

        result['contents'] = prepared_contents or None

        if validate_ctx and not error_msgs_aux:
          schema_file = pod.get('schema')

          if schema_file:
            schema_file = base_dir_prefix + schema_file

          if schema_file:
            if os.path.exists(schema_file):
              schema = load_cached_file(schema_file)

              schema_data = dict()

              for key in ['params', 'credentials', 'contents']:
                if result.get(key) is not None:
                  schema_data[key] = result.get(key)

              error_msgs_aux_validate = validate_schema(
                  schema, schema_data
              )

              for value in (error_msgs_aux_validate or []):
                new_value = [
                    'context: validate pod schema',
                    str('schema file: ' + schema_file),
                ] + value
                error_msgs_aux += [new_value]
            else:
              error_msgs_aux += [[
                  'context: validate pod schema',
                  str('msg: schema file not found: ' + schema_file),
              ]]

        if validate_ctx and not error_msgs_aux:
          try:
            result_info = load_vars(
                pod_info=dict(
                    pod=result,
                    dependencies=dependencies,
                ),
                run_info=run_info,
                meta_info=dict(no_ctx_msg=True),
            )

            error_msgs_validate = result_info.get('error_msgs') or list()

            if error_msgs_validate:
              error_msgs_aux += error_msgs_validate
          except Exception as error:
            error_msgs_validate = [[
                'msg: error when trying to load pod vars',
                'error type: ' + str(type(error)),
                'error details: ',
                traceback.format_exc(),
            ]]
            error_msgs_aux += error_msgs_validate

        for value in (error_msgs_aux or []):
          new_value = [str('pod: ' + pod_description)] + value
          error_msgs += [new_value]

      result_keys = list(result.keys())

      for key in result_keys:
        if result.get(key) is None:
          result.pop(key, None)

      return dict(result=result, error_msgs=error_msgs)
    except Exception as error:
      error_msgs = [[
          str('pod: ' + pod_description),
          'msg: error when trying to prepare pod',
          'error type: ' + str(type(error)),
          'error details:',
          traceback.format_exc(),
      ]]
      return dict(error_msgs=error_msgs)
  except Exception as error:
    error_msgs = [[
        'msg: error when trying to prepare unknown pod',
        'error type: ' + str(type(error)),
        'error details:',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_pods(pods, parent_data, run_info):
  try:
    result = []
    error_msgs = []

    pod_names = set()
    env_data = run_info.get('env_data')
    env = env_data.get('env')

    if pods:
      pods_dict = env.get('pods')

      if not pods_dict:
        error_msgs += [['msg: no pod specified for the environment']]
      else:
        for pod_info in pods:
          info = prepare_pod(pod_info, parent_data, run_info)

          result_aux = info.get('result')
          error_msgs_aux = info.get('error_msgs') or list()

          if error_msgs_aux:
            error_msgs += error_msgs_aux
          else:
            pod_name = result_aux.get('name')

            if pod_name in pod_names:
              error_msgs += [[
                  str('pod_name: ' + pod_name),
                  'msg: duplicate pod name',
              ]]
            else:
              pod_names.add(pod_name)
              result += [result_aux]

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs = [[
        'msg: error when trying to prepare pods',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_node(node_info, run_info):
  try:
    result = dict()
    error_msgs = []

    env_data = run_info.get('env_data')
    validate_ctx = run_info.get('validate')

    env = env_data.get('env')

    node_info_dict = node_info if isinstance(node_info, dict) else dict()

    node_name = default(node_info_dict.get('name'), node_info)
    node_key = default(node_info_dict.get('key'), node_name)
    node_description = (
        (node_name + ' (' + node_key + ')')
        if node_name != node_key
        else node_name
    )

    if not node_name:
      error_msgs += [['msg: node name not specified']]
      return dict(result=result, error_msgs=error_msgs)
    elif node_name == 'main':
      error_msgs += [[
          str('node: ' + node_description),
          'msg: the node name value, which will correspond to the ansible group, '
          + 'is "main", which is a reserved group for the local host; please, choose '
          + 'other name'
      ]]
      return dict(result=result, error_msgs=error_msgs)

    result['name'] = node_name
    result['key'] = node_key
    result['description'] = node_description

    try:
      nodes_dict = env.get('nodes')

      if node_key not in nodes_dict:
        error_msgs += [[
            str('node: ' + node_description),
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
        local = to_bool(node_info_dict.get('local') or False)
        result['local'] = local
        external = to_bool(node_info_dict.get('external'))
        result['external'] = external

        ctx_dir = env_data.get('ctx_dir')
        secrets_ctx_dir = env_data.get('secrets_ctx_dir')

        result_aux_info = dict()
        error_msgs_aux = []

        if not local:
          required_props = ['base_dir']

          for key in required_props:
            if is_empty(node.get(key)):
              error_msgs += [[
                  str('node: ' + node_description),
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
                  str('node: ' + node_description),
                  'property: ' + key,
                  'msg: required property not found in node '
                  + 'or is empty (non-local and non-external)'
              ]]

        if local and not env_data.get('dev'):
          error_msgs += [[
              str('node: ' + node_description),
              'msg: local node should be defined only in development environments'
          ]]

        local_dir = ctx_dir + '/nodes/' + node_name
        result['local_dir'] = local_dir
        local_secrets_dir = secrets_ctx_dir + '/nodes/' + node_name
        result['local_secrets_dir'] = local_secrets_dir

        node_identifier = env.get('name') + '-' + env_data.get('ctx_name')
        result['identifier'] = node_identifier

        dev_repos_dir = env_data.get('dev_repos_dir')

        base_dir = None if local else node.get('base_dir')
        node_dir = local_dir if local else (
            node.get('node_dir') or (base_dir + '/.node'))
        local_tmp_dir = dev_repos_dir + '/tmp/nodes/' + node_identifier
        tmp_dir = (
            local_tmp_dir
            if local
            else (node.get('tmp_dir') or (base_dir + '/.tmp'))
        )

        result['root'] = to_bool(node.get('root'))
        result['base_dir'] = base_dir
        result['node_dir'] = node_dir
        result['local_tmp_dir'] = local_tmp_dir
        result['tmp_dir'] = tmp_dir
        result['local_host_test'] = to_bool(
            node_info_dict.get('local_host_test'))
        result['local_host_test_error'] = node_info_dict.get(
            'local_host_test_error')

        instance_amount = int(node_info_dict.get('amount') or 1)
        instance_max_amount = int(
            node_info_dict.get('max_amount') or instance_amount)
        dependencies = node_info_dict.get('dependencies')

        result['amount'] = instance_amount
        result['max_amount'] = instance_max_amount
        result['dependencies'] = dependencies

        credential = node.get('credential')

        credential_info = node_info_dict.get('credential')
        credential = node.get('credential')
        credentials_env_dict = env.get('credentials')

        if credential_info:
          credential = credential_info

        if credential:
          params_args = dict(
              group_params=dict(credential=credential),
              group_params_dict=credentials_env_dict,
          )

          info = mix(params_args)

          result_aux_credential = info.get('result')
          error_msgs_aux_credential = info.get('error_msgs') or list()

          for value in (error_msgs_aux_credential or []):
            new_value = ['context: node credential'] + value
            error_msgs_aux += [new_value]

          if not error_msgs_aux_credential:
            credential = result_aux_credential.get('credential')
            result['credential'] = credential

        error_msgs_aux_params = []

        all_content_dests = set()
        prepared_transfer = []

        prepare_transfer_info = dict(
            env=env,
            env_data=env_data,
            run_info=run_info,
            all_content_dests=all_content_dests,
        )

        transfer_contents = node_info_dict.get('transfer')

        if transfer_contents:
          info = prepare_transfer_content(
              transfer_contents,
              context_title='prepare node info transfer contents',
              prepare_info=prepare_transfer_info,
          )

          prepared_transfer_aux = info.get('result')
          error_msgs_aux_transfer = info.get('error_msgs')

          if error_msgs_aux_transfer:
            error_msgs_aux += error_msgs_aux_transfer
          else:
            prepared_transfer += prepared_transfer_aux

        transfer_contents = node.get('transfer')

        if transfer_contents:
          info = prepare_transfer_content(
              transfer_contents,
              context_title='prepare node transfer contents',
              prepare_info=prepare_transfer_info,
          )

          prepared_transfer_aux = info.get('result')
          error_msgs_aux_transfer = info.get('error_msgs')

          if error_msgs_aux_transfer:
            error_msgs_aux += error_msgs_aux_transfer
          else:
            prepared_transfer += prepared_transfer_aux

        if prepared_transfer:
          result['prepared_transfer'] = prepared_transfer

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
          error_msgs_aux_info = info.get('error_msgs') or list()

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
        error_msgs_aux_node = info.get('error_msgs') or list()

        for value in (error_msgs_aux_node or []):
          new_value = ['context: node params'] + value
          error_msgs_aux_params += [new_value]

        error_msgs_aux += error_msgs_aux_params
        node_params = None

        if not error_msgs_aux_params:
          node_params = merge_dicts(result_aux_node, result_aux_info)
          result['params'] = node_params or None

        if validate_ctx and not error_msgs_aux:
          schema_file = 'schemas/node.schema.yml'

          if schema_file:
            if os.path.exists(schema_file):
              schema = load_cached_file(schema_file)

              schema_data = dict()

              for key in ['params', 'credential']:
                if result.get(key) is not None:
                  schema_data[key] = result.get(key)

              error_msgs_aux_validate = validate_schema(
                  schema, schema_data
              )

              for value in (error_msgs_aux_validate or []):
                new_value = [
                    'context: validate node schema',
                    str('schema file: ' + schema_file),
                ] + value
                error_msgs_aux += [new_value]

              if (not error_msgs_aux_validate) and (not local):
                required_props = ['host_test']

                for key in required_props:
                  if is_empty(node_params.get(key)):
                    error_msgs += [[
                        str('node: ' + node_description),
                        str('property: ' + key),
                        'context: validate node params (custom)',
                        'msg: required property not found in node params or is empty (non-local)'
                    ]]
            else:
              error_msgs_aux += [[
                  'context: validate node schema',
                  str('msg: schema file not found: ' + schema_file),
              ]]

        if node_params:
          cron = node_params.get('cron')

          if cron:
            info = prepare_transfer_content(
                cron,
                context_title='prepare the node cron transfer contents',
                prepare_info=prepare_transfer_info,
            )

            cron_transfer = info.get('result')
            error_msgs_aux_transfer = info.get('error_msgs')

            if error_msgs_aux_transfer:
              error_msgs_aux += error_msgs_aux_transfer
            else:
              result['cron_transfer'] = cron_transfer

        credential = result.get('credential') or dict()
        ssh_file = credential.get('ssh_file')
        ssh_key_path = (
            (local_secrets_dir + '/' + node_name + '.key')
            if ssh_file
            else None
        )
        result['ssh_key_path'] = ssh_key_path

        service = node.get('service')
        dns_service = node.get('dns_service')
        dns_service_params_list = node_params.get('dns_service_params_list')

        if not service:
          if dns_service:
            error_msgs += [[
                str('node: ' + node_description),
                'msg: dns_service is defined, but service is undefined'
            ]]

          if dns_service_params_list:
            error_msgs += [[
                str('node: ' + node_description),
                'msg: dns_service_params_list is defined with records, but service is undefined'
            ]]
        else:
          replicas = []

          if instance_amount > instance_max_amount:
            error_msgs += [[
                str('node: ' + node_description),
                str('amount: ' + str(instance_amount)),
                str('max_amount: ' + str(instance_max_amount)),
                'msg: the node replica amount is higher than the node max_amount'
            ]]
          elif instance_amount < 0:
            error_msgs += [[
                str('node: ' + node_description),
                str('amount: ' + str(instance_amount)),
                'msg: the node replica amount is less than 0'
            ]]

          hostname = node_info_dict.get('hostname')

          if hostname and (hostname == node_name):
            error_msgs += [[
                str('node: ' + node_description),
                'msg: the node hostname should be different than the node name'
            ]]

          active_hosts = []
          all_hosts = []

          if instance_max_amount > 0:
            for idx in range(1, instance_max_amount + 1):
              name_suffix = ('-' + str(idx)) if idx > 1 else ''
              absent = None if (idx <= instance_amount) else True
              real_hostname = (hostname or (node_name + '-host')) + name_suffix
              real_hostname = real_hostname.replace('_', '-')
              replica = dict(
                  name=real_hostname,
                  absent=absent,
              )
              replicas += [replica]

              all_hosts += [real_hostname]

              if not absent:
                active_hosts += [real_hostname]

            result['active_hosts'] = active_hosts
            result['all_hosts'] = all_hosts

            service_info = dict(
                name=service,
                single=True,
                params=dict(replicas=replicas)
            )

            info = prepare_service(service_info, run_info=run_info, top=True)

            prepared_service = info.get('result')
            error_msgs_aux_services = info.get('error_msgs') or list()

            if error_msgs_aux_services:
              for value in error_msgs_aux_services:
                new_value = ['context: prepare node service'] + value
                error_msgs_aux += [new_value]
            else:
              result['prepared_service'] = prepared_service

          if not dns_service:
            if dns_service_params_list:
              error_msgs += [[
                  str('node: ' + node_description),
                  'msg: dns records defined (dns_service_params_list), but dns_service is undefined'
              ]]
          elif dns_service_params_list and (instance_amount > 1):
            error_msgs += [[
                str('node: ' + node_description),
                'msg: dns service with records defined (dns_service_params_list) '
                + 'for node with more than 1 replica'
            ]]
          elif dns_service_params_list:
            services_info = []

            for idx, dns_service_params in enumerate(dns_service_params_list, start=1):
              for dns_type_name in ['ipv4', 'ipv6']:
                name_suffix = (
                    '-' + dns_type_name
                    + (('-' + str(idx)) if idx > 1 else '')
                )
                service_info = dict(
                    name=dns_service + name_suffix,
                    key=dns_service,
                    can_destroy=to_bool(dns_service_params.get('can_destroy')),
                    params=dict(
                        record=dns_service_params.get('record'),
                        ttl=dns_service_params.get('ttl'),
                        dns_type='A' if dns_type_name == 'ipv4' else 'AAAA',
                    )
                )
                services_info += [service_info]

            if services_info:
              result['prepared_dns_services'] = list(services_info)

              if validate_ctx:
                info = prepare_services(
                    services_info, run_info=run_info, top=True
                )
                error_msgs_aux_service = info.get('error_msgs') or list()

                for value in (error_msgs_aux_service or []):
                  new_value = ['context: node dns service'] + value
                  error_msgs_aux += [new_value]

        pods = node.get('pods')
        pod_ctx_info_dict = node_info_dict.get('pods')

        if pods:
          dependencies_names = sorted(list((dependencies or dict()).keys()))
          original_dependencies = dependencies
          dependencies = dict()

          for dependency_name in dependencies_names:
            dependency = original_dependencies.get(dependency_name)

            if dependency.get('type') != 'node':
              dependencies[dependency_name] = dependency
            else:
              required_amount = int(dependency.get('required_amount') or 0)
              amount = required_amount if (required_amount > 0) else 1
              host_ip = '127.0.0.1'
              host_list = [host_ip for v in range(amount)]
              dependencies[dependency_name] = dict(
                  original_type='ip',
                  host=host_ip,
                  host_list=host_list,
              )

          node_data = dict(
              pod_ctx_info_dict=pod_ctx_info_dict,
              local=local,
              base_dir=base_dir,
              parent_type='node',
              parent_description=node_description,
              dependencies=dependencies,
          )
          info = prepare_pods(pods, node_data, run_info)

          prepared_pods = info.get('result')
          error_msgs_aux_pods = info.get('error_msgs') or list()

          if error_msgs_aux_pods:
            error_msgs_aux += error_msgs_aux_pods
          else:
            pod_names = set()

            for pod in (prepared_pods or []):
              pod_names.add(pod.get('name'))

            pod_ctx_info_keys = sorted(
                list((pod_ctx_info_dict or dict()).keys()))

            for pod_ctx_info_key in pod_ctx_info_keys:
              if pod_ctx_info_key not in pod_names:
                error_msgs_aux += [[
                    str('pod: ' + pod_ctx_info_key),
                    'msg: pod defined in the context for the node info,'
                    + ' but the node doesn\'t have a pod with such name',
                    'node pods: ',
                    sorted(list(pod_names)),
                ]]

            if node_dir in pod_names:
              error_msgs_aux += [[
                  str('node_dir: ' + node_dir),
                  'msg: there is a pod with the same name as the node directory',
              ]]

            result['pods'] = prepared_pods

        for value in (error_msgs_aux or []):
          new_value = [str('node: ' + node_description)] + value
          error_msgs += [new_value]

      result_keys = list(result.keys())

      for key in result_keys:
        if result.get(key) is None:
          result.pop(key, None)

      return dict(result=result, error_msgs=error_msgs)
    except Exception as error:
      error_msgs = [[
          str('node: ' + node_description),
          'msg: error when trying to prepare node',
          'error type: ' + str(type(error)),
          'error details: ',
          traceback.format_exc(),
      ]]
      return dict(error_msgs=error_msgs)
  except Exception as error:
    error_msgs = [[
        'msg: error when trying to prepare unknown node',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_nodes(nodes, run_info):
  result = []
  error_msgs = []

  node_names = set()
  env_data = run_info.get('env_data')
  env = env_data.get('env')

  if nodes:
    nodes_dict = env.get('nodes')

    if not nodes_dict:
      error_msgs += [['msg: no node specified for the environment']]
    else:
      for node_info in nodes:
        info = prepare_node(node_info, run_info)

        result_aux = info.get('result')
        error_msgs_aux = info.get('error_msgs') or list()

        if error_msgs_aux:
          error_msgs += error_msgs_aux
        else:
          node_name = result_aux.get('name')

          if node_name in node_names:
            error_msgs += [[
                str('node_name: ' + node_name),
                'msg: duplicate node name',
            ]]
          else:
            node_names.add(node_name)
            result += [result_aux]

  return dict(result=result, error_msgs=error_msgs)


def prepare_task(task_info_dict, run_info):
  try:
    result = dict()
    error_msgs = []

    env_data = run_info.get('env_data')
    validate_ctx = run_info.get('validate')

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
          str('task: ' + task_description),
          'msg: no task specified for the environment'
      ]]
      return dict(result=result, error_msgs=error_msgs)

    task = tasks_dict.get(task_key)

    if task is None:
      error_msgs += [[
          str('task: ' + task_description),
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

    try:
      valid_task_types = ['skip', 'task', 'shell']

      if task_type not in valid_task_types:
        error_msgs_aux += [[
            str('task_type: ' + task_type),
            'msg: invalid task type',
            'valid task types:',
            valid_task_types,
        ]]
      elif task_type != 'skip':
        allowed_props_map = dict(
            task=list([
                'type',
                'target_origin',
                'file',
                'root',
                'schema',
                'credentials',
                'contents',
                'params',
                'group_params',
                'shared_params',
                'shared_group_params',
            ]),
            shell=list(['type', 'cmd', 'root', 'poll']),
        )

        allowed_props = allowed_props_map.get(task_type)

        for key in sorted(list(task.keys())):
          if key not in allowed_props:
            error_msgs_aux += [[
                str('task_type: ' + task_type),
                str('property: ' + key),
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
                str('task_type: ' + task_type),
                str('property: ' + key),
                'msg: required property not specified',
            ]]
          elif not task.get(key):
            error_msgs_aux += [[
                str('task_type: ' + task_type),
                str('property: ' + key),
                'msg: required property is empty',
            ]]

      credentials_info_dict = task_info_dict.get('credentials')
      credentials_dict = task.get('credentials')
      credentials_env_dict = env.get('credentials')

      if credentials_info_dict:
        credentials_dict = merge_dicts(
            credentials_dict, credentials_info_dict)

      params_args = dict(
          group_params=credentials_dict,
          group_params_dict=credentials_env_dict,
      )

      info = mix(params_args)

      result_aux_credentials = info.get('result')
      error_msgs_aux_credentials = info.get('error_msgs') or list()

      for value in (error_msgs_aux_credentials or []):
        new_value = ['context: task credentials'] + value
        error_msgs_aux += [new_value]

      if not error_msgs_aux_credentials:
        if task_type != 'task':
          if result_aux_credentials:
            error_msgs_aux += [[
                str('task_type: ' + task_type),
                'msg: task type has no support for task credentials',
            ]]

        credentials = result_aux_credentials
        result['credentials'] = credentials or None

      error_msgs_aux_params = []
      result_aux_info = None

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
        error_msgs_aux_info = info.get('error_msgs') or list()

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
      error_msgs_aux_task = info.get('error_msgs') or list()

      for value in (error_msgs_aux_task or []):
        new_value = ['context: task params'] + value
        error_msgs_aux_params += [new_value]

      error_msgs_aux += error_msgs_aux_params

      if not error_msgs_aux_params:
        if task_type != 'task':
          if result_aux_info:
            error_msgs_aux += [[
                str('task_type: ' + task_type),
                'msg: task type has no support for task parameters (overwrite)',
            ]]

          if result_aux_task:
            error_msgs_aux += [[
                str(str),
                'msg: task type has no support for task parameters',
            ]]

        task_params = merge_dicts(result_aux_task, result_aux_info)
        result['params'] = task_params or None

      contents = task.get('contents')
      prepared_contents = dict()

      contents_info = task_info_dict.get('contents')

      if contents_info:
        contents = merge_dicts(contents, contents_info)

      for content_key in sorted(list((contents or dict()).keys())):
        content = contents.get(content_key)

        info = load_content(content, env=env, run_info=run_info)

        prepared_content = info.get('result')
        error_msgs_aux_content = info.get('error_msgs') or list()

        for value in (error_msgs_aux_content or []):
          new_value = [str('task content: ' + content_key)] + value
          error_msgs_aux += [new_value]

        if not error_msgs_aux_content:
          prepared_contents[content_key] = prepared_content

      result['contents'] = prepared_contents or None

      schema_file = task.get('schema')
      result['schema'] = schema_file

      if validate_ctx and task_target_origin in ['cloud', 'env']:
        if schema_file:
          schema_file_full = (
              schema_file
              if (task_target_origin == 'cloud')
              else env_data.get('env_dir') + '/' + schema_file
          ) or ''

          if os.path.exists(schema_file_full):
            schema = load_cached_file(schema_file_full)

            schema_data = dict()

            for key in ['params', 'credentials', 'contents']:
              if result.get(key) is not None:
                schema_data[key] = result.get(key)

            error_msgs_aux_validate = validate_schema(schema, schema_data)

            for value in (error_msgs_aux_validate or []):
              new_value = [
                  'context: validate task schema',
                  str('schema file: ' + schema_file_full),
              ] + value
              error_msgs_aux += [new_value]
          else:
            error_msgs_aux += [[
                'context: validate task schema',
                str('target_origin: ' + task_target_origin),
                str('msg: params schema file not found: ' + schema_file),
            ]]

      for value in (error_msgs_aux or []):
        new_value = [str('task: ' + task_description)] + value
        error_msgs += [new_value]

      result_keys = list(result.keys())

      for key in result_keys:
        if result.get(key) is None:
          result.pop(key, None)

      return dict(result=result, error_msgs=error_msgs)
    except Exception as error:
      error_msgs = [[
          str('task: ' + task_description),
          'msg: error when trying to prepare task',
          'error type: ' + str(type(error)),
          'error details: ',
          traceback.format_exc(),
      ]]
      return dict(error_msgs=error_msgs)
  except Exception as error:
    error_msgs = [[
        'msg: error when trying to prepare unknown task',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_run_stage_task(run_stage_task_info, run_stage_data):
  try:
    result = dict()
    error_msgs = []

    default_task_name = run_stage_data.get('default_task_name')
    prepared_nodes = run_stage_data.get('prepared_nodes')
    run_info = run_stage_data.get('run_info')

    env_data = run_info.get('env_data')
    validate_ctx = run_info.get('validate')

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
            str('run_stage_task: ' + run_stage_task_name),
            'msg: no run stage task specified for the environment'
        ]]
        return dict(result=result, error_msgs=error_msgs)

      run_stage_task = run_stage_tasks_dict.get(run_stage_task_name)

      if run_stage_task is None:
        error_msgs += [[
            str('run_stage_task: ' + run_stage_task_name),
            'msg: run stage task not specified for the environment'
        ]]
        return dict(result=result, error_msgs=error_msgs)

    result['name'] = run_stage_task_name

    try:
      task_name = run_stage_task.get('name') or ''

      if not task_name:
        error_msgs += [[
            str('run_stage_task: ' + run_stage_task_name),
            'msg: task name relative to the run stage task not specified'
        ]]

      task_target = run_stage_task.get('task_target') or ''
      result['task_target'] = task_target

      if not task_target:
        error_msgs += [[
            str('run_stage_task: ' + run_stage_task_name),
            str('task_name: ' + task_name),
            'msg: task target not specified'
        ]]

      all_nodes = []
      node_map = dict()
      node_pod_map = dict()

      for node in (prepared_nodes or []):
        node_name = node.get('name')

        pods_aux = []
        pod_map = dict()

        if task_target == 'pod':
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
      node_info_list = run_stage_task.get('nodes')
      nodes_to_run = []

      if (not is_all_nodes) and (node_info_list is None):
        error_msgs += [[
            str('run_stage_task: ' + run_stage_task_name),
            str('task_name: ' + task_name),
            'msg: all_nodes must be true or nodes must be defined',
        ]]
      elif (is_all_nodes is not None) and (node_info_list is not None):
        error_msgs += [[
            str('run_stage_task: ' + run_stage_task_name),
            str('task_name: ' + task_name),
            'msg: nodes and all_nodes specified for the task (specify only one)',
        ]]
      elif is_all_nodes:
        nodes_to_run = all_nodes
      else:
        for node_info in (node_info_list or []):
          node_name = (
              node_info.get('name')
              if isinstance(node_info, dict)
              else node_info
          )

          node = node_map.get(node_name)

          if not node:
            error_msgs += [[
                str('run_stage_task: ' + run_stage_task_name),
                str('task_name: ' + task_name),
                str('node_name: ' + node_name),
                'msg: node not found in the environment',
            ]]
          elif is_str(node_info):
            nodes_to_run += [node]
          else:
            all_pods = node_info.get('all_pods')
            pods_names = node_info.get('pods')

            if (not all_pods) and (pods_names is None):
              error_msgs += [[
                  str('run_stage_task: ' + run_stage_task_name),
                  str('task_name: ' + task_name),
                  str('node_name: ' + node_name),
                  'msg: all_pods must be true or pods must be defined',
              ]]
            elif (all_pods is not None) and (pods_names is not None):
              error_msgs += [[
                  str('run_stage_task: ' + run_stage_task_name),
                  str('task_name: ' + task_name),
                  str('node_name: ' + node_name),
                  'msg: pods and all_pods specified for the node (specify only one)',
              ]]
            elif all_pods:
              nodes_to_run += [node]
            else:
              all_node_pods_names = map(
                  lambda p: p.get('name'), node.get('pods') or []
              )

              for pod_name in (pods_names or []):
                if pod_name not in all_node_pods_names:
                  error_msgs += [[
                      str('run_stage_task: ' + run_stage_task_name),
                      str('task_name: ' + task_name),
                      str('node_name: ' + node_name),
                      str('pod_name: ' + pod_name),
                      'msg: pod specified for the node task, but not specified in the node itself',
                  ]]

              pod_map = node_pod_map.get(node_name)
              pods_to_add = [pod_map.get(pod_name) for pod_name in pods_names]

              node_to_add = node.copy()
              node_to_add['pods'] = pods_to_add
              nodes_to_run += [node_to_add]

      result['nodes'] = nodes_to_run

      if task_name:
        result['task_name'] = task_name

        info = prepare_task(run_stage_task, run_info=run_info)

        result_aux = info.get('result')
        error_msgs_aux = info.get('error_msgs') or list()

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
              ) or ''

              if not os.path.exists(task_file_full):
                error_msgs_aux += [[str('msg: task file not found: ' + task_file)]]
            else:
              task_file_paths = set()

              if task_target == 'node':
                error_msgs_aux += [
                    [str('msg: node task with pod target_origin: ' + task_file)]
                ]

              for node in nodes_to_run:
                for pod in node.get('pods'):
                  pod_local_dir = pod.get('local_dir')
                  error_msgs_aux_pod = []

                  schema_file = task.get('schema')

                  if schema_file:
                    schema_file_full = pod_local_dir + '/' + schema_file

                    if os.path.exists(schema_file_full):
                      schema = load_cached_file(schema_file_full)

                      schema_data = dict()

                      for key in ['params', 'credentials', 'contents']:
                        if task.get(key) is not None:
                          schema_data[key] = task.get(key)

                      error_msgs_aux_validate = validate_schema(
                          schema, schema_data
                      )

                      for value in (error_msgs_aux_validate or []):
                        new_value = [
                            'context: validate pod task schema',
                            str('schema file: ' + schema_file_full),
                        ] + value
                        error_msgs_aux_pod += [new_value]
                    else:
                      error_msgs_aux_pod += [[
                          'context: validate pod task schema',
                          str('msg: schema file not found: ' + schema_file_full),
                      ]]

                  task_file_path = pod_local_dir + '/' + task_file

                  if task_file_path not in task_file_paths:
                    if not os.path.exists(task_file_path):
                      error_msgs_aux_pod += [[
                          str('msg: pod task file not found: ' + task_file),
                      ]]

                    task_file_paths.add(task_file_path)

                  for value in error_msgs_aux_pod:
                    new_value = [
                        str('node_name: ' + node_name),
                        str('pod_name: ' + pod_name),
                    ] + value
                    error_msgs_aux += [new_value]

            for value in error_msgs_aux:
              new_value = [
                  str('run_stage_task: ' + run_stage_task_name),
                  str('task: ' + task_description),
                  str('task_type: ' + task_type),
                  str('task_target_origin: ' + task_target_origin),
              ] + value
              error_msgs += [new_value]

          result['task'] = task

      result_keys = list(result.keys())

      for key in result_keys:
        if result.get(key) is None:
          result.pop(key, None)

      return dict(result=result, error_msgs=error_msgs)
    except Exception as error:
      error_msgs = [[
          str('run stage task: ' + run_stage_task_name),
          'msg: error when trying to prepare run stage task',
          'error type: ' + str(type(error)),
          'error details: ',
          traceback.format_exc(),
      ]]
      return dict(error_msgs=error_msgs)
  except Exception as error:
    error_msgs = [[
        'msg: error when trying to prepare unknown run stage task',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_run_stage(run_stage_info, default_name, prepared_nodes, run_info):
  try:
    result = dict()
    error_msgs = []

    env_data = run_info.get('env_data')
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
            str('run_stage: ' + run_stage_name),
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
            str('run_stage: ' + run_stage_name),
            'msg: no run stage specified for the environment'
        ]]
        return dict(result=result, error_msgs=error_msgs)

      run_stage_tasks_input = run_stages_dict.get(run_stage_name)

      if run_stage_tasks_input is None:
        error_msgs += [[
            str('run_stage: ' + run_stage_name),
            'msg: run stage not specified for the environment'
        ]]
        return dict(result=result, error_msgs=error_msgs)

    result['name'] = run_stage_name

    try:
      hosts = set()
      run_stage_tasks = []
      run_stage_task_names = set()
      task_names = set()

      for idx, run_stage_task in enumerate(run_stage_tasks_input or []):
        default_task_name = str(idx + 1)
        run_stage_data = dict(
            default_task_name=default_task_name,
            prepared_nodes=prepared_nodes,
            run_info=run_info,
        )
        info = prepare_run_stage_task(
            run_stage_task,
            run_stage_data,
        )

        result_aux = info.get('result')
        error_msgs_aux = info.get('error_msgs') or list()

        if error_msgs_aux:
          for value in (error_msgs_aux or []):
            new_value = ['run_stage: ' + run_stage_name] + value
            error_msgs += [new_value]
        else:
          run_stage_task = result_aux
          run_stage_task_name = run_stage_task.get('name')

          if run_stage_task_name in run_stage_task_names:
            error_msgs += [[
                str('run_stage: ' + run_stage_name),
                str('run_stage_task: ' + run_stage_task_name),
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
                  str('run_stage: ' + run_stage_name),
                  str('run_stage_task: ' + run_stage_task_name),
                  str('task_name: ' + task_name),
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
    except Exception as error:
      error_msgs = [[
          str('run stage: ' + run_stage_name),
          'msg: error when trying to prepare run stage',
          'error type: ' + str(type(error)),
          'error details: ',
          traceback.format_exc(),
      ]]
      return dict(error_msgs=error_msgs)
  except Exception as error:
    error_msgs = [[
        'msg: error when trying to prepare unknown run stage',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_run_stages(run_stages, prepared_nodes, run_info):
  try:
    result = []
    error_msgs = []

    for idx, run_stage_info in enumerate(run_stages or []):
      default_name = str(idx + 1)
      info = prepare_run_stage(
          run_stage_info,
          default_name=default_name,
          prepared_nodes=prepared_nodes,
          run_info=run_info,
      )

      result_aux = info.get('result')
      error_msgs_aux = info.get('error_msgs') or list()

      if error_msgs_aux:
        error_msgs += error_msgs_aux
      else:
        result += [result_aux]

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs = [[
        'msg: error when trying to prepare run stages',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_ctx(ctx_name, run_info):
  try:
    result = dict()
    error_msgs = []

    env_data = run_info.get('env_data')

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
        result['cfg'] = ctx.get('cfg')
        result['hosts'] = ctx.get('hosts')

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
                str('msg: repository not found: ' + env_repo.get('repo')),
            ]]

        hooks = ctx.get('hooks')

        if hooks:
          for key in sorted(list(hooks.keys())):
            hook_file = hooks.get(key) or ''

            if not os.path.exists(hook_file):
              error_msgs += [[
                  'context: validate ctx hooks',
                  str('hook: ' + key),
                  str('hook file: ' + hook_file),
                  'msg: hook file not found',
              ]]

        result['hooks'] = hooks

        ctx_initial_services = ctx.get('initial_services')

        if ctx_initial_services:
          info = prepare_services(
              ctx_initial_services,
              run_info=run_info,
              top=True,
          )

          result_aux = info.get('result')
          error_msgs_aux = info.get('error_msgs') or list()

          for value in (error_msgs_aux or []):
            new_value = ['service context: initial services'] + value
            error_msgs += [new_value]

          if not error_msgs_aux:
            result['prepared_initial_services'] = result_aux

        ctx_nodes = ctx.get('nodes')
        prepared_nodes = []
        nodes_errors = []

        if ctx_nodes:
          info = prepare_nodes(ctx_nodes, run_info)

          result_aux = info.get('result')
          error_msgs_aux = info.get('error_msgs') or list()

          if error_msgs_aux:
            nodes_errors = error_msgs_aux
            error_msgs += error_msgs_aux
          else:
            prepared_nodes = result_aux
            result['nodes'] = prepared_nodes

            if prepared_nodes:
              all_hosts_dict = dict()

              for prepared_node in prepared_nodes:
                node_description = prepared_node.get('description')

                for host in (prepared_node.get('all_hosts') or []):
                  if host in all_hosts_dict.keys():
                    previous_node_description = all_hosts_dict[host]

                    error_msgs += [[
                        str('node1: ' + str(previous_node_description)),
                        str('node2: ' + str(node_description)),
                        str('host: ' + str(host)),
                        'msg: there are 2 hosts with the same name in different nodes',
                    ]]
                  else:
                    all_hosts_dict[host] = node_description

              node_names = []
              prepared_node_dict = dict()

              for prepared_node in prepared_nodes:
                node_name = prepared_node.get('name')
                node_names += [node_name]
                prepared_node_dict[node_name] = prepared_node

              info = prepare_node_dependencies(
                  node_names, prepared_node_dict
              )

              node_dependencies = info.get('result')
              error_msgs_aux = info.get('error_msgs') or list()

              if error_msgs_aux:
                nodes_errors = error_msgs_aux

                for value in error_msgs_aux:
                  new_value = ['context: prepare node dependencies'] + value
                  error_msgs += [new_value]
              else:
                result['node_dependencies'] = node_dependencies

                for node_name in sorted(list(node_dependencies.keys() or {})):
                  single_node_dependencies_info = node_dependencies.get(
                      node_name)
                  dependencies = single_node_dependencies_info.get(
                      'dependencies'
                  )
                  dependencies_type_node_amount = len(filter(
                      lambda d: d.get('type') == 'node',
                      dependencies.values()
                  ))
                  has_node_dependency = dependencies_type_node_amount > 0
                  result['has_node_dependency'] = has_node_dependency

                  env_meta = env.get('meta') or dict()
                  no_node_type_dependency = env_meta.get(
                      'no_node_type_dependency'
                  )

                  if has_node_dependency and no_node_type_dependency:
                    error_msgs += [[
                        str('node name: ' + str(node_name)),
                        'context: node dependencies (node type forbidden)',
                        str(
                            'msg: there are ' +
                            str(dependencies_type_node_amount)
                            + ' node dependencies with type "node", but this type'
                            + ' is forbidden due to the environment meta flag'
                            + ' "no_node_type_dependency"'),
                    ]]

        ctx_final_services = ctx.get('final_services')

        if ctx_final_services:
          info = prepare_services(
              ctx_final_services,
              run_info=run_info,
              top=True,
          )

          result_aux = info.get('result')
          error_msgs_aux = info.get('error_msgs') or list()

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
                run_stages,
                prepared_nodes=prepared_nodes,
                run_info=run_info,
            )

            result_aux = info.get('result')
            error_msgs_aux = info.get('error_msgs') or list()

            if error_msgs_aux:
              error_msgs += error_msgs_aux
            else:
              result['run_stages'] = result_aux

    result_keys = list(result.keys())

    for key in result_keys:
      if result.get(key) is None:
        result.pop(key, None)

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs = [[
        'ctx_name: ' + str(ctx_name),
        'msg: error when trying to prepare the context',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)
