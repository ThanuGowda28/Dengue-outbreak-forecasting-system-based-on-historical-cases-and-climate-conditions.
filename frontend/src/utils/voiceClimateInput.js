const labels = [
  ["solar_radiation", ["solar radiation", "solar"]],
  ["wind_speed", ["wind speed", "wind"]],
  ["temperature", ["temperature", "temp"]],
  ["humidity", ["humidity"]],
  ["rainfall", ["rainfall", "rain"]],
  ["pressure", ["pressure"]],
  ["year", ["observation year", "year"]],
  ["state", ["state"]]
];

const markerPattern = new RegExp(
  `\\b(${labels.flatMap(([, aliases]) => aliases)
    .sort((left, right) => right.length - left.length)
    .map((alias) => alias.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\\ /g, "\\s+"))
    .join("|")})\\b`,
  "gi"
);

function normalizedWords(value) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim().replace(/\s+/g, " ");
}

export function parseVoiceClimateInput(transcript, supportedStates = []) {
  if (typeof transcript !== "string" || !transcript.trim()) {
    return { fields: {}, state: null };
  }

  const matches = [...transcript.matchAll(markerPattern)];
  const fields = {};
  let state = null;
  for (let index = 0; index < matches.length; index += 1) {
    const match = matches[index];
    const label = match[0].toLowerCase().replace(/\s+/g, " ");
    const entry = labels.find(([, aliases]) => aliases.includes(label));
    if (!entry) continue;
    const [field] = entry;
    const valueStart = match.index + match[0].length;
    const valueEnd = matches[index + 1]?.index ?? transcript.length;
    const spokenValue = transcript.slice(valueStart, valueEnd).replace(/^[\s:,-]+|[\s,;.!]+$/g, "");
    if (field === "state") {
      const normalizedValue = normalizedWords(spokenValue).replace(/^of\s+/, "");
      state = supportedStates
        .slice()
        .sort((left, right) => right.length - left.length)
        .find((candidate) => {
          const normalizedCandidate = normalizedWords(candidate);
          return normalizedValue === normalizedCandidate
            || normalizedValue.startsWith(`${normalizedCandidate} `);
        }) || null;
      continue;
    }
    const number = spokenValue.match(/-?\d+(?:\.\d+)?/);
    if (number) fields[field] = number[0];
  }
  return { fields, state };
}
