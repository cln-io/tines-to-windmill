# Tines formula functions: Hashing/Signing (part 1 of 2: HMAC_SHA1 to SHA256)

Independent, unofficial porting notes for the functions Tines files under "Hashing/Signing": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: HMAC_SHA1, HMAC_SHA1_BASE64, HMAC_SHA256, HMAC_SHA256_BASE64, JWT_DECODE, JWT_SIGN, MD5, MD5_BASE64, SHA1, SHA256

## HMAC_SHA1

- **Summary:** hex HMAC-SHA1 of text
- **Signature:** `HMAC_SHA1(text, secret)`
- **Categories:** Hashing/Signing
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/hmac-sha1/

**Arguments**

- `text` (required): The message.
- `secret` (required): The HMAC secret key.

**Returns:** Lowercase hex text of the HMAC-SHA1 digest.

**Porting semantics**

- Not specified in docs: non-text input; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: HMAC_SHA1("order:1842", "s3cr3t-key")
output:  "4fd92e8acd1d5b1060cd5e2b7b826858c1abdb75"
```

**TypeScript equivalent**

```ts
import { createHmac } from "node:crypto";
createHmac("sha1", secret).update(text).digest("hex")
```

- Argument order flips: Tines is `(text, secret)`, Node is `createHmac(alg, secret).update(text)`.

## HMAC_SHA1_BASE64

- **Summary:** Base64 HMAC-SHA1 of text
- **Signature:** `HMAC_SHA1_BASE64(text, secret)`
- **Categories:** Hashing/Signing
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/hmac-sha1-base64/

**Arguments**

- `text` (required): The message.
- `secret` (required): The HMAC secret key.

**Returns:** Base64 text of the HMAC-SHA1 digest.

**Porting semantics**

- Not specified in docs: non-text input; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: HMAC_SHA1_BASE64("order:1842", "s3cr3t-key")
output:  "T9kuis0dWxBgzV4re4JoWMGr23U="
```

**TypeScript equivalent**

```ts
import { createHmac } from "node:crypto";
createHmac("sha1", secret).update(text).digest("base64")
```

- Argument order flips: Tines is `(text, secret)`, Node is `createHmac(alg, secret).update(text)`.

## HMAC_SHA256

- **Summary:** hex HMAC-SHA256 of text
- **Signature:** `HMAC_SHA256(text, secret)`
- **Categories:** Hashing/Signing
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/hmac-sha256/

**Arguments**

- `text` (required): The message.
- `secret` (required): The HMAC secret key.

**Returns:** Lowercase hex text of the HMAC-SHA256 digest.

**Porting semantics**

- Not specified in docs: non-text input; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: HMAC_SHA256("order:1842", "s3cr3t-key")
output:  "eb1066f20f3048194d06d1adc40a8de2a5fe212ea7f6b247fcd46ff4e3f8fc87"
```

**TypeScript equivalent**

```ts
import { createHmac } from "node:crypto";
createHmac("sha256", secret).update(text).digest("hex")
```

- Argument order flips: Tines is `(text, secret)`, Node is `createHmac(alg, secret).update(text)`.

## HMAC_SHA256_BASE64

- **Summary:** Base64 HMAC-SHA256 of text
- **Signature:** `HMAC_SHA256_BASE64(text, secret)`
- **Categories:** Hashing/Signing
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/hmac-sha256-base64/

**Arguments**

- `text` (required): The message.
- `secret` (required): The HMAC secret key.

**Returns:** Base64 text of the HMAC-SHA256 digest.

**Porting semantics**

- Not specified in docs: non-text input; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: HMAC_SHA256_BASE64("order:1842", "s3cr3t-key")
output:  "6xBm8g8wSBlNBtGtxAqN4qX+IS6n9rJH/NRv9OP4/Ic="
```

**TypeScript equivalent**

```ts
import { createHmac } from "node:crypto";
createHmac("sha256", secret).update(text).digest("base64")
```

- Argument order flips: Tines is `(text, secret)`, Node is `createHmac(alg, secret).update(text)`.

## JWT_DECODE

- **Summary:** decode and optionally verify a JWT
- **Signature:** `JWT_DECODE(token, secret_or_key, algorithm, **options)`
- **Categories:** Hashing/Signing
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/jwt-decode/

**Arguments**

- `token` (required): The JWT text.
- `secret_or_key` (required): HMAC secret, PEM key, or JWK object. `NULL` is allowed when a key set is supplied through the `jwks` option.
- `algorithm` (required): One of HS256/HS384/HS512, RS256/RS384/RS512, ES256/ES384/ES512.
- `**options` (optional): Keyword options with the names used by the Ruby JWT library's decode call: signature and claim switches (`verify`, `verify_expiration`, `verify_not_before`, `verify_iss`, `verify_aud`, `verify_sub`, `verify_jti`), expected values (`iss`, `aud`, `sub`, `jti`, `required_claims`), plus `leeway` and `jwks`.

**Returns:** Object `{payload, header, verified}`.

**Porting semantics**

- With `verify: FALSE` the token is only decoded: the signature is not checked and `verified` is `false`.
- A claim is checked only when both its expected value and its switch are given, e.g. `iss: "my-app", verify_iss: TRUE`.
- Keys may be given as a JWK, or as a JWKS through `jwks:`.
- Not specified in docs: what happens when verification fails (error vs `verified: false`); default values of the verify_* options.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - for a token signed with that secret over {"sub": "u-17"}
formula: JWT_DECODE(token, "s3cr3t-key", "HS256")
output:  {"payload": {"sub": "u-17"}, "header": {"alg": "HS256", "typ": "JWT"}, "verified": true}

# 2
formula: JWT_DECODE(token, "wrong", "HS256", verify: FALSE).verified
output:  false
```

**TypeScript equivalent** (APPROXIMATE: jsonwebtoken option names and failure behaviour differ from the Ruby library)

```ts
import jwt from "jsonwebtoken";
type Opts = { verify?: boolean; verify_expiration?: boolean; leeway?: number;
  iss?: string; verify_iss?: boolean; aud?: string; verify_aud?: boolean; sub?: string; verify_sub?: boolean };
function jwtDecode(token: string, key: string, algorithm: string, o: Opts = {}) {
  const decoded = jwt.decode(token, { complete: true });
  if (!decoded) throw new Error("JWT_DECODE: malformed token");
  if (o.verify === false) return { payload: decoded.payload, header: decoded.header, verified: false };
  const payload = jwt.verify(token, key, {
    algorithms: [algorithm as jwt.Algorithm], clockTolerance: o.leeway, ignoreExpiration: o.verify_expiration === false,
    issuer: o.verify_iss ? o.iss : undefined, audience: o.verify_aud ? o.aud : undefined, subject: o.verify_sub ? o.sub : undefined,
  });
  return { payload, header: decoded.header, verified: true };
}
```

- npm package: `jsonwebtoken` (throws on a bad signature or failed claim).
- For a JWK key convert first: `createPublicKey({ key: jwk, format: "jwk" })` from `node:crypto`. For a JWKS pick the key whose `kid` equals `decoded.header.kid`.

## JWT_SIGN

- **Summary:** create a signed JSON Web Token
- **Signature:** `JWT_SIGN(claim_set, key, [algorithm=RS256], [headers])`
- **Categories:** Hashing/Signing
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/jwt-sign/

**Arguments**

- `claim_set` (required): The payload object: registered claims such as `sub`, `iss` or `exp`, and any custom ones.
- `key` (required): HMAC secret, PEM key, or JWK object (RSA and ECDSA).
- `algorithm` (optional): Default `RS256`. HS256/HS384/HS512, RS256/RS384/RS512, ES256/ES384/ES512.
- `headers` (optional): Object of extra header fields such as `kid` or `typ`.

**Returns:** The JWT text (`header.payload.signature`, base64url).

**Porting semantics**

- With an HMAC algorithm and no extra headers, the token header holds only `alg` and the payload is exactly the claim set: nothing such as `iat` is added.
- Extra values may also be passed by name after the positional arguments; in the docs' outputs a claim such as `exp` ends up in the payload and `kid` in the header.
- Some docs outputs show a `typ` header that was not passed and a placeholder signature, so they cannot be used to pin down header contents exactly.
- Not specified in docs: header field order; whether `typ` is added automatically; how keyword arguments are split between payload and header.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - header, payload and verification
formula: JWT_SIGN({sub: "u-17"}, "s3cr3t-key", "HS256")
output:  {"header": {"alg": "HS256"}, "payload": {"sub": "u-17"}, "signature_ok": true}

# 2 - first segment decoded
formula: JWT_SIGN({sub: "u-17"}, "s3cr3t-key", "HS256", {kid: "k1"})
output:  {"alg": "HS256", "kid": "k1"}
```

**TypeScript equivalent**

```ts
import { createHmac, createSign } from "node:crypto";
function jwtSign(claims: object, key: string, algorithm = "RS256", headers: object = {}): string {
  const b64u = (v: unknown) => Buffer.from(JSON.stringify(v)).toString("base64url");
  const head = `${b64u({ alg: algorithm, ...headers })}.${b64u(claims)}`;
  const bits = algorithm.slice(2);
  const sig = algorithm.startsWith("HS")
    ? createHmac(`sha${bits}`, key).update(head).digest("base64url")
    : createSign(`SHA${bits}`).update(head).sign(algorithm.startsWith("ES") ? { key, dsaEncoding: "ieee-p1363" } : key, "base64url");
  return `${head}.${sig}`;
}
```

- The HS256 path reproduces a documented Tines token byte for byte. RSA/ECDSA paths expect a PEM key; convert a JWK with `createPrivateKey({ key: jwk, format: "jwk" })`.
- `exp`/`iat` claims are unix seconds: `Math.floor(Date.now() / 1000) + 86400` for "one day from now".
- npm `jsonwebtoken.sign` adds `iat` and `typ` by default, so its output differs from Tines' unless `noTimestamp: true` is set and the header is trimmed.

## MD5

- **Summary:** hex MD5 hash of text
- **Signature:** `MD5(text)`
- **Categories:** Hashing/Signing
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/md5/

**Arguments**

- `text` (required): Text to hash.

**Returns:** Lowercase hex text of the MD5 digest.

**Porting semantics**

- Not specified in docs: non-text input; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: MD5("order:1842")
output:  "d5328cbfdcf1cb8a05cb6cf027f0376c"
```

**TypeScript equivalent**

```ts
import { createHash } from "node:crypto";
createHash("md5").update(text).digest("hex")
```

## MD5_BASE64

- **Summary:** Base64 MD5 hash of text
- **Signature:** `MD5_BASE64(text)`
- **Categories:** Hashing/Signing
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/md5-base64/

**Arguments**

- `text` (required): Text to hash.

**Returns:** Base64 text of the MD5 digest.

**Porting semantics**

- Not specified in docs: non-text input; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: MD5_BASE64("order:1842")
output:  "1TKMv9zxy4oFy2zwJ/A3bA=="
```

**TypeScript equivalent**

```ts
import { createHash } from "node:crypto";
createHash("md5").update(text).digest("base64")
```

## SHA1

- **Summary:** hex SHA-1 hash of text
- **Signature:** `SHA1(text)`
- **Categories:** Hashing/Signing
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/sha1/

**Arguments**

- `text` (required): Text to hash.

**Returns:** Lowercase hex text of the SHA-1 digest.

**Porting semantics**

- Not specified in docs: non-text input; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: SHA1("order:1842")
output:  "59d105c2437db8f53745be6ba27839ad05410747"
```

**TypeScript equivalent**

```ts
import { createHash } from "node:crypto";
createHash("sha1").update(text).digest("hex")
```

## SHA256

- **Summary:** hex SHA-256 hash of text
- **Signature:** `SHA256(text)`
- **Categories:** Hashing/Signing
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/sha256/

**Arguments**

- `text` (required): Text to hash.

**Returns:** Lowercase hex text of the SHA-256 digest.

**Porting semantics**

- Not specified in docs: non-text input; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: SHA256("order:1842")
output:  "9f29308de65fa84ef0c7ad20abc558003d43f2a36ddabf441fb5f59f2e6f3997"
```

**TypeScript equivalent**

```ts
import { createHash } from "node:crypto";
createHash("sha256").update(text).digest("hex")
```
