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
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_ctx import prepare_ctx

from ansible.module_utils._text import to_text
from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError

__metaclass__ = type  # pylint: disable=invalid-name

DOCUMENTATION = """
    name: lrd.cloud.ctx
    author: Lucas Basquerotto
    version_added: "2.11"
    description:
      - Return the context variables from the environment based on the environment dictionary and ctx name.
    options:
      ctx_name:
        description: The context name
        type: str
        required: true
      env_data:
        description: The environment data (vars, env type, ctx dir)
        type: dict
        required: true
      validate:
        description: Specifies if the schema (when defined) should be validated
        type: bool
        default: true
"""

RETURN = """
_raw:
   description: file(s) content after templating
   type: dicts
   elements: raw
"""


class LookupModule(LookupBase):

  def run(self, terms, variables, **kwargs):
    env_data = kwargs.get('env_data')
    services_data = kwargs.get('services_data')
    validate = kwargs.get('validate')

    ret = []
    error_msgs = []

    for term in terms:
      ctx_name = term

      run_info = dict(
          plugin=self,
          ansible_vars=variables,
          env_data=env_data,
          services_data=services_data,
          validate=validate if (validate is not None) else True,
      )

      result_info = prepare_ctx(ctx_name, run_info)

      result_aux = result_info.get('result')
      error_msgs_aux = result_info.get('error_msgs') or list()

      if error_msgs_aux:
        error_msgs += error_msgs_aux
      else:
        ret.append(result_aux)

    if error_msgs:
      raise AnsibleError(to_text(error_text(error_msgs, 'ctx generation')))

    return ret
