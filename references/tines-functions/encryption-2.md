# Tines formula functions: Encryption (part 2 of 2: RSA_SIGN to TINES_ENCRYPT)

Independent, unofficial porting notes for the functions Tines files under "Encryption": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: RSA_SIGN, TINES_DECRYPT, TINES_ENCRYPT

## RSA_SIGN

- **Summary:** sign data with an RSA private key
- **Signature:** `RSA_SIGN(data, key, [digest: "SHA256"])`
- **Categories:** Encryption
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/rsa-sign/

**Arguments**

- `data` (required): The data to sign.
- `key` (required): A private key.
- `digest` (optional): Keyword argument: `"SHA256"` (default), `"SHA384"` or `"SHA512"`.

**Returns:** The signature.

**Porting semantics**

- Not specified in docs: output encoding (base64 assumed); signature padding scheme (PKCS#1 v1.5 assumed); key format (PEM assumed).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: RSA_SIGN("payload-v1", private_key, digest: "SHA512")
output:  a signature that verifies against the matching public key with SHA-512
```

**TypeScript equivalent** (APPROXIMATE: output encoding and padding scheme are assumptions)

```ts
import { sign } from "node:crypto";
const rsaSign = (data: string, key: string, digest = "SHA256"): string => sign(digest, Buffer.from(data, "utf8"), key).toString("base64");
```

- PKCS#1 v1.5 signatures are deterministic, so if the encoding assumption holds the output can be compared with a Tines run.

## TINES_DECRYPT

- **Summary:** decrypt text produced by TINES_ENCRYPT
- **Signature:** `TINES_DECRYPT(encrypted, key)`
- **Categories:** Encryption
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/tines-decrypt/

**Arguments**

- `encrypted` (required): Ciphertext exactly as TINES_ENCRYPT returned it.
- `key` (required): The key, 32 bytes or longer.

**Returns:** The decrypted plaintext.

**Porting semantics**

- Expiry set at encryption time is enforced: decrypting after it has passed fails with an error. Expiry is tracked to the second, and clock differences between systems can shift it slightly.
- Not specified in docs: error behaviour for a wrong key or tampered data (authenticated encryption, so presumably an error).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TINES_DECRYPT(TINES_ENCRYPT("vault code 9", key), key)
output:  "vault code 9"
(not executed: the Tines ciphertext format is not documented; the replacement pair is exercised under TINES_ENCRYPT)
```

**TypeScript equivalent** (APPROXIMATE: the Tines ciphertext format is deliberately abstract; this only decrypts data produced by the helper in the TINES_ENCRYPT entry)

```ts
import { createDecipheriv, createHash } from "node:crypto";
// Counterpart of the helper in the TINES_ENCRYPT entry. NOT compatible with ciphertext produced by Tines.
function decrypt(encrypted: string, key: string): string {
  const raw = Buffer.from(encrypted, "base64");
  const d = createDecipheriv("aes-256-gcm", createHash("sha256").update(key).digest(), raw.subarray(0, 12));
  d.setAuthTag(raw.subarray(12, 28));
  const { t, exp } = JSON.parse(Buffer.concat([d.update(raw.subarray(28)), d.final()]).toString("utf8"));
  if (exp !== null && Math.floor(Date.now() / 1000) >= exp) throw new Error("ciphertext expired");
  return t;
}
```

- Ciphertext created by a real Tines tenant cannot be decrypted outside Tines. Port the encrypting and the decrypting side together, or flag it for a human.

## TINES_ENCRYPT

- **Summary:** encrypt text with Tines' managed authenticated encryption
- **Signature:** `TINES_ENCRYPT(text, key, [expires_in])`
- **Categories:** Encryption
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/tines-encrypt/

**Arguments**

- `text` (required): Plaintext to encrypt.
- `key` (required): Key text, 32 bytes or longer; a longer key is reduced to 32 bytes internally.
- `expires_in` (optional): Keyword argument: lifetime in whole seconds, zero or more. Zero means already expired; a negative value is an error.

**Returns:** Ciphertext text that TINES_DECRYPT will always decrypt.

**Porting semantics**

- Deliberately opaque: authenticated encryption with random IVs, and the only promise is that TINES_DECRYPT can read the output.
- The docs mention, without commitment, that the current implementation is AES-256-GCM with an oversized random IV and an additional HMAC tag.
- When the exact algorithm matters, OPENSSL_ENCRYPT is the function to use.
- Not specified in docs: the output encoding and layout; the key derivation details.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TINES_ENCRYPT("vault code 9", key, expires_in: 300)
output:  opaque ciphertext text, different on every call, that the matching decrypt turns back into "vault code 9"

# 2
formula: TINES_ENCRYPT("x", key, expires_in: -1)
output:  an error is raised
```

**TypeScript equivalent** (APPROXIMATE: self-contained AES-256-GCM replacement with expiry; not wire-compatible with Tines)

```ts
import { createCipheriv, createHash, randomBytes } from "node:crypto";
// Own format; pair it with the helper in the TINES_DECRYPT entry. NOT readable by Tines.
function encrypt(text: string, key: string, expiresIn?: number): string {
  if (expiresIn !== undefined && expiresIn < 0) throw new Error("expires_in must be >= 0");
  const iv = randomBytes(12);
  const c = createCipheriv("aes-256-gcm", createHash("sha256").update(key).digest(), iv);
  const body = JSON.stringify({ t: text, exp: expiresIn === undefined ? null : Math.floor(Date.now() / 1000) + expiresIn });
  const enc = Buffer.concat([c.update(body, "utf8"), c.final()]);
  return Buffer.concat([iv, c.getAuthTag(), enc]).toString("base64");
}
```

- Output differs on every call (random IV).
