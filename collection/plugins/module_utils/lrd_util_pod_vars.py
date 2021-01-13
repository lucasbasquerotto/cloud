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
import traceback

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import (
    load_cached_file, load_yaml, to_bool
)
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_schema import validate_schema
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_template import lookup


def load_vars(pod_info, run_info, meta_info=None):
  try:
    pod = pod_info.get('pod')
    dependencies_data = pod_info.get(
        'dependencies_data',
        dict(list=list(), node_ip_dict=dict(), node_ips_dict=dict()),
    )

    plugin = run_info.get('plugin')
    ansible_vars = run_info.get('ansible_vars')
    env_data = run_info.get('env_data')
    validate = run_info.get('validate')

    meta_info = meta_info or dict()
    no_ctx_msg = meta_info.get('no_ctx_msg')

    result = None
    error_msgs = []

    pod_ctx_file = pod.get('ctx') or ''

    if not pod_ctx_file:
      result = dict(
          directories=list(),
          files=list(),
          templates=list(),
      )
      return dict(result=result)

    params = dict(
        identifier=pod.get('identifier'),
        env_name=env_data.get('env').get('name'),
        ctx_name=env_data.get('ctx_name'),
        pod_name=pod.get('name'),
        local=pod.get('local'),
        dev=env_data.get('dev'),
        lax=env_data.get('lax'),
        main=pod.get('params', {}),
        credentials=pod.get('credentials', {}),
        contents=pod.get('contents', {}),
        data_dir=pod.get('data_dir'),
        extra_repos_dir_relpath=pod.get('extra_repos_dir_relpath'),
        dependencies_data=dependencies_data,
    )

    previous = dict(
        dir_names=set(),
        file_names=set(),
    )

    data_info = dict(
        plugin=plugin,
        ansible_vars=ansible_vars,
        env_data=env_data,
        pod=pod,
        previous=previous,
        validate=validate,
    )

    res = load_next_vars(
        file_relpath=pod_ctx_file,
        params=params,
        data_info=data_info,
    )

    error_msgs_aux = res.get('error_msgs') or list()

    if error_msgs_aux:
      parent_type = pod.get('parent_type')
      parent_description = pod.get('parent_description')
      pod_description = pod.get('description')

      for value in error_msgs_aux:
        new_value = ['context: pod ctx vars'] + value

        if not no_ctx_msg:
          new_value = [
              str((parent_type or '') + ': ' + (parent_description or '')),
              str('pod: ' + pod_description),
          ] + new_value

        error_msgs += [new_value]
    else:
      result = res.get('result')

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs = [[
        'msg: error when trying to load the pod ctx vars',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)


def load_ctx_file(current_file, is_env, data_info):
  try:
    directories = list()
    files = list()
    error_msgs = list()

    pod = data_info.get('pod')
    env_data = data_info.get('env_data')
    previous = data_info.get('previous')
    validate = data_info.get('validate')

    pod_dir = pod.get('pod_dir')
    pod_local_dir = pod.get('local_dir')

    dir_names = previous.get('dir_names')
    file_names = previous.get('file_names')

    env_dir = env_data.get('env_dir')
    env_lax = env_data.get('lax')
    default_dir_mode = 777 if env_lax else 751
    default_file_mode = 666 if env_lax else 640
    default_file_executable_mode = default_dir_mode

    when = current_file.get('when')

    if to_bool(when if (when is not None) else True):
      src_relpath = current_file.get('src')
      src = (env_dir if is_env else pod_dir) + '/' + src_relpath
      local_src = src if is_env else (pod_local_dir + '/' + src_relpath)

      dest = pod_dir + '/' + current_file.get('dest')
      dest_dir = os.path.dirname(dest)

      if validate and not os.path.exists(local_src):
        error_msgs += [[
            str('src: ' + (src_relpath or '')),
            'msg: pod ctx file not found',
        ]]

      if dest_dir not in dir_names:
        dir_names.add(dest_dir)
        dir_to_add = dict(
            path=dest_dir,
            mode=current_file.get('dir_mode') or default_dir_mode,
        )
        directories += [dir_to_add]

      if dest not in file_names:
        file_names.add(dest)
        file_to_add = dict(
            remote_src=not is_env,
            src=src,
            dest=dest,
            mode=(
                current_file.get('mode')
                or
                (
                    default_file_executable_mode
                    if to_bool(current_file.get('executable'))
                    else default_file_mode
                )
            ),
        )
        files += [file_to_add]
      else:
        error_msgs += [[
            str('src: ' + (src or '')),
            str('dest: ' + (dest or '')),
            'msg: duplicate destination for the pod ctx file',
        ]]

    result = dict(directories=directories, files=files)

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs = [[
        'msg: error when trying to load the pod ctx file',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)


def load_ctx_template(current_template, is_env, data_info):
  try:
    directories = list()
    templates = list()
    error_msgs = list()

    pod = data_info.get('pod')
    env_data = data_info.get('env_data')
    previous = data_info.get('previous')
    validate = data_info.get('validate')

    pod_dir = pod.get('pod_dir')
    pod_local_dir = pod.get('local_dir')
    pod_tmp_dir = pod.get('tmp_dir')

    dir_names = previous.get('dir_names')
    file_names = previous.get('file_names')

    env_dir = env_data.get('env_dir')
    env_lax = env_data.get('lax')
    default_dir_mode = 777 if env_lax else 751
    default_file_mode = 666 if env_lax else 640
    default_file_executable_mode = default_dir_mode

    when = current_template.get('when')

    if to_bool(when if (when is not None) else True):
      src_relpath = current_template.get('src')
      src = (env_dir if is_env else pod_local_dir) + '/' + src_relpath
      local_src = src

      dest_relpath = current_template.get('dest')
      dest = pod_dir + '/' + dest_relpath
      dest_tmp = pod_tmp_dir + '/tpl/' + dest_relpath

      dest_dir = os.path.dirname(dest)
      dest_tmp_dir = os.path.dirname(dest_tmp)

      if validate and not os.path.exists(local_src):
        error_msgs += [[
            str('src: ' + (src_relpath or '')),
            'msg: pod ctx template file not found',
        ]]

      template_params = current_template.get('params') or None

      if validate and not error_msgs:
        schema_file = current_template.get('schema')

        if schema_file:
          schema_file = (env_dir if is_env else pod_local_dir) + \
              '/' + schema_file

          if os.path.exists(schema_file):
            schema = load_cached_file(schema_file)

            error_msgs_aux = validate_schema(schema, template_params)

            for value in (error_msgs_aux or []):
              new_value = [
                  str('src: ' + (src_relpath or '')),
                  'context: validate pod ctx vars template schema',
                  str('schema file: ' + schema_file),
              ] + value
              error_msgs += [new_value]

            if error_msgs:
              return dict(error_msgs=error_msgs)
          else:
            error_msgs += [[
                'context: validate pod ctx vars template schema',
                str('schema file: ' + schema_file),
                str('msg: schema file not found: ' + schema_file),
            ]]
            return dict(error_msgs=error_msgs)

      if dest_dir not in dir_names:
        dir_names.add(dest_dir)
        dir_to_add = dict(
            path=dest_dir,
            mode=current_template.get('dir_mode') or default_dir_mode,
        )
        directories += [dir_to_add]

      if dest_tmp_dir not in dir_names:
        dir_names.add(dest_tmp_dir)
        dir_to_add = dict(
            path=dest_tmp_dir,
            mode=current_template.get('dir_mode') or default_dir_mode,
        )
        directories += [dir_to_add]

      if dest not in file_names:
        file_names.add(dest)
        template_to_add = dict(
            src=src,
            dest=dest,
            dest_tmp=dest_tmp,
            mode=(
                current_template.get('mode')
                or
                (
                    default_file_executable_mode
                    if to_bool(current_template.get('executable'))
                    else default_file_mode
                )
            ),
            params=template_params,
        )
        templates += [template_to_add]
      else:
        error_msgs += [[
            str('src: ' + (src or '')),
            str('dest: ' + (dest or '')),
            'msg: duplicate destination for the pod ctx template',
        ]]

    result = dict(directories=directories, templates=templates)

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs = [[
        'msg: error when trying to load the pod ctx template',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)


def load_next_vars(file_relpath, params, data_info):
  try:
    directories = list()
    files = list()
    templates = list()
    error_msgs = list()

    plugin = data_info.get('plugin')
    ansible_vars = data_info.get('ansible_vars')
    pod = data_info.get('pod')
    validate = data_info.get('validate')

    pod_local_dir = pod.get('local_dir')

    try:
      file = pod_local_dir + '/' + file_relpath

      if validate and not os.path.exists(file):
        error_msgs += [[
            str('file: ' + file_relpath),
            str('pod_local_dir: ' + pod_local_dir),
            'msg: pod ctx file not found in the pod repository',
        ]]
        return dict(error_msgs=error_msgs)

      res_str = None

      try:
        res_str = lookup(plugin, ansible_vars, file, dict(params=params))
      except Exception as error:
        error_msgs += [[
            str('file: ' + file_relpath),
            'msg: error when trying to load the pod ctx file',
            'error type: ' + str(type(error)),
            'error details: ',
            traceback.format_exc(),
        ]]
        return dict(error_msgs=error_msgs)

      res = None

      try:
        res = load_yaml(str(res_str))
      except Exception as error:
        error_msgs += [[
            str('file: ' + (file_relpath or '')),
            'file content type: ' + str(type(res_str)),
            'msg: error when trying to process the pod ctx file',
            'error type: ' + str(type(error)),
            'error details: ',
            traceback.format_exc(),
        ]]
        return dict(error_msgs=error_msgs)

      if res:
        if validate:
          schema_file = 'schemas/pod_ctx.schema.yml'

          if os.path.exists(schema_file):
            schema = load_cached_file(schema_file)

            error_msgs_aux = validate_schema(schema, res)

            for value in (error_msgs_aux or []):
              new_value = [
                  'context: validate pod ctx vars schema',
                  str('schema file: ' + schema_file),
              ] + value
              error_msgs += [new_value]

            if error_msgs:
              return dict(error_msgs=error_msgs)
          else:
            error_msgs += [[
                'context: validate pod ctx vars schema',
                str('msg: schema file not found: ' + schema_file),
            ]]
            return dict(error_msgs=error_msgs)

        res_files = res.get('files')
        res_templates = res.get('templates')
        res_env_files = res.get('env_files')
        res_env_templates = res.get('env_templates')

        for res_file in (res_files or []):
          info = load_ctx_file(res_file, is_env=False, data_info=data_info)

          result_aux = info.get('result')
          error_msgs_aux = info.get('error_msgs')

          if error_msgs_aux:
            for value in error_msgs_aux:
              new_value = ['context: pod ctx file'] + value
              error_msgs += [new_value]
          else:
            directories += result_aux.get('directories') or []
            files += result_aux.get('files') or []

        for res_template in (res_templates or []):
          info = load_ctx_template(
              res_template, is_env=False, data_info=data_info)

          result_aux = info.get('result')
          error_msgs_aux = info.get('error_msgs')

          if error_msgs_aux:
            for value in error_msgs_aux:
              new_value = ['context: pod ctx template'] + value
              error_msgs += [new_value]
          else:
            directories += result_aux.get('directories') or []
            templates += result_aux.get('templates') or []

        for res_env_file in (res_env_files or []):
          info = load_ctx_file(res_env_file, is_env=True, data_info=data_info)

          result_aux = info.get('result')
          error_msgs_aux = info.get('error_msgs')

          if error_msgs_aux:
            for value in error_msgs_aux:
              new_value = ['context: pod ctx env file'] + value
              error_msgs += [new_value]
          else:
            directories += result_aux.get('directories') or []
            files += result_aux.get('files') or []

        for res_env_template in (res_env_templates or []):
          info = load_ctx_template(
              res_env_template, is_env=True, data_info=data_info)

          result_aux = info.get('result')
          error_msgs_aux = info.get('error_msgs')

          if error_msgs_aux:
            for value in error_msgs_aux:
              new_value = ['context: pod ctx env template'] + value
              error_msgs += [new_value]
          else:
            directories += result_aux.get('directories') or []
            templates += result_aux.get('templates') or []

        if not error_msgs:
          children = res.get('children')

          if children:
            for child in children:
              when = child.get('when')

              if to_bool(when if (when is not None) else True):
                child_name = child.get('name')
                child_params = child.get('params')

                res_child = load_next_vars(
                    file_relpath=child_name,
                    params=child_params,
                    data_info=data_info,
                )

                child_error_msgs = res_child.get('error_msgs') or list()

                if child_error_msgs:
                  for value in child_error_msgs:
                    new_value = [str('ctx child: ' + child_name)] + value
                    error_msgs += [new_value]
                else:
                  child_result = res_child.get('result')

                  child_directories = child_result.get('directories')
                  child_files = child_result.get('files')
                  child_templates = child_result.get('templates')

                  if child_directories:
                    directories += child_directories

                  if child_files:
                    files += child_files

                  if child_templates:
                    templates += child_templates
    except Exception as error:
      error_msgs = [[
          str('file: ' + (file_relpath or '')),
          'msg: error when trying to define the pod ctx vars',
          'error type: ' + str(type(error)),
          'error details: ',
          traceback.format_exc(),
      ]]
      return dict(error_msgs=error_msgs)

    result = dict(
        directories=directories,
        files=files,
        templates=templates,
    )

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs = [[
        str('file: ' + (file_relpath or '')),
        'msg: unknown error when trying to define the pod ctx vars',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)
