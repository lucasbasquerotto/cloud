#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=import-error
# pylint: disable=broad-except

from __future__ import absolute_import, division, print_function
__metaclass__ = type  # pylint: disable=invalid-name

import os

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import (
    is_str, load_file, load_schema, merge_dicts
)
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_params_mixer import mix
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_schema import validate_schema
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_template import lookup


def load_content(content, env, custom_dir, run_info):
  try:
    env_data = run_info.get('env_data')
    validate = run_info.get('validate')

    result = None

    info = prepare_content(
        content,
        env=env,
        custom_dir=custom_dir,
        env_data=env_data,
        validate=validate,
    )

    prepared_content = info.get('result')
    error_msgs_aux = info.get('error_msgs') or list()

    if not error_msgs_aux:
      content_type = prepared_content.get('type')

      if content_type == 'str':
        params = prepared_content.get('params')
        result = params.get('value')
      elif content_type == 'file':
        content_file = prepared_content.get('file')
        result = load_file(content_file)
      elif content_type == 'template':
        plugin = run_info.get('plugin')
        ansible_vars = run_info.get('ansible_vars')

        content_file = prepared_content.get('file')
        params = prepared_content.get('params')
        credentials = prepared_content.get('credentials')

        result = lookup(
            plugin,
            ansible_vars,
            content_file,
            dict(params=params, credentials=credentials),
        )
      else:
        error_msgs_aux = [[
            str('type: ' + str(type(content))),
            'msg: invalid prepared content type',
        ]]

    error_msgs = list()

    for value in (error_msgs_aux or []):
      new_value = ['context: load content'] + value
      error_msgs += [new_value]

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs = [[
        'msg: error when trying to load the content',
        'error type: ' + str(type(error)),
        'error details: ' + str(error),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_content(content, env, custom_dir, env_data, validate, content_names=None):
  try:
    if env is None:
      error_msgs = [['msg: environment variable not specified']]
      return dict(error_msgs=error_msgs)
    elif not isinstance(env, dict):
      error_msgs = [[
          str('env type: ' + str(type(env))),
          'msg: environment variable is not a dictionary',
      ]]
      return dict(error_msgs=error_msgs)

    if content is None:
      error_msgs = [['msg: content not specified']]
      return dict(error_msgs=error_msgs)
    elif is_str(content):
      result = dict(
          type='str',
          params=dict(value=content)
      )
      return dict(result=result)
    elif isinstance(content, dict):
      result = dict()
      error_msgs_aux = list()

      content_type = content.get('type')

      if content_type == 'env':
        allowed_props = [
            'type',
            'name',
            'key',
            'params',
            'group_params',
            'shared_params',
            'shared_group_params',
        ]
        required_props = [
            'type',
            'name',
        ]
      elif content_type == 'str':
        allowed_props = [
            'type',
            'params',
            'group_params',
            'shared_params',
            'shared_group_params',
        ]
        required_props = ['type']
      elif content_type == 'template':
        allowed_props = [
            'type',
            'origin',
            'file',
            'params_schema',
            'credentials_schema',
            'credentials',
            'params',
            'group_params',
            'shared_params',
            'shared_group_params',
        ]
        required_props = [
            'type',
            'file',
        ]
      else:
        content_type = 'file'
        allowed_props = [
            'type',
            'origin',
            'file',
        ]
        required_props = ['file']

      for prop in sorted(list(content.keys())):
        if prop not in allowed_props:
          error_msgs_aux += [[
              str('property: ' + prop),
              'msg: invalid property defined for the content',
              'allowed: ',
              allowed_props,
          ]]

      for prop in sorted(required_props):
        if not content.get(prop):
          error_msgs_aux += [[
              str('property: ' + prop),
              'msg: required property not defined for the content or empty',
          ]]

      if not error_msgs_aux:
        content_origin = content.get('origin') or 'custom'
        allowed_origins = ['env', 'cloud', 'custom']

        if content_origin not in allowed_origins:
          error_msgs_aux += [[
              str('content origin: ' + content_origin),
              'msg: invalid content origin',
              'allowed:',
              allowed_origins,
          ]]

      if not error_msgs_aux:
        origin_dir_map = dict(
            cloud='',
            env=env_data.get('env_dir'),
            custom=custom_dir or '',
        )

        base_dir = origin_dir_map.get(content_origin)
        base_dir_prefix = (base_dir + '/') if base_dir else base_dir

        result['type'] = content_type

        if content_type == 'template':
          params_args = dict(
              group_params=content.get('credentials'),
              group_params_dict=env.get('credentials'),
          )

          info = mix(params_args)

          credentials = info.get('result')
          error_msgs_aux_credentials = info.get('error_msgs') or list()

          for value in (error_msgs_aux_credentials or []):
            new_value = ['context: content credentials'] + value
            error_msgs_aux += [new_value]

          if not error_msgs_aux_credentials:
            result['credentials'] = credentials

            if validate:
              schema_file = content.get('credentials_schema')

              if schema_file:
                schema_file = base_dir_prefix + schema_file

                if os.path.exists(schema_file):
                  schema = load_schema(schema_file)
                  error_msgs_aux_validate = validate_schema(
                      schema, credentials
                  )

                  for value in (error_msgs_aux_validate or []):
                    new_value = [
                        'context: validate content credentials'
                    ] + value
                    error_msgs_aux += [new_value]
                else:
                  error_msgs_aux += [[
                      'context: validate content credentials',
                      str('msg: content schema file not found: ' + schema_file),
                  ]]

        if content_type in ['env', 'str', 'template']:
          params_args = dict(
              params=content.get('params'),
              group_params=content.get('group_params'),
              shared_params=content.get('shared_params'),
              shared_group_params=content.get('shared_group_params'),
              shared_group_params_dict=env.get('content_shared_group_params'),
              shared_params_dict=env.get('content_shared_params'),
              group_params_dict=env.get('content_group_params'),
          )

          info = mix(params_args)

          content_params = info.get('result')
          error_msgs_aux_params = info.get('error_msgs') or list()

          for value in (error_msgs_aux_params or []):
            new_value = ['context: content params'] + value
            error_msgs_aux += [new_value]

          if not error_msgs_aux_params:
            result['params'] = content_params

            if validate:
              schema_file = content.get('params_schema')

              if content_type == 'str':
                schema_file = 'schemas/content_params_str.yml'

              if schema_file:
                schema_file = base_dir_prefix + schema_file

                if os.path.exists(schema_file):
                  schema = load_schema(schema_file)
                  error_msgs_aux_validate = validate_schema(
                      schema, content_params
                  )

                  for value in (error_msgs_aux_validate or []):
                    new_value = ['context: validate content params'] + value
                    error_msgs_aux += [new_value]
                else:
                  error_msgs_aux += [[
                      'context: validate content params',
                      str('msg: params schema file not found: ' + schema_file),
                  ]]

        if content_type in ['file', 'template']:
          file_rel = content.get('file')
          file_path = base_dir_prefix + file_rel
          result['file'] = file_path

          if validate and (not os.path.exists(file_path)):
            error_msgs_aux += [[
                str('content origin: ' + content_origin),
                str('msg: content file not found: ' + file_rel),
            ]]

      error_msgs = list()

      for value in (error_msgs_aux or []):
        new_value = [str('content type: ' + content_type)] + value
        error_msgs += [new_value]

      if (content_type == 'env') and not error_msgs:
        content_name = content.get('name')
        content_key = content.get('key') or content_name
        content_description = (
            (content_name + ' (' + content_key + ')')
            if content_name != content_key
            else content_name
        )

        content_names = content_names or set()

        if content_name in content_names:
          error_msgs_aux += [['msg: content env with duplicate name']]

        if not error_msgs_aux:
          content_names.add(content_name)
          contents = env.get('contents')

          if not contents:
            error_msgs_aux += [['msg: no content specified for the environment']]
          elif not contents.get(content_key):
            error_msgs_aux += [['msg: the content is not specified for the environment']]
          else:
            child_content = contents.get(content_key)
            params = result['params']

            try:
              info = prepare_content(
                  child_content,
                  env=env,
                  custom_dir=custom_dir,
                  env_data=env_data,
                  validate=validate,
                  content_names=content_names,
              )

              result = info.get('result')
              error_msgs_aux += info.get('error_msgs') or list()
            except Exception as error:
              error_msgs_aux += [[
                  'msg: error when trying to prepare the content child (env type)',
                  'error type: ' + str(type(error)),
                  'error details: ' + str(error),
              ]]

            if params and not error_msgs_aux:
              child_content_type = result.get('type')

              if child_content_type != 'template':
                error_msgs_aux += [[str(
                    'msg: the parent content [' + content_description + '] '
                    + 'has parameters specified but the resulting child '
                    + 'is not a template (' + child_content_type + ')'
                )]]
              else:
                result_content_params = merge_dicts(
                    result.get('params'), params
                )
                result['params'] = result_content_params

        for value in (error_msgs_aux or []):
          new_value = [str('content: ' + content_description)] + value
          error_msgs += [new_value]

      if error_msgs:
        result = None
      else:
        result_keys = list(result.keys())

        for key in result_keys:
          if result.get(key) is None:
            result.pop(key, None)

      return dict(result=result, error_msgs=error_msgs)
    else:
      error_msgs = [[
          str('type: ' + str(type(content))),
          'msg: invalid content type',
      ]]
      return dict(error_msgs=error_msgs)
  except Exception as error:
    error_msgs = [[
        'msg: error when trying to prepare the content',
        'error type: ' + str(type(error)),
        'error details: ' + str(error),
    ]]
    return dict(error_msgs=error_msgs)
