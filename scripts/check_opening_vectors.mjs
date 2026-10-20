// Independent fixture encoder/hash check. This is not a production decoder or verifier.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

const raw = readFileSync(process.argv[2] ?? new URL("../fixtures/wire/openings-v1.json", import.meta.url));
const vectors = JSON.parse(raw);
assert.equal(vectors.schema_id, "hallmark/opening-vectors/1");
const sha256 = (bytes) => createHash("sha256").update(bytes).digest();
function hex(value) {
  assert.equal(typeof value, "string");
  assert.match(value, /^(?:[0-9a-f]{2})*$/);
  return Buffer.from(value, "hex");
}
function header(major, value) {
  const n = BigInt(value);
  assert(n >= 0n && n < (1n << 64n));
  if (n < 24n) return Buffer.from([major * 32 + Number(n)]);
  const size = n <= 0xffn ? 1 : n <= 0xffffn ? 2 : n <= 0xffffffffn ? 4 : 8;
  const result = Buffer.alloc(1 + size);
  result[0] = major * 32 + (size === 1 ? 24 : size === 2 ? 25 : size === 4 ? 26 : 27);
  for (let i = 0; i < size; i++) result[size - i] = Number((n >> BigInt(8 * i)) & 255n);
  return result;
}
function cbor(value) {
  if (value === null) return Buffer.from([0xf6]);
  if (typeof value === "boolean") return Buffer.from([value ? 0xf5 : 0xf4]);
  if (typeof value === "number") {
    assert(Number.isSafeInteger(value));
    return cbor(BigInt(value));
  }
  if (typeof value === "bigint") {
    assert(value >= -(1n << 63n));
    return value >= 0n ? header(0, value) : header(1, -1n - value);
  }
  if (Buffer.isBuffer(value)) return Buffer.concat([header(2, value.length), value]);
  if (typeof value === "string") {
    const bytes = Buffer.from(value, "utf8");
    assert.equal(bytes.toString("utf8"), value);
    return Buffer.concat([header(3, bytes.length), bytes]);
  }
  if (Array.isArray(value)) return Buffer.concat([header(4, value.length), ...value.map(cbor)]);
  assert(value && Object.getPrototypeOf(value) === Object.prototype);
  const entries = Object.entries(value).map(([key, item]) => [cbor(key), cbor(item)]);
  entries.sort(([a], [b]) => a.length - b.length || Buffer.compare(a, b));
  return Buffer.concat([header(5, entries.length), ...entries.flat()]);
}
function hash(domain, value) {
  const tag = Buffer.from(`hallmark/v1/${domain}`, "ascii");
  const length = Buffer.alloc(4);
  length.writeUInt32BE(tag.length);
  return sha256(Buffer.concat([length, tag, cbor(value)]));
}
const byteFields = new Set([
  "system_ref", "salt", "nonce", "interaction_id", "model", "policy", "previous",
  "sha256", "rubric", "program", "weights", "tokenizer", "input_profile", "arithmetic",
  "backend", "verifier_key", "setup",
]);
function fromProjection(value, key = "") {
  if (value === null) return null;
  if (byteFields.has(key)) return hex(value);
  if (key === "classifiers") return value.map(hex);
  if (Array.isArray(value)) return value.map((item) => fromProjection(item));
  if (typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([name, item]) => [name, fromProjection(item, name)]));
  }
  return value;
}
function record(vector, domain) {
  const value = fromProjection(vector.json);
  assert.equal(cbor(value).toString("hex"), vector.cbor_hex);
  if (domain) assert.equal(hash(domain, value).toString("hex"), vector.identity_hex);
  return value;
}
const expected = record(vectors.expected);
const policy = record(vectors.policy, "policy");
assert.deepEqual(hash("policy", policy), expected.policy);
const profiles = Object.fromEntries(
  Object.entries(vectors.profiles).map(([name, item]) => [name, record(item, "input-profile")]),
);
const classifiers = Object.fromEntries(
  Object.entries(vectors.classifiers).map(([name, item]) => [name, record(item, "classifier")]),
);
assert.deepEqual(policy.classifiers, ["rule", "mlp", "encoder"].map((kind) => hash("classifier", classifiers[kind])));
const decimal = (value) => {
  assert.equal(typeof value, "string");
  assert.match(value, /^(0|[1-9][0-9]*)$/);
  return BigInt(value);
};
let inputCount = 0;
for (const item of vectors.cases) {
  const opening = record(item.opening);
  const transcript = [opening.system_ref, opening.salt, Buffer.from(opening.prompt, "utf8"), Buffer.from(opening.response, "utf8")];
  assert.equal(cbor(transcript).toString("hex"), item.transcript_preimage_cbor_hex);
  const digest = hash("transcript", transcript);
  assert.equal(digest.toString("hex"), item.transcript_hex);
  const context = [expected, digest];
  assert.equal(cbor(context).toString("hex"), item.context_preimage_cbor_hex);
  assert.equal(hash("context", context).toString("hex"), item.context_hex);
  for (const input of item.inputs) {
    const classifier = classifiers[input.classifier];
    const profile = profiles[input.profile];
    const profileDigest = hash("input-profile", profile);
    assert.deepEqual(classifier.input_profile, profileDigest);
    const units = input.units_decimal.map(decimal);
    if (profile.encoding === "utf8-bytes") {
      assert.deepEqual(units, [...Buffer.from(opening.prompt, "utf8")].map(BigInt));
    } else {
      const bound = decimal(input.vocabulary_size_decimal);
      assert(units.every((unit) => unit < bound));
    }
    const saltPreimage = [opening.salt, hash("classifier", classifier)];
    const salt = hash("input-salt", saltPreimage);
    assert.equal(cbor(saltPreimage).toString("hex"), input.salt_preimage_cbor_hex);
    assert.equal(salt.toString("hex"), input.salt_hex);
    const preimage = [salt, profileDigest, units.length, units];
    assert.equal(cbor(preimage).toString("hex"), input.input_preimage_cbor_hex);
    assert.equal(hash("input", preimage).toString("hex"), input.digest_hex);
    inputCount++;
  }
}
assert(vectors.cases.length > 0 && inputCount > 0);
console.log(JSON.stringify({
  schema_id: "hallmark/cross-language-check/1", status: "passed",
  transcripts: vectors.cases.length, inputs: inputCount, node: process.version,
  vector_sha256: sha256(raw).toString("hex"),
}));
