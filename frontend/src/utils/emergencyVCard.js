function unescapeVCard(value) {
  return value
    .replace(/\\n/gi, "\n")
    .replace(/\\([\\;,])/g, "$1");
}

export function createEmergencyVCard(contact) {
  const escape = (value) => String(value)
    .replaceAll("\\", "\\\\")
    .replaceAll(";", "\\;")
    .replaceAll(",", "\\,")
    .replaceAll("\r\n", "\n")
    .replaceAll("\r", "\n")
    .replaceAll("\n", "\\n");
  return `BEGIN:VCARD\nVERSION:3.0\nFN:${escape(contact.name)}\nTEL;TYPE=CELL:${escape(contact.phone)}\nEND:VCARD`;
}

export function parseEmergencyVCard(value) {
  if (typeof value !== "string") return null;
  const lines = value
    .replace(/\r\n[ \t]/g, "")
    .replace(/\r/g, "\n")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines[0]?.toUpperCase() !== "BEGIN:VCARD" || lines.at(-1)?.toUpperCase() !== "END:VCARD") {
    return null;
  }

  let name = "";
  let phone = "";
  for (const line of lines.slice(1, -1)) {
    const separator = line.indexOf(":");
    if (separator < 0) continue;
    const property = line.slice(0, separator).split(";")[0].split(".").at(-1).toUpperCase();
    const propertyValue = unescapeVCard(line.slice(separator + 1));
    if (property === "FN" && !name) name = propertyValue.replace(/[\r\n\t]+/g, " ");
    if (property === "TEL" && !phone) phone = propertyValue;
  }

  const digitCount = [...phone].filter((character) => /\d/.test(character)).length;
  if (
    !name.trim()
    || name.length > 150
    || /[\u0000-\u001f\u007f]/.test(name)
    || !phone.trim()
    || phone.length > 32
    || !/^[0-9+().\-\s]+$/.test(phone)
    || digitCount < 7
    || digitCount > 15
  ) {
    return null;
  }
  return { name: name.trim(), phone: phone.trim() };
}
