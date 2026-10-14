import assert from "node:assert/strict";
import test from "node:test";
import { parseVoiceClimateInput } from "./voiceClimateInput.js";

const states = ["Karnataka", "Andhra Pradesh", "Himachal Pradesh"];

test("parses spoken climate labels, numeric values, and a supported state", () => {
  assert.deepEqual(
    parseVoiceClimateInput(
      "state of Andhra Pradesh, temperature 28.5, humidity 70, rainfall 1200, wind speed 4.2, pressure 1008, solar radiation 18, year 2025",
      states
    ),
    {
      fields: {
        temperature: "28.5",
        humidity: "70",
        rainfall: "1200",
        wind_speed: "4.2",
        pressure: "1008",
        solar_radiation: "18",
        year: "2025"
      },
      state: "Andhra Pradesh"
    }
  );
});

test("supports alternate labels and partial dictation", () => {
  assert.deepEqual(
    parseVoiceClimateInput("temp 29, wind 5, rain 800, year 2024", states),
    {
      fields: {
        temperature: "29",
        wind_speed: "5",
        rainfall: "800",
        year: "2024"
      },
      state: null
    }
  );
});

test("ignores unknown states, missing numeric values, and unrelated speech", () => {
  assert.deepEqual(
    parseVoiceClimateInput("state Atlantis, humidity high, hello assistant", states),
    { fields: {}, state: null }
  );
  assert.deepEqual(parseVoiceClimateInput("", states), { fields: {}, state: null });
});
