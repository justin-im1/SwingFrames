type Mp4Info = {
  videoTracks?: Array<{ duration: number; timescale: number; nb_samples: number }>;
  tracks?: Array<{
    type?: string;
    duration: number;
    timescale: number;
    nb_samples: number;
  }>;
};

type Mp4File = {
  onReady: ((info: Mp4Info) => void) | null;
  onError: ((err: unknown) => void) | null;
  appendBuffer: (buf: ArrayBuffer) => void;
  flush: () => void;
};

export async function detectVideoFps(file: File): Promise<number | null> {
  if (!file.name.toLowerCase().match(/\.(mp4|m4v|mov)$/)) {
    return null;
  }
  try {
    const mod = (await import("mp4box")) as {
      default?: { createFile: () => Mp4File };
      createFile?: () => Mp4File;
    };
    const createFile = mod.createFile ?? mod.default?.createFile;
    if (!createFile) return null;
    const mp4boxFile = createFile();
    return await new Promise((resolve) => {
      mp4boxFile.onError = () => resolve(null);
      mp4boxFile.onReady = (info) => {
        const track =
          info.videoTracks?.[0] ??
          info.tracks?.find((t) => t.type === "video") ??
          info.tracks?.[0];
        if (!track || !track.timescale || !track.nb_samples) {
          resolve(null);
          return;
        }
        const durationSec = track.duration / track.timescale;
        if (durationSec <= 0) {
          resolve(null);
          return;
        }
        resolve(track.nb_samples / durationSec);
      };
      file.arrayBuffer().then((buf) => {
        const data = buf as ArrayBuffer & { fileStart: number };
        data.fileStart = 0;
        mp4boxFile.appendBuffer(data);
        mp4boxFile.flush();
      });
    });
  } catch {
    return null;
  }
}
