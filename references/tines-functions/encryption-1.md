# Tines formula functions: Encryption (part 1 of 2: AES_DECRYPT to RSA_ENCRYPT)

Independent, unofficial porting notes for the functions Tines files under "Encryption": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: AES_DECRYPT, AES_ENCRYPT, GENERATE_RSA_KEYS, OPENSSL_DECRYPT, OPENSSL_ENCRYPT, RSA_AES_HYBRID_DECRYPT, RSA_AES_HYBRID_ENCRYPT, RSA_DECRYPT, RSA_ENCRYPT

## AES_DECRYPT

- **Summary:** DEPRECATED - decrypt AES-256-CBC text
- **Signature:** `AES_DECRYPT(encoded_text, key, [iv])`
- **Categories:** Encryption
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/aes-decrypt/

**Arguments**

- `encoded_text` (required): AES-256-CBC Base64 encoded text, or the direct output of AES_ENCRYPT.
- `key` (required): Secret key (AES_ENCRYPT docs: a 32 byte secret value).
- `iv` (optional): Initialization vector (positional third argument).

**Returns:** The decrypted plaintext (text).

**Porting semantics**

- Deprecated in the Tines docs; the TINES_* or OPENSSL_* pairs are the suggested replacements.
- Ciphertext produced in AES_ENCRYPT's `aead` mode with an expiry is refused once it has expired.
- Not specified in docs: which IV is used when `iv` is omitted; byte encoding of key/iv; error behaviour on wrong key or bad input; the layout of "aead" mode output.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - where the ciphertext is AES-256-CBC of "meet at noon" under that key and iv
formula: AES_DECRYPT(ciphertext, key, iv),
output:  "meet at noon"
```

**TypeScript equivalent** (APPROXIMATE: only plain AES-256-CBC with an explicit IV can be reproduced; the "aead" format and the default IV are Tines-internal)

```ts
import { createDecipheriv } from "node:crypto";
// Plain mode with an explicit IV only. Key = 32 bytes, IV = 16 bytes (encoding assumed UTF-8).
function aesDecrypt(encodedText: string, key: string, iv: string): string {
  const d = createDecipheriv("aes-256-cbc", Buffer.from(key, "utf8"), Buffer.from(iv, "utf8"));
  return Buffer.concat([d.update(Buffer.from(encodedText, "base64")), d.final()]).toString("utf8");
}
```

- If the story both encrypts and decrypts, port both sides together using the replacement pair in the TINES_ENCRYPT / TINES_DECRYPT entries instead of trying to match the Tines wire format.

## AES_ENCRYPT

- **Summary:** DEPRECATED - encrypt text with AES
- **Signature:** `AES_ENCRYPT(text, key, [iv], [mode: "aead"], [expires_in])`
- **Categories:** Encryption
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/aes-encrypt/

**Arguments**

- `text` (required): Plaintext.
- `key` (required): Secret key, 32 bytes long.
- `iv` (optional): Initialization vector, 16 bytes, unique per message. Not needed in `aead` mode, which manages its own.
- `mode` (optional): Keyword argument. Omitted: plain AES-256-CBC. `mode: "aead"`: authenticated encryption.
- `expires_in` (optional): Keyword argument, `aead` mode only: lifetime of the ciphertext in seconds, enforced when decrypting.

**Returns:** Ciphertext as text made of base64 characters plus `.`.

**Porting semantics**

- Deprecated in the Tines docs; the TINES_* or OPENSSL_* pairs are the suggested replacements.
- `mode` and `expires_in` are passed by name, after the positional arguments.
- Not specified in docs: which IV is used when none is given in plain mode; byte encoding of key and iv; exact output layout; details of the `aead` mode.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - with a 32-byte key and a 16-byte iv
formula: AES_ENCRYPT("meet at noon", key, iv)
output:  base64 text that decrypts back to "meet at noon" with the same key and iv
```

**TypeScript equivalent** (APPROXIMATE: only plain AES-256-CBC with an explicit IV can be reproduced; the `aead` output is a Tines-internal format)

```ts
import { createCipheriv } from "node:crypto";
// Plain mode with an explicit IV only. Key = 32 bytes, IV = 16 bytes (encoding assumed UTF-8).
function aesEncrypt(text: string, key: string, iv: string): string {
  const c = createCipheriv("aes-256-cbc", Buffer.from(key, "utf8"), Buffer.from(iv, "utf8"));
  return Buffer.concat([c.update(text, "utf8"), c.final()]).toString("base64");
}
```

- Output will not be readable by Tines' AES_DECRYPT unless the formats happen to match; if the story both encrypts and decrypts, port both sides together (see the TINES_ENCRYPT / TINES_DECRYPT entries for a self-contained pair with expiry).

## GENERATE_RSA_KEYS

- **Summary:** generate an RSA public/private key pair
- **Signature:** `GENERATE_RSA_KEYS()`
- **Categories:** Encryption
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/generate-rsa-keys/

**Arguments**

- None.

**Returns:** An array of two texts: the public key first, the private key second.

**Porting semantics**

- Keys are 2048 bits by default; 4096 is the other supported size.
- The documented signature has no parameter, so how a 4096-bit key is requested is not shown.
- Not specified in docs: key encoding (PEM type) of the returned keys; how to request 4096 bits.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: GENERATE_RSA_KEYS()
output:  a fresh [public key, private key] pair, different on every call
```

**TypeScript equivalent**

```ts
import { generateKeyPairSync } from "node:crypto";
function generateRsaKeys(bits: 2048 | 4096 = 2048): [string, string] {
  const { publicKey, privateKey } = generateKeyPairSync("rsa", {
    modulusLength: bits,
    publicKeyEncoding: { type: "spki", format: "pem" },
    privateKeyEncoding: { type: "pkcs8", format: "pem" },
  });
  return [publicKey, privateKey];
}
```

- PEM (SPKI / PKCS#8) output is an assumption.

## OPENSSL_DECRYPT

- **Summary:** decrypt data with OpenSSL (AES CBC/GCM/ECB)
- **Signature:** `OPENSSL_DECRYPT(ciphertext, algorithm, key, iv, [aad], [auth_tag])`
- **Categories:** Encryption
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/openssl-decrypt/

**Arguments**

- `ciphertext` (required): The encrypted data.
- `algorithm` (required): The cipher: AES in CBC mode (128- or 256-bit key), GCM mode (256-bit) or ECB mode (128- or 256-bit), written like `"aes-256-gcm"`.
- `key` (required): The decryption key.
- `iv` (required): The IV that was used to encrypt. Pass empty text or null for a cipher without an IV (ECB).
- `aad` (optional): Additional authenticated data, for authenticated ciphers (GCM) only.
- `auth_tag` (optional): The authentication tag, for authenticated ciphers (GCM) only.

**Returns:** The plaintext.

**Porting semantics**

- Not specified in docs: encodings of ciphertext, iv and auth_tag (OPENSSL_ENCRYPT returns them base64 encoded, so base64 is the natural assumption); key encoding; error behaviour on wrong key or failed authentication.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - where enc is AES-256-GCM of "wire 250 EUR"
formula: OPENSSL_DECRYPT(enc.encrypted, "aes-256-gcm", key, enc.iv, NULL, enc.auth_tag)
output:  "wire 250 EUR"
```

**TypeScript equivalent** (APPROXIMATE: assumes base64 inputs as produced by OPENSSL_ENCRYPT and a raw (UTF-8 text or Buffer) key)

```ts
import { createDecipheriv } from "node:crypto";
function opensslDecrypt(ciphertext: string, algorithm: string, key: string | Buffer, iv?: string | null, aad?: string | null, authTag?: string | null): string {
  const d = createDecipheriv(algorithm, key, iv ? Buffer.from(iv, "base64") : null) as any;
  if (authTag) d.setAuthTag(Buffer.from(authTag, "base64"));
  if (aad != null && algorithm.endsWith("gcm")) d.setAAD(Buffer.from(aad));
  return Buffer.concat([d.update(Buffer.from(ciphertext, "base64")), d.final()]).toString("utf8");
}
```

- Key length must fit the algorithm (16 bytes for aes-128, 32 bytes for aes-256) or Node throws.

## OPENSSL_ENCRYPT

- **Summary:** encrypt text with OpenSSL (AES CBC/GCM/ECB)
- **Signature:** `OPENSSL_ENCRYPT(text, algorithm, key, [aad])`
- **Categories:** Encryption
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/openssl-encrypt/

**Arguments**

- `text` (required): The plaintext.
- `algorithm` (required): The cipher: AES in CBC mode (128- or 256-bit key), GCM mode (256-bit; the one the docs recommend) or ECB mode (128- or 256-bit), written like `"aes-256-gcm"`.
- `key` (required): The encryption key. Its length must fit the cipher, otherwise an error is raised.
- `aad` (optional): Additional authenticated data: not encrypted, but covered by the authentication tag of an authenticated cipher.

**Returns:** Object with base64-encoded values: `encrypted` (the ciphertext), `iv` (if the algorithm supports it), `auth_tag` (for AEAD algorithms). The description also mentions `aad` among the outputs.

**Porting semantics**

- The IV is generated with OpenSSL's cryptographic random number generator, using the standard IV size for the algorithm - a new one per call, so output differs every time.
- Wrong key size raises an error.
- Not specified in docs: key encoding (raw text vs hex/base64); whether `aad` is echoed in the result and in what encoding.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - with a 32-byte key
formula: OPENSSL_ENCRYPT("wire 250 EUR", "aes-256-gcm", key)
output:  an object with base64 `encrypted`, `iv` and `auth_tag` values; different on every call because the IV is random

# 2 - with a 16-byte key - no IV for ECB
formula: OPENSSL_ENCRYPT("wire 250 EUR", "aes-128-ecb", key)
output:  an object with only `encrypted`
```

**TypeScript equivalent** (APPROXIMATE: key is used as raw bytes and `aad` is echoed as given - both assumptions)

```ts
import { createCipheriv, randomBytes } from "node:crypto";
function opensslEncrypt(text: string, algorithm: string, key: string | Buffer, aad?: string) {
  const gcm = algorithm.endsWith("gcm");
  const iv = algorithm.endsWith("ecb") ? null : randomBytes(gcm ? 12 : 16);
  const c = createCipheriv(algorithm, key, iv) as any;
  if (gcm && aad != null) c.setAAD(Buffer.from(aad));
  const encrypted = Buffer.concat([c.update(text, "utf8"), c.final()]).toString("base64");
  return { encrypted, ...(iv ? { iv: iv.toString("base64") } : {}), ...(gcm ? { aad: aad ?? null, auth_tag: c.getAuthTag().toString("base64") } : {}) };
}
```

## RSA_AES_HYBRID_DECRYPT

- **Summary:** decrypt data produced by RSA_AES_HYBRID_ENCRYPT
- **Signature:** `RSA_AES_HYBRID_DECRYPT(encrypted_data_array, key, [padding: "PKCS1_PADDING"])`
- **Categories:** Encryption
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/rsa-aes-hybrid-decrypt/

**Arguments**

- `encrypted_data_array` (required): The three-element array produced by RSA_AES_HYBRID_ENCRYPT.

**Returns:** The decrypted message (text).

**Porting semantics**

- Not specified in docs: the AES mode and key size used internally; encodings of the three array elements; error behaviour.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: RSA_AES_HYBRID_DECRYPT(RSA_AES_HYBRID_ENCRYPT("long report text", public_key), private_key)
output:  "long report text"
(not executed: the Tines wire format is not documented; the helper pair is exercised under RSA_AES_HYBRID_ENCRYPT)
```

**TypeScript equivalent** (APPROXIMATE: the hybrid wire format is Tines-internal; this only decrypts data produced by the matching helper in the RSA_AES_HYBRID_ENCRYPT entry)

```ts
import { constants, createDecipheriv, privateDecrypt } from "node:crypto";
// Counterpart of the helper in the RSA_AES_HYBRID_ENCRYPT entry. NOT compatible with data encrypted by Tines.
function rsaAesHybridDecrypt([encKey, encIv, data]: string[], privateKeyPem: string): string {
  const opts = { key: privateKeyPem, padding: constants.RSA_PKCS1_OAEP_PADDING };
  const key = privateDecrypt(opts, Buffer.from(encKey, "base64")), iv = privateDecrypt(opts, Buffer.from(encIv, "base64"));
  const d = createDecipheriv("aes-256-cbc", key, iv);
  return Buffer.concat([d.update(Buffer.from(data, "base64")), d.final()]).toString("utf8");
}
```

- If the ciphertext comes from a real Tines tenant (or another system built against Tines), this function cannot be ported from the docs alone - flag it for a human.

## RSA_AES_HYBRID_ENCRYPT

- **Summary:** encrypt arbitrary-length data with RSA + AES
- **Signature:** `RSA_AES_HYBRID_ENCRYPT(plain_message, key, [padding: "PKCS1_PADDING"])`
- **Categories:** Encryption
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/rsa-aes-hybrid-encrypt/

**Arguments**

- `plain_message` (required): Data of arbitrary length.
- `key` (required): A public or private RSA key.
- `padding` (optional): Keyword argument: `"PKCS1_PADDING"` (default), `"PKCS1_OAEP_PADDING"` or `"SSLV23_PADDING"`.

**Returns:** An array of three encrypted parts: the AES key, the IV, and the data.

**Porting semantics**

- Not specified in docs: the AES mode and key size used internally; encodings of the three array elements.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: RSA_AES_HYBRID_ENCRYPT("long report text", public_key)
output:  an array of three texts (encrypted key, encrypted IV, encrypted data), different on every call
```

**TypeScript equivalent** (APPROXIMATE: same three-part shape as Tines but an assumed format (AES-256-CBC, RSA-OAEP, base64); not interoperable with Tines)

```ts
import { constants, createCipheriv, publicEncrypt, randomBytes } from "node:crypto";
// Own format; pair it with the helper in the RSA_AES_HYBRID_DECRYPT entry. NOT readable by Tines.
function rsaAesHybridEncrypt(plain: string, publicKeyPem: string): string[] {
  const key = randomBytes(32), iv = randomBytes(16);
  const c = createCipheriv("aes-256-cbc", key, iv);
  const data = Buffer.concat([c.update(plain, "utf8"), c.final()]);
  const opts = { key: publicKeyPem, padding: constants.RSA_PKCS1_OAEP_PADDING };
  return [publicEncrypt(opts, key), publicEncrypt(opts, iv), data].map((b) => b.toString("base64"));
}
```

- If the receiver is a real Tines tenant (or a system built against Tines' format), this function cannot be ported from the docs alone - flag it for a human.

## RSA_DECRYPT

- **Summary:** decrypt data with an RSA key
- **Signature:** `RSA_DECRYPT(encrypted_message, key, [padding: "PKCS1_PADDING"])`
- **Categories:** Encryption
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/rsa-decrypt/

**Arguments**

- `encrypted_message` (required): The encrypted data.
- `key` (required): A public or private key.
- `padding` (optional): Keyword argument: `"PKCS1_PADDING"` (default), `"PKCS1_OAEP_PADDING"` or `"SSLV23_PADDING"`.

**Returns:** The decrypted message (text).

**Porting semantics**

- Not specified in docs: encoding of the encrypted input (base64 assumed); key format (PEM assumed); error behaviour on failure.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: RSA_DECRYPT(RSA_ENCRYPT("pin 4471", public_key, padding: "PKCS1_OAEP_PADDING"), private_key, padding: "PKCS1_OAEP_PADDING")
output:  "pin 4471"
```

**TypeScript equivalent** (APPROXIMATE: input encoding is assumed to be base64; SSLV23_PADDING is not available in current Node/Bun)

```ts
import { constants, privateDecrypt, publicDecrypt } from "node:crypto";
const PAD: Record<string, number> = { PKCS1_PADDING: constants.RSA_PKCS1_PADDING, PKCS1_OAEP_PADDING: constants.RSA_PKCS1_OAEP_PADDING };
const rsaDecrypt = (encrypted: string, key: string, padding = "PKCS1_PADDING"): string =>
  (key.includes("PRIVATE") ? privateDecrypt : publicDecrypt)({ key, padding: PAD[padding] }, Buffer.from(encrypted, "base64")).toString("utf8");
```

- Recent Node versions refuse `RSA_PKCS1_PADDING` for private-key decryption (a security hardening); if the runtime throws, the counterpart must switch to OAEP.

## RSA_ENCRYPT

- **Summary:** encrypt data with an RSA key
- **Signature:** `RSA_ENCRYPT(plain_message, key, [padding: "PKCS1_PADDING"])`
- **Categories:** Encryption
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/rsa-encrypt/

**Arguments**

- `plain_message` (required): The data to encrypt.
- `key` (required): A public or private key.
- `padding` (optional): Keyword argument: `"PKCS1_PADDING"` (default), `"PKCS1_OAEP_PADDING"` or `"SSLV23_PADDING"`.

**Returns:** The encrypted data.

**Porting semantics**

- Not specified in docs: output encoding (base64 assumed); key format (PEM assumed); maximum message size.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: RSA_ENCRYPT("pin 4471", public_key, padding: "PKCS1_OAEP_PADDING")
output:  encrypted data that only the private key can turn back into "pin 4471"; different on every call
```

**TypeScript equivalent** (APPROXIMATE: output encoding is assumed to be base64; SSLV23_PADDING is not available in current Node/Bun)

```ts
import { constants, privateEncrypt, publicEncrypt } from "node:crypto";
const PAD: Record<string, number> = { PKCS1_PADDING: constants.RSA_PKCS1_PADDING, PKCS1_OAEP_PADDING: constants.RSA_PKCS1_OAEP_PADDING };
const rsaEncrypt = (plain: string, key: string, padding = "PKCS1_PADDING"): string =>
  (key.includes("PRIVATE") ? privateEncrypt : publicEncrypt)({ key, padding: PAD[padding] }, Buffer.from(plain, "utf8")).toString("base64");
```

- RSA encryption is randomised: output differs on every call and cannot be compared with a Tines run.
- `privateEncrypt` only supports PKCS1 padding.
