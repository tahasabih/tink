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

"""HybridDecrypt wrapper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import google_type_annotations
from __future__ import print_function

# Special imports
from absl import logging

from typing import Type

from tink.python.core import crypto_format
from tink.python.core import primitive_set
from tink.python.core import primitive_wrapper
from tink.python.core import tink_error
from tink.python.hybrid import hybrid_decrypt


class _WrappedHybridDecrypt(hybrid_decrypt.HybridDecrypt):
  """Implements HybridDecrypt for a set of HybridDecrypt primitives."""

  def __init__(self, pset: primitive_set.PrimitiveSet):
    self._primitive_set = pset

  def decrypt(self, ciphertext: bytes, context_info: bytes) -> bytes:
    if len(ciphertext) > crypto_format.NON_RAW_PREFIX_SIZE:
      prefix = ciphertext[:crypto_format.NON_RAW_PREFIX_SIZE]
      ciphertext_no_prefix = ciphertext[crypto_format.NON_RAW_PREFIX_SIZE:]
      for entry in self._primitive_set.primitive_from_identifier(prefix):
        try:
          return entry.primitive.decrypt(ciphertext_no_prefix,
                                         context_info)
        except tink_error.TinkError as e:
          logging.info(
              'ciphertext prefix matches a key, but cannot decrypt: %s', e)
    # Let's try all RAW keys.
    for entry in self._primitive_set.raw_primitives():
      try:
        return entry.primitive.decrypt(ciphertext, context_info)
      except tink_error.TinkError as e:
        pass
    # nothing works.
    raise tink_error.TinkError('Decryption failed.')


class HybridDecryptWrapper(
    primitive_wrapper.PrimitiveWrapper[hybrid_decrypt.HybridDecrypt]):
  """HybridDecryptWrapper is the PrimitiveWrapper for HybridDecrypt.

  The returned primitive works with a keyset (rather than a single key). To
  decrypt, the primitive uses the prefix of the ciphertext to efficiently select
  the right key in the set. If the keys associated with the prefix do not work,
  the primitive tries all keys with OutputPrefixType RAW.
  """

  def wrap(self,
           pset: primitive_set.PrimitiveSet) -> hybrid_decrypt.HybridDecrypt:
    return _WrappedHybridDecrypt(pset)

  def primitive_class(self) -> Type[hybrid_decrypt.HybridDecrypt]:
    return hybrid_decrypt.HybridDecrypt
