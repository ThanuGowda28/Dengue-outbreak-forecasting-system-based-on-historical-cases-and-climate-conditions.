import assert from "node:assert/strict";
import test from "node:test";
import { createEmergencyVCard, parseEmergencyVCard } from "./emergencyVCard.js";

test("creates and parses a vCard emergency contact", () => {
  const card = createEmergencyVCard({ name: "Alex Example", phone: "+1 555 123 4567" });
  assert.deepEqual(parseEmergencyVCard(card), {
    name: "Alex Example",
    phone: "+1 555 123 4567"
  });
});

test("escapes vCard delimiters and line breaks", () => {
  const card = createEmergencyVCard({
    name: "Alex; Example\nSecond line",
    phone: "+1 555 123 4567"
  });
  assert.match(card, /FN:Alex\\; Example\\nSecond line/);
  assert.equal(parseEmergencyVCard(card)?.name, "Alex; Example Second line");
});

test("rejects non-vCard and invalid emergency contact payloads", () => {
  assert.equal(parseEmergencyVCard("https://example.test"), null);
  assert.equal(
    parseEmergencyVCard("BEGIN:VCARD\nVERSION:3.0\nFN:Alex\nTEL:12\nEND:VCARD"),
    null
  );
  assert.equal(
    parseEmergencyVCard("BEGIN:VCARD\nVERSION:3.0\nTEL:5551234567\nEND:VCARD"),
    null
  );
});
