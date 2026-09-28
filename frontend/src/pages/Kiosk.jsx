import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { apiPostForm, ApiError } from "../api/client";
import "./Kiosk.css";

const BURST_FRAME_COUNT = 10;
const BURST_FRAME_INTERVAL_MS = 140; // ~1.4s per step, long enough to catch a blink or head turn
const READY_PAUSE_MS = 700; // time to read the instruction before capture starts

const CHALLENGES = {
  blink: { label: "Please blink", icon: "👁" },
  left: { label: "Please turn your head to the LEFT", icon: "⬅" },
  right: { label: "Please turn your head to the RIGHT", icon: "➡" },
};

function shuffledChallengeSequence() {
  const keys = Object.keys(CHALLENGES);
  for (let i = keys.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [keys[i], keys[j]] = [keys[j], keys[i]];
  }
  return keys; // all 3, in random order
}

function captureFrameBlob(video, canvas) {
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0);
  return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg"));
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export default function Kiosk() {
  const [searchParams] = useSearchParams();
  const [sessionId, setSessionId] = useState(searchParams.get("session") || "");
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  const [cameraError, setCameraError] = useState(null);
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | ready | capturing | submitting
  const [sequence, setSequence] = useState([]); // e.g. ["right", "blink", "left"]
  const [stepIndex, setStepIndex] = useState(0);
  const [stepError, setStepError] = useState(null); // failure message for the current step, with a retry option
  const [apiError, setApiError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    navigator.mediaDevices
      ?.getUserMedia({ video: { facingMode: "user" } })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
      })
      .catch((err) => setCameraError(err.message));

    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  async function captureBurst(challenge) {
    setStatus("ready");
    await delay(READY_PAUSE_MS);

    setStatus("capturing");
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const blobs = [];
    for (let i = 0; i < BURST_FRAME_COUNT; i++) {
      const blob = await captureFrameBlob(video, canvas);
      if (blob) blobs.push(blob);
      await delay(BURST_FRAME_INTERVAL_MS);
    }

    setStatus("submitting");
    const formData = new FormData();
    formData.append("challenge", challenge);
    blobs.forEach((blob, i) => formData.append("frames", blob, `frame-${i}.jpg`));
    return formData;
  }

  // Runs the sequence starting at `fromIndex` -- used both for a fresh
  // attempt (fromIndex 0) and for retrying just the step that failed.
  async function runSequenceFrom(seq, fromIndex) {
    for (let i = fromIndex; i < seq.length; i++) {
      setStepIndex(i);
      const challenge = seq[i];
      const isFinalStep = i === seq.length - 1;

      try {
        const formData = await captureBurst(challenge);

        if (!isFinalStep) {
          const stepResult = await apiPostForm("/recognize/liveness-step", formData);
          if (!stepResult.passed) {
            setStepError({ index: i, message: stepResult.message });
            setStatus("idle");
            return;
          }
          // passed -- fall through to the next iteration (next step)
        } else {
          formData.append("session_id", sessionId);
          const finalResult = await apiPostForm("/recognize/kiosk-burst", formData);
          if (!finalResult.liveness_passed) {
            setStepError({ index: i, message: finalResult.message });
            setStatus("idle");
            return;
          }
          setResult(finalResult);
          setStatus("idle");
          return;
        }
      } catch (err) {
        setApiError(err instanceof ApiError ? err.detail : "Recognition request failed.");
        setStatus("idle");
        return;
      }
    }
  }

  function handleCapture() {
    if (!sessionId) {
      setApiError("Enter a session ID first.");
      return;
    }
    setApiError(null);
    setResult(null);
    setStepError(null);
    const seq = shuffledChallengeSequence();
    setSequence(seq);
    runSequenceFrom(seq, 0);
  }

  function handleRetryStep() {
    setStepError(null);
    runSequenceFrom(sequence, stepError.index);
  }

  const showingChallenge = status === "ready" || status === "capturing";
  const activeChallenge = sequence[stepIndex];
  const totalSteps = sequence.length;

  return (
    <div className="kiosk">
      <h1>Attendance Check-In</h1>

      <label className="kiosk-session">
        Session ID:{" "}
        <input value={sessionId} onChange={(e) => setSessionId(e.target.value)} placeholder="e.g. 3" />
      </label>

      {cameraError && <p className="form-error">Camera unavailable: {cameraError}</p>}

      <div className="kiosk-video-wrap">
        {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
        <video ref={videoRef} autoPlay playsInline muted className="kiosk-video" />
        <canvas ref={canvasRef} style={{ display: "none" }} />
        {showingChallenge && activeChallenge && (
          <div className="kiosk-challenge-overlay">
            <span className="kiosk-challenge-step">
              Step {stepIndex + 1} of {totalSteps}
            </span>
            <span className="kiosk-challenge-icon">{CHALLENGES[activeChallenge].icon}</span>
            <span>{CHALLENGES[activeChallenge].label}</span>
          </div>
        )}
      </div>

      <p className="kiosk-hint">
        Click below, then follow each on-screen instruction in turn (3 steps total).
      </p>

      <button onClick={handleCapture} disabled={status !== "idle"} className="btn btn-primary">
        {status === "ready" && `Get ready (step ${stepIndex + 1} of ${totalSteps})...`}
        {status === "capturing" && `Capturing (step ${stepIndex + 1} of ${totalSteps})...`}
        {status === "submitting" && "Checking..."}
        {status === "idle" && "Mark my attendance"}
      </button>

      {apiError && <p className="form-error">{apiError}</p>}

      {stepError && (
        <div className="kiosk-face-result status-unrecognized">
          <p>
            Step {stepError.index + 1} of {totalSteps} failed: {stepError.message}
          </p>
          <button onClick={handleRetryStep} className="btn btn-secondary">
            Retry this step
          </button>
        </div>
      )}

      {result?.liveness_passed && result.face && (
        <div className={`kiosk-face-result status-${result.face.attendance_status}`}>
          {result.face.matched ? (
            <p>
              <strong>{result.face.person_name}</strong> —{" "}
              {result.face.attendance_status === "marked" ? "attendance marked" : "already marked today"}
            </p>
          ) : (
            <p>Face not recognized. Please see an administrator if you believe this is an error.</p>
          )}
          {result.face.distance !== null && (
            <p className="kiosk-distance">
              match distance: {result.face.distance.toFixed(4)} (threshold: {result.threshold_used.toFixed(2)})
            </p>
          )}
        </div>
      )}
    </div>
  );
}
