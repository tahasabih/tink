// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
////////////////////////////////////////////////////////////////////////////////

#ifndef TINK_STREAMINGAEAD_TEST_UTIL_H_
#define TINK_STREAMINGAEAD_TEST_UTIL_H_

#include "absl/strings/string_view.h"
#include "tink/streaming_aead.h"
#include "tink/util/status.h"

namespace crypto {
namespace tink {

// Encrypt with NewEncryptingStream, then decrypt using NewDecryptingStream.
// Any error will be propagated to the caller. Returns OK if the resulting
// decryption is equal to the plaintext.
crypto::tink::util::Status EncryptThenDecrypt(
    StreamingAead* encrypter, StreamingAead* decrypter,
    absl::string_view plaintext, absl::string_view associated_data);

}  // namespace tink
}  // namespace crypto

#endif  // TINK_STREAMINGAEAD_TEST_UTIL_H_
