# Copyright: (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
# Copyright: (c) 2012-17, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=wrong-import-position
# pylint: disable=import-error
# pylint: disable=protected-access

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type # pylint: disable=invalid-name

DOCUMENTATION = """
    name: pod_vars
    author: Lucas Basquerotto
    version_added: "2.11"
    short_description: retrieve contents of pod context after templating with Jinja2
    description:
      - Returns a dictionary with a list of directories, another list of files and another list of templates.
    options:
      _terms:
        description: list of pods to template
        default: False
        version_added: '2.11'
        type: bool
      env_data:
        description: Data about the environment.
        version_added: '2.11'
        type: dict
      dependencies_data:
        description: Information about the pod dependencies.
        default: {}
        version_added: '2.11'
        type: dict
      validate:
        description: Specifies if the src files and templates should be validated.
        version_added: '2.11'
        type: bool
"""

RETURN = """
_raw:
   description: file(s) content after templating
   type: dicts
   elements: raw
"""

from copy import deepcopy
import os

import yaml

try:
  from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
  from yaml import Loader, Dumper

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
# from ansible.template import generate_ansible_template_vars, AnsibleEnvironment, USE_JINJA2_NATIVE
from ansible.template import generate_ansible_template_vars, USE_JINJA2_NATIVE
from ansible.utils.display import Display
from ansible.module_utils._text import to_text

if USE_JINJA2_NATIVE:
  from ansible.utils.native_jinja import NativeJinjaText

display = Display()

class LookupModule(LookupBase):

  def run(self, terms, variables, **kwargs):
    env_data = kwargs.get('env_data')
    dependencies_data = kwargs.get(
        'dependencies_data',
        dict(list=list(), node_ip_dict=dict(), node_ips_dict=dict())
    )
    validate = kwargs.get('validate')
    ret = []
    error_msgs = []

    for term in terms:
      pod_ctx_file = term.get('ctx')

      params = dict(
          identifier=term.get('identifier'),
          env_name=env_data.get('env').get('name'),
          ctx_name=env_data.get('ctx_name'),
          pod_name=term.get('name'),
          local=term.get('local'),
          main=term.get('params', {}),
          credentials=term.get('credentials', {}),
          data_dir=term.get('data_dir'),
          extra_repos_dir_relpath=term.get('extra_repos_dir_relpath'),
          dependencies_data=dependencies_data,
      )

      previous = dict(
          dir_names=set(),
          file_names=set(),
      )

      data_info = dict(
          variables=variables,
          env_data=env_data,
          pod=term,
          previous=previous,
          validate=validate,
      )

      res = self.load_vars(
          file_relpath=pod_ctx_file,
          params=params,
          data_info=data_info,
      )

      error_msgs_aux = res.get('error_msgs')

      if error_msgs_aux:
        parent_type = term.get('parent_type')
        parent_description = term.get('parent_description')
        pod_description = term.get('description')

        for value in error_msgs_aux:
          new_value = [
            str(parent_type + ': ' + parent_description),
            str('pod: ' + pod_description),
          ] + value
          error_msgs += [new_value]
      else:
        res_result = res.get('result')
        res_result['count'] = len(terms)
        ret.append(res_result)

    if error_msgs:
      raise AnsibleError(to_text(self.error_text(error_msgs, 'pod_vars')))

    return ret

  def load_vars(self, file_relpath, params, data_info):
    directories = list()
    files = list()
    templates = list()
    error_msgs = list()

    variables = data_info.get('variables')
    env_data = data_info.get('env_data')
    pod = data_info.get('pod')
    previous = data_info.get('previous')
    validate = data_info.get('validate')

    pod_dir = pod.get('pod_dir')
    pod_local_dir = pod.get('local_dir')
    pod_tmp_dir = pod.get('tmp_dir')

    dir_names = previous.get('dir_names')
    file_names = previous.get('file_names')

    env_lax = env_data.get('lax')
    default_dir_mode = 777 if env_lax else 751
    default_file_mode = 666 if env_lax else 640

    env_dir = env_data.get('env_dir')

    file = pod_dir + '/' + file_relpath

    if validate and not os.path.exists(file):
      error_msgs += [[
          str('file: ' + file_relpath),
          'msg: pod ctx file not found in the pod repository',
      ]]
      return dict(error_msgs=error_msgs)

    try:
      res_str = self.lookup(variables, file, params)
    except Exception as error: # pylint: disable=broad-except
      error_msgs += [[
          str('file: ' + file_relpath),
          'msg: error when trying to load the pod ctx file',
          'error type: ' + str(type(error)),
          'error details: ' + str(error),
      ]]
      return dict(error_msgs=error_msgs)


    res = yaml.load(res_str, Loader=Loader)

    if res:
      res_files = res.get('files')
      res_templates = res.get('templates')
      res_env_files = res.get('env_files')
      res_env_templates = res.get('env_templates')

      for res_file in (res_files or []):
        src_relpath = res_file.get('src')
        src = pod_dir + '/' + src_relpath
        local_src = pod_local_dir + '/' + src_relpath

        dest = pod_dir + '/' + res_file.get('dest')
        dest_dir = os.path.dirname(dest)

        if validate and not os.path.exists(local_src):
          error_msgs += [[
              str('src: ' + src_relpath),
              'msg: file not found in the pod repository',
          ]]

        if dest_dir not in dir_names:
          dir_names.add(dest_dir)
          dir_to_add = dict(
              path=dest_dir,
              mode=res_file.get('dir_mode') or default_dir_mode,
          )
          directories += [dir_to_add]

        if dest not in file_names:
          file_names.add(dest)
          file_to_add = dict(
              remote_src=True,
              src=src,
              dest=dest,
              mode=res_file.get('mode') or default_file_mode,
          )
          files += [file_to_add]
        else:
          error_msgs += [[
              str('src: ' + src),
              str('dest: ' + dest),
              'msg: duplicate destination for pod file',
          ]]

      for res_template in (res_templates or []):
        src_relpath = res_template.get('src')
        src = pod_dir + '/' + src_relpath
        local_src = pod_local_dir + '/' + src_relpath

        dest_relpath = res_template.get('dest')
        dest = pod_dir + '/' + dest_relpath
        dest_tmp = pod_tmp_dir + '/tpl/' + dest_relpath

        dest_dir = os.path.dirname(dest)
        dest_tmp_dir = os.path.dirname(dest_tmp)

        if validate and not os.path.exists(local_src):
          error_msgs += [[
              str('src: ' + src_relpath),
              'msg: template file not found in the pod repository',
          ]]

        if dest_dir not in dir_names:
          dir_names.add(dest_dir)
          dir_to_add = dict(
              path=dest_dir,
              mode=res_template.get('dir_mode') or default_dir_mode,
          )
          directories += [dir_to_add]

        if dest_tmp_dir not in dir_names:
          dir_names.add(dest_tmp_dir)
          dir_to_add = dict(
              path=dest_tmp_dir,
              mode=res_template.get('dir_mode') or default_dir_mode,
          )
          directories += [dir_to_add]

        if dest not in file_names:
          file_names.add(dest)
          template_to_add = dict(
              src=src,
              dest=dest,
              dest_tmp=dest_tmp,
              mode=res_template.get('mode') or default_file_mode,
              params=res_template.get('params') or {},
          )
          templates += [template_to_add]
        else:
          error_msgs += [[
              str('src: ' + src),
              str('dest: ' + dest),
              'msg: duplicate destination for pod template',
          ]]

      for res_file in (res_env_files or []):
        src_relpath = res_file.get('src')
        src = env_dir + '/' + src_relpath
        local_src = src

        dest = pod_dir + '/' + res_file.get('dest')
        dest_dir = os.path.dirname(dest)

        if validate and not os.path.exists(local_src):
          error_msgs += [[
              str('src: ' + src_relpath),
              'msg: file not found in the environment repository',
          ]]

        if dest_dir not in dir_names:
          dir_names.add(dest_dir)
          dir_to_add = dict(
              path=dest_dir,
              mode=res_file.get('dir_mode') or default_dir_mode,
          )
          directories += [dir_to_add]

        if dest not in file_names:
          file_names.add(dest)
          file_to_add = dict(
              src=src,
              dest=dest,
              mode=res_file.get('mode') or default_file_mode,
          )
          files += [file_to_add]
        else:
          error_msgs += [[
              str('src: ' + src),
              str('dest: ' + dest),
              'msg: duplicate destination for pod environment file',
          ]]

      for res_template in (res_env_templates or []):
        src_relpath = res_template.get('src')
        src = env_dir + '/' + src_relpath
        local_src = src

        dest_relpath = res_template.get('dest')
        dest = pod_dir + '/' + dest_relpath
        dest_tmp = pod_tmp_dir + '/tpl/' + dest_relpath

        dest_dir = os.path.dirname(dest)
        dest_tmp_dir = os.path.dirname(dest_tmp)

        if validate and not os.path.exists(local_src):
          error_msgs += [[
              str('src: ' + src_relpath),
              'msg: template file not found in the environment repository',
          ]]

        if dest_dir not in dir_names:
          dir_names.add(dest_dir)
          dir_to_add = dict(
              path=dest_dir,
              mode=res_template.get('dir_mode') or default_dir_mode,
          )
          directories += [dir_to_add]

        if dest_tmp_dir not in dir_names:
          dir_names.add(dest_tmp_dir)
          dir_to_add = dict(
              path=dest_tmp_dir,
              mode=res_template.get('dir_mode') or default_dir_mode,
          )
          directories += [dir_to_add]

        if dest not in file_names:
          file_names.add(dest)
          template_to_add = dict(
              src=src,
              dest=dest,
              dest_tmp=dest_tmp,
              mode=res_template.get('mode') or default_file_mode,
              params=res_template.get('params') or {},
          )
          templates += [template_to_add]
        else:
          error_msgs += [[
              str('src: ' + src),
              str('dest: ' + dest),
              'msg: duplicate destination for pod environment template',
          ]]

      if not error_msgs:
        children = res.get('children')

        if children:
          for child in children:
            child_name = child.get('name')
            child_params = child.get('params')

            res_child = self.load_vars(
                file_relpath=child_name,
                params=child_params,
                data_info=data_info,
            )

            child_error_msgs = res_child.get('error_msgs')

            if child_error_msgs:
              for value in child_error_msgs:
                new_value = [str('ctx child: ' + child_name)] + value
                error_msgs += [new_value]
            else:
              res_child_result = res_child.get('result')

              child_directories = res_child_result.get('directories')
              child_files = res_child_result.get('files')
              child_templates = res_child_result.get('templates')

              if child_directories:
                directories += child_directories

              if child_files:
                files += child_files

              if child_templates:
                templates += child_templates

    ret = dict(
        result=dict(
            directories=directories,
            files=files,
            templates=templates,
        ),
        error_msgs=error_msgs,
    )

    return ret

  def lookup(self, variables, file, params):
    display.debug("File lookup term: %s" % file)

    lookupfile = self.find_file_in_search_path(variables, 'templates', file)
    display.vvvv("File lookup using %s as file" % lookupfile)

    if lookupfile:
      b_template_data, _ = self._loader._get_file_contents(lookupfile)
      template_data = to_text(b_template_data, errors='surrogate_or_strict')

      # set jinja2 internal search path for includes
      searchpath = variables.get('ansible_search_path', [])

      if searchpath:
        # our search paths aren't actually the proper ones for jinja includes.
        # We want to search into the 'templates' subdir of each search path in
        # addition to our original search paths.
        newsearchpath = []

        for path in searchpath:
          newsearchpath.append(os.path.join(path, 'templates'))
          newsearchpath.append(path)

        searchpath = newsearchpath

      searchpath.insert(0, os.path.dirname(lookupfile))

      # The template will have access to all existing variables,
      # plus some added by ansible (e.g., template_{path,mtime}),
      # plus anything passed to the lookup with the template_vars=
      # argument.
      new_vars = deepcopy(variables)
      new_vars.update(generate_ansible_template_vars(lookupfile))
      new_vars.update(dict(params=params))
      display.vv("params keys: %s" % params.keys())

      #TODO: Remove in newer ansible versions
      old_vars = self._templar._available_variables
      self._templar.set_available_variables(new_vars)
      res = self._templar.template(
          template_data,
          preserve_trailing_newlines=True,
          convert_data=False,
          escape_backslashes=False
      )
      self._templar.set_available_variables(old_vars)
      ###

      #TODO: Include in newer ansible versions
      # if USE_JINJA2_NATIVE:
      #   templar = self._templar.copy_with_new_env(environment_class=AnsibleEnvironment)
      # else:
      #   templar = self._templar

      # with templar.set_temporary_context(
      #     variable_start_string=None,
      #     variable_end_string=None,
      #     available_variables=new_vars,
      #     searchpath=searchpath
      # ):
      #   res = templar.template(
      #       template_data,
      #       preserve_trailing_newlines=True,
      #       escape_backslashes=False
      #   )

      if USE_JINJA2_NATIVE:
        # jinja2_native is true globally, we need this text
        # not to be processed by literal_eval anywhere in Ansible
        res = NativeJinjaText(res)

      return res
    else:
      raise AnsibleError("the template file %s could not be found for the lookup" % file)

  #TODO: Use lrd_utils (verify creating a collection to be able to import)
  def error_text(self, error_msgs, context=None):
    if not error_msgs:
      return ''

    if context:
      msg = str('[' + context + '] ' + str(len(error_msgs)) + ' error(s)')
      error_msgs = [[msg]] + error_msgs + [[msg]]

    separator = "-------------------------------------------"
    new_error_msgs = ['', separator]

    for value in error_msgs:
      new_error_msgs += [value, separator]

    Dumper.ignore_aliases = lambda self, data: True
    error = yaml.dump(new_error_msgs, Dumper=Dumper, default_flow_style=False)

    return error
