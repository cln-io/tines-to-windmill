# Tines formula functions: Hashing/Signing (part 2 of 2: SHA256_BASE64 to ZSCALER_OBFUSCATE_API_KEY)

Independent, unofficial porting notes for the functions Tines files under "Hashing/Signing": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: SHA256_BASE64, SHA512, ZSCALER_OBFUSCATE_API_KEY

## SHA256_BASE64

- **Summary:** Base64 SHA-256 hash of text
- **Signature:** `SHA256_BASE64(text)`
- **Categories:** Hashing/Signing
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/sha256-base64/

**Arguments**

- `text` (required): Text to hash.

**Returns:** Base64 text of the SHA-256 digest.

**Porting semantics**

- Not specified in docs: non-text input; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: SHA256_BASE64("order:1842")
output:  "nykwjeZfqE7wx60gq8VYAD1D8qNt2r9EH7X1ny5vOZc="
```

**TypeScript equivalent**

```ts
import { createHash } from "node:crypto";
createHash("sha256").update(text).digest("base64")
```

## SHA512

- **Summary:** hex SHA-512 hash of text
- **Signature:** `SHA512(text)`
- **Categories:** Hashing/Signing
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/sha512/

**Arguments**

- `text` (required): Text to hash.

**Returns:** Lowercase hex text of the SHA-512 digest.

**Porting semantics**

- Not specified in docs: non-text input; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: SHA512("order:1842")
output:  "2c1f572da9e1a23a18699dc89928b8cad16581b1c75beee0ddf1d2a2814f47cce8efa1b0c42d5b47fa044d821291ec0a4c3f367510e36de168f1134270f2d7bb"
```

**TypeScript equivalent**

```ts
import { createHash } from "node:crypto";
createHash("sha512").update(text).digest("hex")
```

## ZSCALER_OBFUSCATE_API_KEY

- **Summary:** obfuscate a Zscaler API key with a timestamp
- **Signature:** `ZSCALER_OBFUSCATE_API_KEY(api_key, now)`
- **Categories:** Hashing/Signing
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/zscaler-obfuscate-api-key/

**Arguments**

- `api_key` (required): The Zscaler API key.
- `now` (required): The present time as a millisecond epoch timestamp; the docs build it by formatting NOW() with the seconds and milliseconds directives.

**Returns:** The obfuscated key text, as required by the Zscaler API authentication call.

**Porting semantics**

- The scrambling scheme is the one Zscaler publishes for its API login; the Tines page refers to it without describing it.
- The sample output on the Tines page is a placeholder, not a real result.
- Not specified in docs: the algorithm itself (defined by Zscaler, not on this page).

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - last six digits 123456, halved 061728
formula: ZSCALER_OBFUSCATE_API_KEY("ABCDEFGHIJKLMNOP", "1700000123456")
output:  "BCDEFGCIDJEK"
```

**TypeScript equivalent** (APPROXIMATE: algorithm taken from Zscaler's published API authentication example, not from the Tines page; verify against a real login)

```ts
function zscalerObfuscateApiKey(apiKey: string, now: string | number): string {
  const n = String(now).slice(-6);
  const r = String(Number(n) >> 1).padStart(6, "0");
  let out = "";
  for (const c of n) out += apiKey[Number(c)];
  for (const c of r) out += apiKey[Number(c) + 2];
  return out;
}
// const now = String(Date.now()); send both `now` (as the timestamp) and the obfuscated key to Zscaler.
```

- The same `now` value must be sent to Zscaler as the `timestamp` field of the authentication request.
