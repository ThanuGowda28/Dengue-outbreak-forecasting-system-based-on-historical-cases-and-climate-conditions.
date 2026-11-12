import { useEffect, useRef, useState } from "react";
import { FiMic, FiMicOff } from "react-icons/fi";
import AlertMessage from "./AlertMessage.jsx";
import { parseVoiceClimateInput } from "../utils/voiceClimateInput.js";

const speechErrorMessages = {
  "not-allowed": "Microphone permission was denied. Allow microphone access and try again.",
  "service-not-allowed": "Speech recognition is blocked by the browser.",
  "audio-capture": "No working microphone was found.",
  "no-speech": "No speech was detected. Try again and speak after listening starts.",
  network: "Browser speech recognition could not reach its recognition service."
};

export default function VoiceClimateInput({ supportedStates, onRecognized }) {
  const recognitionRef = useRef(null);
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [unsupported, setUnsupported] = useState(false);

  useEffect(() => () => {
    recognitionRef.current?.stop();
  }, []);

  function startListening() {
    setError("");
    setMessage("");
    setTranscript("");
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      setUnsupported(true);
      return;
    }
    setUnsupported(false);
    const recognition = new Recognition();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognitionRef.current = recognition;
    recognition.onstart = () => setListening(true);
    recognition.onresult = (event) => {
      const spoken = Array.from(event.results)
        .map((result) => result[0]?.transcript || "")
        .join(" ")
        .trim();
      setTranscript(spoken);
      const parsed = parseVoiceClimateInput(spoken, supportedStates);
      if (Object.keys(parsed.fields).length === 0 && !parsed.state) {
        setMessage("No supported climate fields were recognized. Try the example format below.");
        return;
      }
      onRecognized(parsed);
      setMessage("Recognized values were placed in the form. Review them and submit the climate risk assessment.");
    };
    recognition.onerror = (event) => {
      setError(speechErrorMessages[event.error] || "Speech recognition failed. Try again or enter values manually.");
    };
    recognition.onend = () => {
      setListening(false);
      recognitionRef.current = null;
    };
    try {
      recognition.start();
    } catch {
      setListening(false);
      recognitionRef.current = null;
      setError("Could not start speech recognition. Try again or enter values manually.");
    }
  }

  function stopListening() {
    recognitionRef.current?.stop();
  }

  return (
    <section className="voice-input-panel mb-3" aria-label="Voice climate input">
      <div className="d-flex align-items-center gap-2 flex-wrap">
        <button type="button" className="btn btn-outline-primary" onClick={listening ? stopListening : startListening}>
          {listening ? <><FiMicOff className="me-2" />Stop listening</> : <><FiMic className="me-2" />Speak climate inputs</>}
        </button>
        {listening && <span role="status" aria-live="polite">Listening…</span>}
      </div>
      <p className="small text-secondary mt-2 mb-0">
        Say labelled values, for example: “temperature 28, humidity 70, rainfall 1200,
        wind speed 4, pressure 1008, solar radiation 18, year 2025, state Karnataka.”
      </p>
      <p className="small text-secondary mt-1 mb-0">
        Browser speech recognition may process audio through its configured service. Review every recognized value before submitting.
      </p>
      {unsupported && <AlertMessage variant="warning" message="Speech recognition is not supported by this browser. Enter values in the form instead." />}
      {error && <AlertMessage message={error} />}
      {transcript && <p className="small mt-2 mb-0"><strong>Heard:</strong> {transcript}</p>}
      {message && <p className="small text-success mt-2 mb-0" role="status">{message}</p>}
    </section>
  );
}
