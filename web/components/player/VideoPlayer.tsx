"use client";

import { useEffect, useRef, type CSSProperties } from "react";

export function seekTime(frame: number, fps: number): number {
  return (frame + 0.5) / fps;
}

export function clampFrame(frame: number, frameCount: number): number {
  return Math.max(0, Math.min(Math.max(frameCount - 1, 0), frame));
}

type Props = {
  src: string;
  fps: number;
  frameCount: number;
  seekFrame: number;
  seekToken: number;
  onPresentedFrame?: (frame: number) => void;
  className?: string;
  style?: CSSProperties;
  muted?: boolean;
};

export function VideoPlayer({
  src,
  fps,
  frameCount,
  seekFrame,
  seekToken,
  onPresentedFrame,
  className,
  style,
  muted = true,
}: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const presentedRef = useRef(onPresentedFrame);
  presentedRef.current = onPresentedFrame;

  useEffect(() => {
    const video = videoRef.current;
    if (!video || fps <= 0) return;
    if (!video.paused) video.pause();
    video.currentTime = seekTime(clampFrame(seekFrame, frameCount), fps);
  }, [seekToken, seekFrame, fps, frameCount]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    let handle: number | null = null;
    let stopped = false;

    const emit = (mediaTime: number) => {
      const f = clampFrame(Math.round(mediaTime * fps), frameCount);
      presentedRef.current?.(f);
    };

    const onVfc = (_now: number, meta: VideoFrameCallbackMetadata) => {
      emit(meta.mediaTime);
      if (!stopped && video.requestVideoFrameCallback) {
        handle = video.requestVideoFrameCallback(onVfc);
      }
    };
    const onTime = () => emit(video.currentTime);

    if (typeof video.requestVideoFrameCallback === "function") {
      handle = video.requestVideoFrameCallback(onVfc);
    } else {
      video.addEventListener("timeupdate", onTime);
      video.addEventListener("seeked", onTime);
    }
    return () => {
      stopped = true;
      if (handle != null && video.cancelVideoFrameCallback) {
        video.cancelVideoFrameCallback(handle);
      }
      video.removeEventListener("timeupdate", onTime);
      video.removeEventListener("seeked", onTime);
    };
  }, [src, fps, frameCount]);

  return (
    <video
      ref={videoRef}
      src={src}
      className={className}
      style={style}
      muted={muted}
      playsInline
      preload="auto"
    />
  );
}
