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
    load_yaml, to_bool
)
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_template import lookup
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_validation import (
    validate_ctx_schema
)


def load_vars(pod_info, run_info, meta_info=None):
  result = None
  error_msgs = list()

  try:
    pod = pod_info.get('pod')
    input_params = pod_info.get('input_params', dict())

    plugin = run_info.get('plugin')
    ansible_vars = run_info.get('ansible_vars')
    env_data = run_info.get('env_data')
    validate = run_info.get('validate')

    meta_info = meta_info or dict()
    no_ctx_msg = meta_info.get('no_ctx_msg')

    pod_ctx_file = pod.get('ctx') or ''
    initial_input = pod.get('initial_input')
    input_params = input_params or initial_input

    if not pod_ctx_file:
      result = dict(
          directories=list(),
          files=list(),
          templates=list(),
      )
      return dict(result=result)

    ctx_params = dict(
        params=pod.get('params', {}),
        credentials=pod.get('credentials', {}),
        contents=pod.get('contents', {}),
        input=input_params,
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
        ctx_params=ctx_params,
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
    error_msgs += [[
        'msg: error when trying to load the pod ctx vars',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)


def load_ctx_file(current_file, is_env, data_info):
  error_msgs = list()

  try:
    directories = list()
    files = list()

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
    error_msgs += [[
        'msg: error when trying to load the pod ctx file',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)


def load_ctx_template(current_template, is_env, data_info):
  error_msgs = list()

  try:
    directories = list()
    templates = list()

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

    env = env_data.get('env')
    env_template_no_empty_lines = (env.get('meta') or dict()).get(
        'template_no_empty_lines'
    )

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

      no_empty_lines = to_bool(
          current_template.get('no_empty_lines'),
          to_bool(env_template_no_empty_lines),
      )

      if validate and not os.path.exists(local_src):
        error_msgs += [[
            str('src: ' + (src_relpath or '')),
            'msg: pod ctx template file not found',
        ]]

      template_params = current_template.get('params') or None

      if validate and not error_msgs:
        error_msgs_aux = list()

        base_dir_prefix = (env_dir if is_env else pod_local_dir) + '/'
        task_data = dict(
            base_dir_prefix=base_dir_prefix,
            dict_to_validate=template_params,
            all_props=True,
        )

        info = validate_ctx_schema(
            ctx_title='validate pod ctx vars template schema',
            schema_files=current_template.get('schema'),
            task_data=task_data,
        )
        error_msgs_aux += (info.get('error_msgs') or [])

        for value in (error_msgs_aux or []):
          new_value = [
              str('src: ' + (src_relpath or '')),
              str('dest: ' + (dest_relpath or '')),
          ] + value
          error_msgs += [new_value]

      if error_msgs:
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
            no_empty_lines=no_empty_lines,
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
    error_msgs += [[
        'msg: error when trying to load the pod ctx template',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)


def load_next_vars(file_relpath, ctx_params, data_info):
  error_msgs = list()

  try:
    directories = list()
    files = list()
    templates = list()

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
        res_str = lookup(plugin, ansible_vars, file, ctx_params)
      except Exception as error:
        error_msgs += [[
            str('file: ' + file_relpath),
            'msg: error when trying to load the pod ctx file',
            'error type: ' + str(type(error)),
            'error details: ',
            traceback.format_exc().split('\n'),
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
            traceback.format_exc().split('\n'),
        ]]
        return dict(error_msgs=error_msgs)

      if res:
        if validate:
          task_data = dict(
              base_dir_prefix=None,
              dict_to_validate=res,
              all_props=True,
          )

          info = validate_ctx_schema(
              ctx_title='validate pod ctx vars schema',
              schema_files=['schemas/pod_ctx.schema.yml'],
              task_data=task_data,
          )
          error_msgs += (info.get('error_msgs') or [])

          if error_msgs:
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
                child_error_msgs = list()

                child_name = child.get('name')
                child_params = child.get('params')

                task_data = dict(
                    base_dir_prefix=pod_local_dir,
                    dict_to_validate=child_params,
                    all_props=True,
                )

                info = validate_ctx_schema(
                    ctx_title='validate pod ctx child vars schema',
                    schema_files=child.get('schema'),
                    task_data=task_data,
                )
                child_error_msgs += (info.get('error_msgs') or [])

                res_child = None

                if not child_error_msgs:
                  res_child = load_next_vars(
                      file_relpath=child_name,
                      ctx_params=child_params,
                      data_info=data_info,
                  )

                  child_error_msgs += res_child.get('error_msgs') or list()

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
      error_msgs += [[
          str('file: ' + (file_relpath or '')),
          'msg: error when trying to define the pod ctx vars',
          'error type: ' + str(type(error)),
          'error details: ',
          traceback.format_exc().split('\n'),
      ]]
      return dict(error_msgs=error_msgs)

    result = dict(
        directories=directories,
        files=files,
        templates=templates,
    )

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        str('file: ' + (file_relpath or '')),
        'msg: unknown error when trying to define the pod ctx vars',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)
