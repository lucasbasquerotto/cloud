# Copyright: (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
# Copyright: (c) 2012-17, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=wrong-import-position
# pylint: disable=import-error
# pylint: disable=protected-access

# pyright: reportUnusedImport=true
# pyright: reportUnusedVariable=true
# pyright: reportMissingImports=false

from __future__ import (absolute_import, division, print_function)

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import error_text
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_project import prepare_project

from ansible.module_utils._text import to_text
from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError

__metaclass__ = type  # pylint: disable=invalid-name

DOCUMENTATION = """
    name: lrd.cloud.project
    author: Lucas Basquerotto
    version_added: "2.11"
    description:
      - Return the context variables from the environment based on the environment dictionary and ctx name.
    options:
      env:
        description: The environment dictionary
        type: dict
        required: true
      env_init:
        description: The controller environment dictionary (output of the Controller Preparation Step)
        type: dict
        required: true
      env_original:
        description: The original environment dictionary (loaded from the Project Environemnt Repository File)
        type: dict
        required: true
      env_info:
        description: General information about the environment, like the directory, lax permissions and so on
        type: str
        default: true
"""

RETURN = """
_raw:
   description: file(s) content after templating
   type: dicts
   elements: raw
"""


class LookupModule(LookupBase):

  def run(self, terms, **kwargs):
    env_init = kwargs.get('env_init')
    env_original = kwargs.get('env_original')
    env_info = kwargs.get('env_info')

    ret = []
    error_msgs = []

    for term in terms:
      env = term

      result_info = prepare_project(
          env=env,
          env_init=env_init,
          env_original=env_original,
          env_info=env_info,
      )

      result_aux = result_info.get('result')
      error_msgs_aux = result_info.get('error_msgs') or list()

      if error_msgs_aux:
        error_msgs += error_msgs_aux
      else:
        ret.append(result_aux)

    if error_msgs:
      raise AnsibleError(
          to_text(error_text(error_msgs, 'project data generation'))
      )

    return ret
