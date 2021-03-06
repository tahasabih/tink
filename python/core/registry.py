# Copyright 2019 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tink Registry."""

from __future__ import absolute_import
from __future__ import division
from __future__ import google_type_annotations
from __future__ import print_function

from typing import Any, Text, Tuple, Type, TypeVar

from tink.proto import tink_pb2
from tink.python.core import key_manager as km_module
from tink.python.core import primitive_set as pset_module
from tink.python.core import primitive_wrapper
from tink.python.core import tink_error

P = TypeVar('P')


class Registry(object):
  """A global container of key managers.

  Registry maps supported key types to a corresponding KeyManager object,
  which 'understands' the key type (i.e., the KeyManager can instantiate the
  primitive corresponding to given key, or can generate new keys of the
  supported key type). Keeping KeyManagers for all primitives in a single
  Registry (rather than having a separate KeyManager per primitive) enables
  modular construction of compound primitives from 'simple' ones,
  e.g., AES-CTR-HMAC AEAD encryption uses IND-CPA encryption and a MAC.

  Registry is initialized at startup, and is later used to instantiate
  primitives for given keys or keysets.
  """

  _key_managers = {}  # type: dict[Text, Tuple[km_module.KeyManager, bool]]
  _wrappers = {}  # type: dict[Type, primitive_wrapper.PrimitiveWrapper]

  @classmethod
  def reset(cls) -> None:
    """Resets the registry."""
    cls._key_managers = {}
    cls._wrappers = {}

  @classmethod
  def _key_manager_internal(
      cls, type_url: Text) -> Tuple[km_module.KeyManager, bool]:
    """Returns a key manager, new_key_allowed pair for the given type_url."""
    if type_url not in cls._key_managers:
      raise tink_error.TinkError(
          'No manager for type {} has been registered.'.format(type_url))
    return cls._key_managers[type_url]

  @classmethod
  def key_manager(cls, type_url: Text) -> km_module.KeyManager:
    """Returns a key manager for the given type_url and primitive_class.

    Args:
      type_url: Key type string

    Returns:
      A KeyManager object
    """
    key_mgr, _ = cls._key_manager_internal(type_url)
    return key_mgr

  @classmethod
  def register_key_manager(cls,
                           key_manager: km_module.KeyManager,
                           new_key_allowed: bool = True) -> None:
    """Tries to register a key_manager for the given key_manager.key_type().

    Args:
      key_manager: A KeyManager object
      new_key_allowed: If new_key_allowed is true, users can generate new keys
        with this manager using Registry.new_key()
    """
    key_managers = cls._key_managers
    type_url = key_manager.key_type()
    primitive_class = key_manager.primitive_class()

    if not key_manager.does_support(type_url):
      raise tink_error.TinkError(
          'The manager does not support its own type {}.'.format(type_url))

    if type_url in key_managers:
      existing, existing_new_key = key_managers[type_url]
      if (type(existing) != type(key_manager) or  # pylint: disable=unidiomatic-typecheck
          existing.primitive_class() != primitive_class):
        raise tink_error.TinkError(
            'A manager for type {} has been already registered.'.format(
                type_url))
      else:
        if not existing_new_key and new_key_allowed:
          raise tink_error.TinkError(
              ('A manager for type {} has been already registered '
               'with forbidden new key operation.').format(type_url))
        key_managers[type_url] = (existing, new_key_allowed)
    else:
      key_managers[type_url] = (key_manager, new_key_allowed)

  @classmethod
  def primitive(cls, key_data: tink_pb2.KeyData, primitive_class: Type[P]) -> P:
    """Creates a new primitive for the key given in key_data.

    It looks up a KeyManager identified by key_data.type_url,
    and calls manager's primitive(key_data) method.

    Args:
      key_data: KeyData object
      primitive_class: The expected primitive class

    Returns:
      A primitive for the given key_data
    Raises:
      Error if primitive_class does not match the registered primitive class.
    """
    key_mgr = cls.key_manager(key_data.type_url)
    if key_mgr.primitive_class() != primitive_class:
      raise tink_error.TinkError(
          'Wrong primitive class: type {} uses primitive {}, and not {}.'
          .format(key_data.type_url, key_mgr.primitive_class().__name__,
                  primitive_class.__name__))
    return key_mgr.primitive(key_data)

  @classmethod
  def new_key_data(cls, key_template: tink_pb2.KeyTemplate) -> tink_pb2.KeyData:
    """Generates a new key for the specified key_template."""
    key_mgr, new_key_allowed = cls._key_manager_internal(
        key_template.type_url)

    if not new_key_allowed:
      raise tink_error.TinkError(
          'KeyManager for type {} does not allow for creation of new keys.'
          .format(key_template.type_url))

    return key_mgr.new_key_data(key_template)

  @classmethod
  def public_key_data(cls,
                      private_key_data: tink_pb2.KeyData) -> tink_pb2.KeyData:
    """Generates a new key for the specified key_template."""
    if (private_key_data.key_material_type !=
        tink_pb2.KeyData.ASYMMETRIC_PRIVATE):
      raise tink_error.TinkError('The keyset contains a non-private key')
    key_mgr = cls.key_manager(private_key_data.type_url)
    if not isinstance(key_mgr, km_module.PrivateKeyManager):
      raise tink_error.TinkError(
          'manager for key type {} is not a PrivateKeyManager'
          .format(private_key_data.type_url))
    return key_mgr.public_key_data(private_key_data)

  @classmethod
  def register_primitive_wrapper(
      cls, wrapper: primitive_wrapper.PrimitiveWrapper) -> None:
    """Tries to register a PrimitiveWrapper.

    Args:
      wrapper: A PrimitiveWrapper object.
    Raises:
      Error if a different wrapper has already been registered for the same
      Primitive.
    """
    if (wrapper.primitive_class() in cls._wrappers and
        type(cls._wrappers[wrapper.primitive_class()]) != type(wrapper)):  # pylint: disable=unidiomatic-typecheck
      raise tink_error.TinkError(
          'A wrapper for primitive {} has already been added.'.format(
              wrapper.primitive_class().__name__))
    wrapped = wrapper.wrap(
        pset_module.PrimitiveSet(wrapper.primitive_class()))
    if not isinstance(wrapped, wrapper.primitive_class()):
      raise tink_error.TinkError(
          'Wrapper for primitive {} generates incompatibe primitve of type {}'
          .format(wrapper.primitive_class().__name__,
                  type(wrapped).__name__))
    cls._wrappers[wrapper.primitive_class()] = wrapper

  @classmethod
  def wrap(
      cls, primitive_set: pset_module.PrimitiveSet) -> Any:  # -> Primitive
    """Tries to register a PrimitiveWrapper.

    Args:
      primitive_set: A PrimitiveSet object.
    Returns:
      A primitive that wraps the primitives in primitive_set.
    Raises:
      Error if no wrapper for this primitive class is registered.
    """
    if primitive_set.primitive_class() not in cls._wrappers:
      raise tink_error.TinkError(
          'No PrimitiveWrapper registered for primitive {}.'
          .format(primitive_set.primitive_class() .__name__))
    wrapper = cls._wrappers[primitive_set.primitive_class()]
    return wrapper.wrap(primitive_set)
