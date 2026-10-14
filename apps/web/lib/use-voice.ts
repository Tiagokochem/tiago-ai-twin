"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";

const noopSubscribe = () => () => {};

const MIME_TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];

export type VoiceError = "unsupported" | "denied";

/** Microphone recording and audio playback, both exposing a 0..1 level for the orb. */
export function useVoice() {
  const [recording, setRecording] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [level, setLevel] = useState(0);
  const ctxRef = useRef<AudioContext | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const frameRef = useRef<number>(0);

  const context = useCallback(() => {
    ctxRef.current ??= new AudioContext();
    if (ctxRef.current.state === "suspended") void ctxRef.current.resume();
    return ctxRef.current;
  }, []);

  const meter = useCallback((analyser: AnalyserNode) => {
    const data = new Uint8Array(analyser.fftSize);
    let last = 0;
    const tick = (time: number) => {
      if (time - last > 50) {
        analyser.getByteTimeDomainData(data);
        let sum = 0;
        for (const v of data) sum += ((v - 128) / 128) ** 2;
        setLevel(Math.min(1, Math.sqrt(sum / data.length) * 4));
        last = time;
      }
      frameRef.current = requestAnimationFrame(tick);
    };
    cancelAnimationFrame(frameRef.current);
    frameRef.current = requestAnimationFrame(tick);
  }, []);

  const stopMeter = useCallback(() => {
    cancelAnimationFrame(frameRef.current);
    setLevel(0);
  }, []);

  const supported = useSyncExternalStore(
    noopSubscribe,
    () => !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== "undefined",
    () => false,
  );

  const startRecording = useCallback(async (): Promise<VoiceError | null> => {
    if (!supported) return "unsupported";
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    } catch {
      return "denied";
    }
    streamRef.current = stream;
    const mimeType = MIME_TYPES.find((t) => MediaRecorder.isTypeSupported(t));
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    recorderRef.current = recorder;
    recorder.start();

    const ctx = context();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 512;
    ctx.createMediaStreamSource(stream).connect(analyser);
    meter(analyser);
    setRecording(true);
    return null;
  }, [supported, context, meter]);

  const stopRecording = useCallback(async (): Promise<Blob | null> => {
    const recorder = recorderRef.current;
    if (!recorder) return null;
    const chunks: Blob[] = [];
    const done = new Promise<Blob>((resolve) => {
      recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      recorder.onstop = () => resolve(new Blob(chunks, { type: recorder.mimeType || "audio/webm" }));
    });
    recorder.stop();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    recorderRef.current = null;
    stopMeter();
    setRecording(false);
    return done;
  }, [stopMeter]);

  const stopPlayback = useCallback(() => {
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.dispatchEvent(new Event("ended"));
    }
  }, []);

  const play = useCallback(
    (blob: Blob) =>
      new Promise<void>((resolve) => {
        stopPlayback();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audioRef.current = audio;
        const ctx = context();
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 512;
        const source = ctx.createMediaElementSource(audio);
        source.connect(analyser);
        analyser.connect(ctx.destination);
        let settled = false;
        const finish = () => {
          if (settled) return;
          settled = true;
          source.disconnect();
          URL.revokeObjectURL(url);
          if (audioRef.current === audio) audioRef.current = null;
          stopMeter();
          setPlaying(false);
          resolve();
        };
        audio.addEventListener("ended", finish, { once: true });
        audio.onerror = finish;
        setPlaying(true);
        meter(analyser);
        audio.play().catch(finish);
      }),
    [context, meter, stopMeter, stopPlayback],
  );

  useEffect(
    () => () => {
      cancelAnimationFrame(frameRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      audioRef.current?.pause();
      void ctxRef.current?.close();
    },
    [],
  );

  return { supported, recording, playing, level, startRecording, stopRecording, play, stopPlayback };
}
