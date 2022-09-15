#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=import-error
# pylint: disable=too-many-lines
# pylint: disable=broad-except

# pyright: reportUnusedImport=true
# pyright: reportUnusedVariable=true
# pyright: reportMissingImports=false

from __future__ import absolute_import, division, print_function
__metaclass__ = type  # pylint: disable=invalid-name

import traceback

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import merge_dicts
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_content import load_content
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_params_mixer import mix


def prepare_mixed_data(context_full_info, params_dicts, run_info):
  result = dict()
  error_msgs = []

  try:
    ### Credentials ###

    info = prepare_mixed_credentials(context_full_info, run_info)

    result_aux = info.get('result') or dict()
    error_msgs_aux = info.get('error_msgs') or list()

    for value in (error_msgs_aux or []):
      new_value = ['context: mixed data (credentials)'] + value
      error_msgs += [new_value]

    if not error_msgs_aux:
      result['credentials'] = result_aux.get('credentials') or None

    ### Params ###

    info = prepare_mixed_params(context_full_info, params_dicts, run_info)

    result_aux = info.get('result')
    error_msgs_aux = info.get('error_msgs') or list()

    for value in (error_msgs_aux or []):
      new_value = ['context: mixed data (params)'] + value
      error_msgs += [new_value]

    if not error_msgs_aux:
      result['params'] = result_aux.get('params') or None

    ### Contents ###

    info = prepare_mixed_loaded_contents(context_full_info, run_info)

    result_aux = info.get('result')
    error_msgs_aux = info.get('error_msgs') or list()

    for value in (error_msgs_aux or []):
      new_value = ['context: mixed data (contents)'] + value
      error_msgs += [new_value]

    if not error_msgs_aux:
      result['contents'] = result_aux.get('contents') or None
      result['validators'] = result_aux.get('validators') or None

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        'msg: error when trying to prepare mixed data',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_mixed_credentials(context_full_info, run_info):
  result = dict()
  error_msgs = []

  try:
    context_data = context_full_info.get('data')
    context_info = context_full_info.get('info')
    context_ctx_info = context_full_info.get('ctx_info')

    env_data = run_info.get('env_data')
    services_data = run_info.get('services_data')

    env = env_data.get('env')

    ### Credentials ###

    result_aux_ctx_info = None
    result_aux_info = None
    error_msgs_aux = []

    credentials_dict = context_data.get('credentials')
    dynamic_credentials_dict = context_data.get('dynamic_credentials')
    credentials_env_dict = env.get('credentials')

    ### Credentials - Ctx Info ###

    if context_ctx_info:
      credentials_ctx_info_dict = context_ctx_info.get('credentials')
      dynamic_credentials_ctx_info_dict = context_ctx_info.get(
          'dynamic_credentials'
      )

      dynamic_credentials_info = dict()

      for credential_key in (dynamic_credentials_ctx_info_dict or dict()):
        if credentials_ctx_info_dict.get(credential_key):
          error_msgs_aux += [[
              'context: duplicate credential ctx info key',
              'credential_key: ' + credential_key,
              'msg: duplicate credential key '
              + '(defined both in credentials and dynamic_credentials)',
          ]]
        else:
          service_info = dynamic_credentials_ctx_info_dict.get(credential_key)
          service_name = service_info
          service_credential_name = credential_key

          if isinstance(service_info, dict):
            service_name = service_info.get('name')
            service_credential_name = service_info.get(
                'credential'
            ) or credential_key

          service_inner_data = services_data.get(service_name) or dict()
          service_data_credentials = service_inner_data.get(
              'credentials'
          ) or dict()
          credential_value = service_data_credentials.get(
              service_credential_name
          )

          if credential_value is not None:
            dynamic_credentials_info[credential_key] = credential_value

      params_args = dict(
          params=dynamic_credentials_info,
          group_params=credentials_ctx_info_dict,
          group_params_dict=credentials_env_dict,
      )

      info = mix(params_args)

      result_aux_ctx_info = info.get('result')
      error_msgs_aux_ctx_info = info.get('error_msgs') or list()

      for value in (error_msgs_aux_ctx_info or []):
        new_value = ['context: ctx info params'] + value
        error_msgs_aux += [new_value]

    ### Credentials - Info ###

    if isinstance(context_info, dict):
      credentials_info_dict = context_info.get('credentials')
      dynamic_credentials_info_dict = context_info.get(
          'dynamic_credentials'
      )

      dynamic_credentials_info = dict()

      for credential_key in (dynamic_credentials_info_dict or dict()):
        if credentials_info_dict.get(credential_key):
          error_msgs_aux += [[
              'context: duplicate credential info key',
              'credential_key: ' + credential_key,
              'msg: duplicate credential key '
              + '(defined both in credentials and dynamic_credentials)',
          ]]
        else:
          service_info = dynamic_credentials_info_dict.get(credential_key)
          service_name = service_info
          service_credential_name = credential_key

          if isinstance(service_info, dict):
            service_name = service_info.get('name')
            service_credential_name = service_info.get(
                'credential'
            ) or credential_key

          service_inner_data = services_data.get(service_name) or dict()
          service_data_credentials = service_inner_data.get(
              'credentials'
          ) or dict()
          credential_value = service_data_credentials.get(
              service_credential_name
          )

          if credential_value is not None:
            dynamic_credentials_info[credential_key] = credential_value

      params_args = dict(
          params=dynamic_credentials_info,
          group_params=credentials_info_dict,
          group_params_dict=credentials_env_dict,
      )

      info = mix(params_args)

      result_aux_info = info.get('result')
      error_msgs_aux_info = info.get('error_msgs') or list()

      for value in (error_msgs_aux_info or []):
        new_value = ['context: info credentials'] + value
        error_msgs_aux += [new_value]

    ### Credentials - Main ###

    dynamic_credentials_data = dict()

    for credential_key in (dynamic_credentials_dict or dict()):
      if credentials_dict.get(credential_key):
        error_msgs_aux += [[
            'context: duplicate credential key',
            'credential_key: ' + credential_key,
            'msg: duplicate credential key '
            + '(defined both in credentials and dynamic_credentials)',
        ]]
      else:
        service_info = dynamic_credentials_dict.get(credential_key)
        service_name = service_info
        service_credential_name = credential_key

        if isinstance(service_info, dict):
          service_name = service_info.get('name')
          service_credential_name = service_info.get(
              'credential'
          ) or credential_key

        service_inner_data = services_data.get(service_name) or dict()
        service_data_credentials = service_inner_data.get(
            'credentials'
        ) or dict()
        credential_value = service_data_credentials.get(
            service_credential_name
        )

        if credential_value is not None:
          dynamic_credentials_data[credential_key] = credential_value

    params_args = dict(
        params=dynamic_credentials_data,
        group_params=credentials_dict,
        group_params_dict=credentials_env_dict,
    )

    info = mix(params_args)

    result_aux = info.get('result')
    error_msgs_aux += info.get('error_msgs') or list()

    for value in error_msgs_aux:
      new_value = ['context: credentials'] + value
      error_msgs += [new_value]

    if not error_msgs:
      credentials = merge_dicts(
          result_aux, result_aux_info, result_aux_ctx_info
      )
      result['credentials'] = credentials or None

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        'msg: error when trying to prepare mixed credentials',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_mixed_params(context_full_info, params_dicts, run_info):
  result = dict()
  error_msgs = []

  try:
    context_data = context_full_info.get('data')
    context_info = context_full_info.get('info')
    context_ctx_info = context_full_info.get('ctx_info')

    shared_group_params_dict = params_dicts.get('shared_group_params_dict')
    shared_params_dict = params_dicts.get('shared_params_dict')
    group_params_dict = params_dicts.get('group_params_dict')

    services_data = run_info.get('services_data')

    ### Params ###

    result_aux_ctx_info = None
    result_aux_info = None
    error_msgs_aux = []

    params_dict = context_data.get('params')
    dynamic_params_dict = context_data.get('dynamic_params')

    ### Params - Ctx Info ###

    if context_ctx_info:
      params_ctx_info_dict = context_ctx_info.get('params')
      dynamic_params_ctx_info_dict = context_ctx_info.get(
          'dynamic_params'
      )

      dynamic_params_info = dict()

      for param_key in (dynamic_params_ctx_info_dict or dict()):
        if params_ctx_info_dict.get(param_key):
          error_msgs_aux += [[
              'context: duplicate param ctx info key',
              'param_key: ' + param_key,
              'msg: duplicate param key '
              + '(defined both in params and dynamic_params)',
          ]]
        else:
          service_info = dynamic_params_ctx_info_dict.get(param_key)
          service_name = service_info
          service_param_name = param_key

          if isinstance(service_info, dict):
            service_name = service_info.get('name')
            service_param_name = service_info.get(
                'param'
            ) or param_key

          service_inner_data = services_data.get(service_name) or dict()
          service_data_params = service_inner_data.get(
              'params'
          ) or dict()
          param_value = service_data_params.get(
              service_param_name
          )

          if param_value is not None:
            dynamic_params_info[param_key] = param_value

      params_args = dict(
          params=merge_dicts(dynamic_params_info, params_ctx_info_dict),
          group_params=context_ctx_info.get('group_params'),
          shared_params=context_ctx_info.get('shared_params'),
          shared_group_params=context_ctx_info.get('shared_group_params'),
          shared_group_params_dict=shared_group_params_dict,
          shared_params_dict=shared_params_dict,
          group_params_dict=group_params_dict,
      )

      info = mix(params_args)

      result_aux_ctx_info = info.get('result')
      error_msgs_aux_ctx_info = info.get('error_msgs') or list()

      for value in (error_msgs_aux_ctx_info or []):
        new_value = ['context: ctx info params'] + value
        error_msgs_aux += [new_value]

    ### Params - Info ###

    if isinstance(context_info, dict):
      params_info_dict = context_info.get('params')
      dynamic_params_info_dict = context_info.get(
          'dynamic_params'
      )

      dynamic_params_info = dict()

      for param_key in (dynamic_params_info_dict or dict()):
        if params_info_dict.get(param_key):
          error_msgs_aux += [[
              'context: duplicate param info key',
              'param_key: ' + param_key,
              'msg: duplicate param key '
              + '(defined both in params and dynamic_params)',
          ]]
        else:
          service_info = dynamic_params_info_dict.get(param_key)
          service_name = service_info
          service_param_name = param_key

          if isinstance(service_info, dict):
            service_name = service_info.get('name')
            service_param_name = service_info.get(
                'param'
            ) or param_key

          service_inner_data = services_data.get(service_name) or dict()
          service_data_params = service_inner_data.get(
              'params'
          ) or dict()
          param_value = service_data_params.get(
              service_param_name
          )

          if param_value is not None:
            dynamic_params_info[param_key] = param_value

      params_args = dict(
          params=merge_dicts(dynamic_params_info, params_info_dict),
          group_params=context_info.get('group_params'),
          shared_params=context_info.get('shared_params'),
          shared_group_params=context_info.get(
              'shared_group_params'
          ),
          shared_group_params_dict=shared_group_params_dict,
          shared_params_dict=shared_params_dict,
          group_params_dict=group_params_dict,
      )

      info = mix(params_args)

      result_aux_info = info.get('result')
      error_msgs_aux_info = info.get('error_msgs') or list()

      for value in (error_msgs_aux_info or []):
        new_value = ['context: service info params'] + value
        error_msgs_aux += [new_value]

    ### Params - Main ###

    dynamic_params = dict()

    for param_key in (dynamic_params_dict or dict()):
      if params_dict.get(param_key):
        error_msgs_aux += [[
            'context: duplicate param info key',
            'param_key: ' + param_key,
            'msg: duplicate param key '
            + '(defined both in params and dynamic_params)',
        ]]
      else:
        service_info = dynamic_params_dict.get(param_key)
        service_name = service_info
        service_param_name = param_key

        if isinstance(service_info, dict):
          service_name = service_info.get('name')
          service_param_name = service_info.get(
              'param'
          ) or param_key

        service_inner_data = services_data.get(service_name) or dict()
        service_data_params = service_inner_data.get(
            'params'
        ) or dict()
        param_value = service_data_params.get(
            service_param_name
        )

        if param_value is not None:
          dynamic_params[param_key] = param_value

    params_args = dict(
        params=merge_dicts(dynamic_params, params_dict),
        group_params=context_data.get('group_params'),
        shared_params=context_data.get('shared_params'),
        shared_group_params=context_data.get('shared_group_params'),
        shared_group_params_dict=shared_group_params_dict,
        shared_params_dict=shared_params_dict,
        group_params_dict=group_params_dict,
    )

    info = mix(params_args)

    result_aux = info.get('result')
    error_msgs_aux += info.get('error_msgs') or list()

    for value in error_msgs_aux:
      new_value = ['context: params'] + value
      error_msgs += [new_value]

    if not error_msgs:
      params = merge_dicts(result_aux, result_aux_info, result_aux_ctx_info)
      result['params'] = params or None

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        'msg: error when trying to prepare mixed params',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_mixed_loaded_contents(context_full_info, run_info):
  result = dict()
  error_msgs = []

  try:
    env_data = run_info.get('env_data')

    env = env_data.get('env')

    info = prepare_mixed_contents(context_full_info, run_info)

    error_msgs_aux = info.get('error_msgs')
    contents = info.get('contents')

    validators = list()
    prepared_contents = dict()

    for content_key in sorted(list((contents or dict()).keys())):
      content = contents.get(content_key)

      info = load_content(content, env=env, run_info=run_info)

      prepared_content = info.get('result')
      meta = info.get('meta') or dict()
      validators = meta.get('validators') or []
      validators += validators
      error_msgs_aux_content = info.get('error_msgs') or list()

      for value in (error_msgs_aux_content or []):
        new_value = [str('content: ' + content_key)] + value
        error_msgs_aux += [new_value]

      if not error_msgs_aux_content:
        prepared_contents[content_key] = prepared_content

    for value in error_msgs_aux:
      new_value = ['context: load contents'] + value
      error_msgs += [new_value]

    if not error_msgs:
      result['contents'] = prepared_contents or None
      result['validators'] = validators or None

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        'msg: error when trying to prepare mixed loaded contents',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_mixed_contents(context_full_info, run_info):
  result = dict()
  error_msgs = []

  try:
    context_data = context_full_info.get('data')
    context_info = context_full_info.get('info')
    context_ctx_info = context_full_info.get('ctx_info')

    services_data = run_info.get('services_data')

    ### Contents ###

    result_aux_ctx_info = None
    result_aux_info = None
    error_msgs_aux = []

    contents_dict = context_data.get('contents')
    dynamic_contents_dict = context_data.get('dynamic_contents')

    ### Contents - Ctx Info ###

    if context_ctx_info:
      contents_ctx_info_dict = context_ctx_info.get('contents')
      dynamic_contents_ctx_info_dict = context_ctx_info.get(
          'dynamic_contents'
      )

      dynamic_contents_info = dict()

      for content_key in (dynamic_contents_ctx_info_dict or dict()):
        if contents_ctx_info_dict.get(content_key):
          error_msgs_aux += [[
              'context: duplicate content ctx info key',
              'content_key: ' + content_key,
              'msg: duplicate content key '
              + '(defined both in contents and dynamic_contents)',
          ]]
        else:
          service_info = dynamic_contents_ctx_info_dict.get(content_key)
          service_name = service_info
          service_content_name = content_key

          if isinstance(service_info, dict):
            service_name = service_info.get('name')
            service_content_name = service_info.get(
                'content'
            ) or content_key

          service_inner_data = services_data.get(service_name) or dict()
          service_data_contents = service_inner_data.get(
              'contents'
          ) or dict()
          content_value = service_data_contents.get(
              service_content_name
          )

          if content_value is not None:
            dynamic_contents_info[content_key] = dict(
                type='str',
                params=dict(value=content_value)
            )

      result_aux_ctx_info = merge_dicts(
          dynamic_contents_info, contents_ctx_info_dict)

    ### Contents - Info ###

    if isinstance(context_info, dict):
      contents_info_dict = context_info.get('contents')
      dynamic_contents_info_dict = context_info.get(
          'dynamic_contents'
      )

      dynamic_contents_info = dict()

      for content_key in (dynamic_contents_info_dict or dict()):
        if contents_info_dict.get('content_key'):
          error_msgs_aux += [[
              'context: duplicate content info key',
              'content_key: ' + content_key,
              'msg: duplicate content key '
              + '(defined both in contents and dynamic_contents)',
          ]]
        else:
          service_info = dynamic_contents_info_dict.get(content_key)
          service_name = service_info
          service_content_name = content_key

          if isinstance(service_info, dict):
            service_name = service_info.get('name')
            service_content_name = service_info.get(
                'content'
            ) or content_key

          service_inner_data = services_data.get(service_name) or dict()
          service_data_contents = service_inner_data.get(
              'contents'
          ) or dict()
          content_value = service_data_contents.get(
              service_content_name
          )

          if content_value is not None:
            dynamic_contents_info[content_key] = dict(
                type='str',
                params=dict(value=content_value)
            )

      result_aux_info = merge_dicts(dynamic_contents_info, contents_info_dict)

    ### Contents - Main ###

    dynamic_contents = dict()

    for content_key in (dynamic_contents_dict or dict()):
      if contents_dict.get(content_key):
        error_msgs_aux += [[
            'context: duplicate content info key',
            'content_key: ' + content_key,
            'msg: duplicate content key '
            + '(defined both in contents and dynamic_contents)',
        ]]
      else:
        service_info = dynamic_contents_dict.get(content_key)
        service_name = service_info
        service_content_name = content_key

        if isinstance(service_info, dict):
          service_name = service_info.get('name')
          service_content_name = service_info.get(
              'content'
          ) or content_key

        service_inner_data = services_data.get(service_name) or dict()
        service_data_contents = service_inner_data.get(
            'contents'
        ) or dict()
        content_value = service_data_contents.get(
            service_content_name
        )

        if content_value is not None:
          dynamic_contents[content_key] = dict(
              type='str',
              params=dict(value=content_value)
          )

    result_aux = merge_dicts(dynamic_contents, contents_dict)

    contents = merge_dicts(result_aux, result_aux_info, result_aux_ctx_info)

    for value in error_msgs_aux:
      new_value = ['context: contents'] + value
      error_msgs += [new_value]

    if not error_msgs:
      result['contents'] = contents or None

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        'msg: error when trying to prepare mixed contents',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)
