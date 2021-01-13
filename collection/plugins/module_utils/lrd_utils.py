#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring

from __future__ import absolute_import, division, print_function
__metaclass__ = type  # pylint: disable=invalid-name

import yaml

try:
  from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
  from yaml import Loader, Dumper

cached_files_dict = dict()


def merge_dicts(*args):
  new_dict = None

  for current_dict in (args or []):
    if not new_dict:
      new_dict = current_dict.copy() if (current_dict is not None) else None
    else:
      current_dict = current_dict if (current_dict is not None) else dict()
      new_dict.update(current_dict)

  return new_dict


def load_file(file_path):
  with open(file_path, 'rb') as file:
    content = file.read().decode('utf-8-sig')
    return content


def load_yaml(text):
  return yaml.load(text, Loader=Loader)


def load_yaml_file(file_path):
  return load_yaml(load_file(file_path))


def error_text(error_msgs, context=None):
  if not error_msgs:
    return ''

  if context:
    msg = '[' + str(context) + '] ' + str(len(error_msgs)) + ' error(s)'
    error_msgs = [[msg]] + error_msgs + [[msg]]

  separator = "-------------------------------------------"
  new_error_msgs = ['', separator]

  for value in error_msgs:
    new_error_msgs += [value, separator]

  Dumper.ignore_aliases = lambda self, data: True
  error = yaml.dump(new_error_msgs, Dumper=Dumper, default_flow_style=False)

  return error


def default(value, default_value):
  return default_value if value is None else value


def is_bool(str_val):
  return to_bool(str_val) is not None


def is_empty(value):
  return (value is None) or (is_str(value) and value == '')


def is_float(str_val):
  try:
    float(str_val)
    return True
  except ValueError:
    return False


def is_int(str_val):
  try:
    int(str_val)
    return True
  except ValueError:
    return False


def is_str(value):
  try:
    return isinstance(value, basestring)
  except NameError:
    return isinstance(value, str)


def load_cached_file(file_path):
  if file_path in cached_files_dict:
    return cached_files_dict.get(file_path)

  file_result = load_yaml_file(file_path)
  cached_files_dict[file_path] = file_result

  return file_result


def to_bool(value, default_value=None):
  if value is None:
    return default_value

  if isinstance(value, bool):
    return value

  if is_str(value):
    valid_strs_true = ['True', 'true', 'Yes', 'yes']
    valid_strs_false = ['False', 'false', 'No', 'no']

    if value in valid_strs_true:
      return True

    if value in valid_strs_false:
      return False

  return None


def to_float(val):
  if val is None:
    return None
  elif isinstance(val, float):
    return val
  elif is_str(val):
    try:
      return float(val)
    except ValueError:
      return None
  else:
    return None


def to_int(val):
  if val is None:
    return None
  elif isinstance(val, int):
    return val
  elif is_str(val):
    try:
      return int(val)
    except ValueError:
      return None
  else:
    return None
