# Tines formula functions: IP Addresses

Independent, unofficial porting notes for the functions Tines files under "IP Addresses": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: IN_CIDR, IS_IPV4, IS_IPV6, IS_IP_ADDRESS

## IN_CIDR

- **Summary:** check whether IP address(es) are in a CIDR block
- **Signature:** `IN_CIDR(ip_address, cidr_range)`
- **Categories:** IP Addresses
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/in-cidr/

**Arguments**

- `ip_address` (required): One IP address as text, or an array of addresses.
- `cidr_range` (required): The network block in CIDR notation, e.g. `"172.16.0.0/12"`.

**Returns:** Boolean. For an array the result is true only when all of its addresses fall inside the block.

**Porting semantics**

- Not specified in docs: empty list; invalid IP or CIDR text; an IPv6 address tested against an IPv4 block (no example).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: IN_CIDR("172.20.4.9", "172.16.0.0/12")
output:  true

# 2
formula: IN_CIDR(["172.20.4.9", "8.8.4.4"], "172.16.0.0/12")
output:  false
```

**TypeScript equivalent**

```ts
import ipaddr from "ipaddr.js";
const inCidr = (ip: string | string[], cidr: string): boolean =>
  [ip].flat().every((a) => ipaddr.parse(a).match(ipaddr.parseCIDR(cidr)));
```

- npm package: `ipaddr.js` (IPv4 and IPv6). It throws on text that is not an IP address and when address and block are of different families; Tines behaviour for those inputs is not specified.
- `every` on an empty list returns true - Tines behaviour for an empty list is not specified.

## IS_IPV4

- **Summary:** check that text is a valid IPv4 address
- **Signature:** `IS_IPV4(text)`
- **Categories:** IP Addresses, Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/is-ipv4/

**Arguments**

- `text` (required): Text to check.

**Returns:** Boolean.

**Porting semantics**

- Not specified in docs: whether a CIDR suffix is accepted; null input; list input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: IS_IPV4("203.0.113.9")
output:  true

# 2
formula: IS_IPV4("fe80::1")
output:  false
```

**TypeScript equivalent**

```ts
import { isIPv4 } from "node:net";
isIPv4(text)
```

## IS_IPV6

- **Summary:** check that text is a valid IPv6 address
- **Signature:** `IS_IPV6(text)`
- **Categories:** IP Addresses, Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/is-ipv6/

**Arguments**

- `text` (required): Text to check.

**Returns:** Boolean.

**Porting semantics**

- Not specified in docs: whether a CIDR suffix or zone id is accepted; null input; list input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: IS_IPV6("fe80::1")
output:  true

# 2
formula: IS_IPV6("203.0.113.9")
output:  false
```

**TypeScript equivalent**

```ts
import { isIPv6 } from "node:net";
isIPv6(text)
```

## IS_IP_ADDRESS

- **Summary:** check that text is a valid IP address
- **Signature:** `IS_IP_ADDRESS(text, [strict: FALSE])`
- **Categories:** IP Addresses
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/is-ip-address/

**Arguments**

- `text` (required): A single value to check.
- `strict` (optional): Keyword argument, off by default. When on, only one plain IPv4 or IPv6 host address in canonical form passes.

**Returns:** Boolean.

**Porting semantics**

- In the default mode an address with a CIDR prefix length or an IPv6 zone identifier also passes; in strict mode neither does.
- Only one value is checked per call. An array raises an error in the default mode and gives false in strict mode; map over the array with MAP_LAMBDA instead.
- Not specified in docs: what "canonical" excludes exactly; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: IS_IP_ADDRESS("203.0.113.9")
output:  true

# 2
formula: IS_IP_ADDRESS("203.0.113.0/26")
output:  true

# 3
formula: IS_IP_ADDRESS("203.0.113.0/26", strict: TRUE)
output:  false
```

**TypeScript equivalent** (APPROXIMATE: "canonical" is interpreted as "plain address without prefix or zone")

```ts
import { isIP } from "node:net";
function isIpAddress(text: unknown, strict = false): boolean {
  if (typeof text !== "string") { if (strict) return false; throw new Error("address family must be specified"); }
  if (strict) return isIP(text) !== 0 && !text.includes("%");
  const [addr, prefix, ...rest] = text.split("/");
  const fam = isIP(addr);
  return fam !== 0 && rest.length === 0 && (prefix === undefined || (/^\d+$/.test(prefix) && Number(prefix) <= (fam === 4 ? 32 : 128)));
}
```
