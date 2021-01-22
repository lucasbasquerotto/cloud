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

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import error_text, to_bool
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_ctx import prepare_services

from ansible.module_utils._text import to_text
from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError

__metaclass__ = type  # pylint: disable=invalid-name

DOCUMENTATION = """
    name: lrd.cloud.services
    author: Lucas Basquerotto
    version_added: "2.11"
    description:
      - Return the prepared services from the raw data about them.
    options:
      services:
        description: The raw services
        type: list
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
   description: prepared services
   type: list
   elements: raw
"""


class LookupModule(LookupBase):

  def run(self, terms, variables, **kwargs):
    top = to_bool(kwargs.get('top'))
    env_data = kwargs.get('env_data')
    validate = kwargs.get('validate')

    ret = []
    error_msgs = []

    for term in terms:
      services = term

      run_info = dict(
          plugin=self,
          ansible_vars=variables,
          env_data=env_data,
          validate=validate if (validate is not None) else True,
      )

      result_info = prepare_services(services, run_info=run_info, top=top)

      result_aux = result_info.get('result')
      error_msgs_aux = result_info.get('error_msgs') or list()

      if error_msgs_aux:
        error_msgs += error_msgs_aux
      else:
        ret.append(result_aux)

    if error_msgs:
      raise AnsibleError(to_text(error_text(error_msgs, 'services')))

    return ret
