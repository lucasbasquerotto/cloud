#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring

from __future__ import absolute_import, division, print_function
__metaclass__ = type # pylint: disable=invalid-name

import yaml

try:
  from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
  from yaml import Loader, Dumper

def merge_dicts(*args):
  new_dict = None

  for current_dict in (args or []):
    if not new_dict:
      new_dict = current_dict.copy()
    else:
      new_dict.update(current_dict)

  return new_dict

def load_yaml(text):
  return yaml.load(text, Loader=Loader)

def load_yaml_file(file_path):
  with open(file_path, 'rb') as file:
    content = file.read().decode('utf-8-sig')
    return load_yaml(content)

def error_text(error_msgs, context=None):
  if not error_msgs:
    return ''

  if context:
    msg = '[' + context + '] ' + str(len(error_msgs)) + ' error(s)'
    error_msgs = [[msg]] + error_msgs + [[msg]]

  separator = "-------------------------------------------"
  new_error_msgs = [separator]

  for value in error_msgs:
    new_error_msgs += [value, separator]

  Dumper.ignore_aliases = lambda self, data: True
  error = yaml.dump(new_error_msgs, Dumper=Dumper, default_flow_style=False)

  return error

def default(value, default_value):
  return default_value if value is None else value

def is_empty(value):
  return (value is None) or (isinstance(value, str) and value == '')

def is_int(str_val):
  try:
    int(str_val)
    return True
  except ValueError:
    return False

def is_float(str_val):
  try:
    float(str_val)
    return True
  except ValueError:
    return False

def is_bool(str_val):
  return to_bool(str_val) is not None

def to_bool(value):
  if value is None:
    return None

  if isinstance(value, bool):
    return value

  if isinstance(value, str):
    valid_strs_true = ['True', 'true', 'Yes', 'yes']
    valid_strs_false = ['False', 'false', 'No', 'no']

    if value in valid_strs_true:
      return True

    if value in valid_strs_false:
      return False

  return None
