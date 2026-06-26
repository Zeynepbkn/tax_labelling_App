import React, { useEffect, useMemo, useState } from "react";
import { formatTime } from "../utils/formatTime";

export default function Timer({ running, resetKey }) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    setSeconds(0);
  }, [resetKey]);

  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [running]);

  const label = useMemo(() => formatTime(seconds), [seconds]);

  return (
    <span className="badge" title="Belge tamamlama süresi">
      Süre: {label}
    </span>
  );
}

export function useTimer(resetKey, initialSeconds = 0, running = true) {
  const [seconds, setSeconds] = useState(initialSeconds);

  useEffect(() => {
    setSeconds(initialSeconds);
  }, [resetKey, initialSeconds]);

  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [running]);

  return { seconds, running, reset: () => setSeconds(initialSeconds) };
}

