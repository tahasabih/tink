// Copyright 2017 Google LLC
//
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

#include "tink/aead/aes_gcm_key_manager.h"

#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "tink/aead.h"
#include "tink/util/status.h"
#include "tink/util/statusor.h"
#include "tink/util/test_matchers.h"
#include "proto/aes_gcm.pb.h"

namespace crypto {
namespace tink {

namespace {

using ::crypto::tink::test::IsOk;
using ::crypto::tink::test::StatusIs;
using ::crypto::tink::util::StatusOr;
using ::google::crypto::tink::AesGcmKey;
using ::google::crypto::tink::AesGcmKeyFormat;
using ::testing::Eq;

TEST(AesGcmKeyManagerTest, Basics) {
  EXPECT_THAT(AesGcmKeyManager().get_version(), Eq(0));
  EXPECT_THAT(AesGcmKeyManager().get_key_type(),
              Eq("type.googleapis.com/google.crypto.tink.AesGcmKey"));
  EXPECT_THAT(AesGcmKeyManager().key_material_type(),
              Eq(google::crypto::tink::KeyData::SYMMETRIC));
}

TEST(AesGcmKeyManagerTest, ValidateEmptyKey) {
  EXPECT_THAT(AesGcmKeyManager().ValidateKey(AesGcmKey()),
              StatusIs(util::error::INVALID_ARGUMENT));
}

TEST(AesGcmKeyManagerTest, ValidateValid16ByteKey) {
  AesGcmKey key;
  key.set_version(0);
  key.set_key_value("0123456789abcdef");
  EXPECT_THAT(AesGcmKeyManager().ValidateKey(key), IsOk());
}

TEST(AesGcmKeyManagerTest, ValidateValid32ByteKey) {
  AesGcmKey key;
  key.set_version(0);
  key.set_key_value("01234567890123456789012345678901");
  EXPECT_THAT(AesGcmKeyManager().ValidateKey(key), IsOk());
}

TEST(AesGcmKeyManagerTest, InvalidKeySizes15Bytes) {
  AesGcmKey key;
  key.set_version(0);
  key.set_key_value("0123456789abcde");
  EXPECT_THAT(AesGcmKeyManager().ValidateKey(key),
              StatusIs(util::error::INVALID_ARGUMENT));
}

TEST(AesGcmKeyManagerTest, InvalidKeySizes17Bytes) {
  AesGcmKey key;
  key.set_version(0);
  key.set_key_value("0123456789abcdefg");
  EXPECT_THAT(AesGcmKeyManager().ValidateKey(key),
              StatusIs(util::error::INVALID_ARGUMENT));
}

TEST(AesGcmKeyManagerTest, InvalidKeySizes24Bytes) {
  AesGcmKey key;
  key.set_version(0);
  key.set_key_value("01234567890123");
  EXPECT_THAT(AesGcmKeyManager().ValidateKey(key),
              StatusIs(util::error::INVALID_ARGUMENT));
}

TEST(AesGcmKeyManagerTest, InvalidKeySizes31Bytes) {
  AesGcmKey key;
  key.set_version(0);
  key.set_key_value("0123456789012345678901234567890");
  EXPECT_THAT(AesGcmKeyManager().ValidateKey(key),
              StatusIs(util::error::INVALID_ARGUMENT));
}

TEST(AesGcmKeyManagerTest, InvalidKeySizes33Bytes) {
  AesGcmKey key;
  key.set_version(0);
  key.set_key_value("012345678901234567890123456789012");
  EXPECT_THAT(AesGcmKeyManager().ValidateKey(key),
              StatusIs(util::error::INVALID_ARGUMENT));
}

TEST(AesGcmKeyManagerTest, ValidateKeyFormat) {
  AesGcmKeyFormat format;

  format.set_key_size(0);
  EXPECT_THAT(AesGcmKeyManager().ValidateKeyFormat(format),
              StatusIs(util::error::INVALID_ARGUMENT));

  format.set_key_size(1);
  EXPECT_THAT(AesGcmKeyManager().ValidateKeyFormat(format),
              StatusIs(util::error::INVALID_ARGUMENT));

  format.set_key_size(15);
  EXPECT_THAT(AesGcmKeyManager().ValidateKeyFormat(format),
              StatusIs(util::error::INVALID_ARGUMENT));

  format.set_key_size(16);
  EXPECT_THAT(AesGcmKeyManager().ValidateKeyFormat(format), IsOk());

  format.set_key_size(17);
  EXPECT_THAT(AesGcmKeyManager().ValidateKeyFormat(format),
              StatusIs(util::error::INVALID_ARGUMENT));

  format.set_key_size(31);
  EXPECT_THAT(AesGcmKeyManager().ValidateKeyFormat(format),
              StatusIs(util::error::INVALID_ARGUMENT));

  format.set_key_size(32);
  EXPECT_THAT(AesGcmKeyManager().ValidateKeyFormat(format), IsOk());

  format.set_key_size(33);
  EXPECT_THAT(AesGcmKeyManager().ValidateKeyFormat(format),
              StatusIs(util::error::INVALID_ARGUMENT));
}

TEST(AesGcmKeyManagerTest, Create16ByteKey) {
  AesGcmKeyFormat format;
  format.set_key_size(16);

  StatusOr<AesGcmKey> key_or = AesGcmKeyManager().CreateKey(format);

  ASSERT_THAT(key_or.status(), IsOk());
  EXPECT_THAT(key_or.ValueOrDie().key_value().size(), Eq(format.key_size()));
}

TEST(AesGcmKeyManagerTest, Create32ByteKey) {
  AesGcmKeyFormat format;
  format.set_key_size(32);

  StatusOr<AesGcmKey> key_or = AesGcmKeyManager().CreateKey(format);

  ASSERT_THAT(key_or.status(), IsOk());
  EXPECT_THAT(key_or.ValueOrDie().key_value().size(), Eq(format.key_size()));
}

crypto::tink::util::Status EncryptThenDecrypt(Aead* encrypter, Aead* decrypter,
                                              absl::string_view message,
                                              absl::string_view aad) {
  StatusOr<std::string> encryption_or = encrypter->Encrypt(message, aad);
  if (!encryption_or.status().ok()) return encryption_or.status();
  StatusOr<std::string> decryption_or =
      decrypter->Decrypt(encryption_or.ValueOrDie(), aad);
  if (!decryption_or.status().ok()) return decryption_or.status();
  if (decryption_or.ValueOrDie() != message) {
    return crypto::tink::util::Status(crypto::tink::util::error::INTERNAL,
                                      "Message/Decryption mismatch");
  }
  return util::OkStatus();
}

TEST(AesGcmKeyManagerTest, CreateAead) {
  AesGcmKeyFormat format;
  format.set_key_size(32);
  StatusOr<AesGcmKey> key_or = AesGcmKeyManager().CreateKey(format);
  ASSERT_THAT(key_or.status(), IsOk());

  StatusOr<std::unique_ptr<Aead>> aead_or =
      AesGcmKeyManager().GetPrimitive<Aead>(key_or.ValueOrDie());

  ASSERT_THAT(aead_or.status(), IsOk());

  StatusOr<std::unique_ptr<Aead>> boring_ssl_aead_or =
      subtle::AesGcmBoringSsl::New(key_or.ValueOrDie().key_value());
  ASSERT_THAT(boring_ssl_aead_or.status(), IsOk());

  ASSERT_THAT(EncryptThenDecrypt(aead_or.ValueOrDie().get(),
                                 boring_ssl_aead_or.ValueOrDie().get(),
                                 "message", "aad"),
              IsOk());
}


}  // namespace
}  // namespace tink
}  // namespace crypto
