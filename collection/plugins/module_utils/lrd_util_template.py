#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=import-error
# pylint: disable=protected-access

import os
from copy import deepcopy

from ansible.errors import AnsibleError
from ansible.module_utils._text import to_text
from ansible.template import generate_ansible_template_vars, USE_JINJA2_NATIVE
from ansible.utils.display import Display

display = Display()

# from ansible.template import generate_ansible_template_vars, AnsibleEnvironment, USE_JINJA2_NATIVE

if USE_JINJA2_NATIVE:
  from ansible.utils.native_jinja import NativeJinjaText


def lookup(plugin, variables, file, params):
  display.debug("File lookup term: %s" % file)

  lookupfile = plugin.find_file_in_search_path(variables, 'templates', file)
  display.vvvv("File lookup using %s as file" % lookupfile)

  if lookupfile:
    b_template_data, _ = plugin._loader._get_file_contents(lookupfile)
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

    # TODO: Remove in newer ansible versions
    old_vars = plugin._templar._available_variables
    plugin._templar.set_available_variables(new_vars)
    res = plugin._templar.template(
        template_data,
        preserve_trailing_newlines=True,
        convert_data=False,
        escape_backslashes=False
    )
    plugin._templar.set_available_variables(old_vars)
    ###

    # TODO: Include in newer ansible versions
    # if USE_JINJA2_NATIVE:
    #   templar = plugin._templar.copy_with_new_env(environment_class=AnsibleEnvironment)
    # else:
    #   templar = plugin._templar

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
    raise AnsibleError(
        "the template file %s could not be found for the lookup" % file
    )
