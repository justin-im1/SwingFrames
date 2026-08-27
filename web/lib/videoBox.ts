export type Box = { left: number; top: number; width: number; height: number };

export function displayedVideoBox(
  container: DOMRect,
  intrinsicW: number,
  intrinsicH: number
): Box {
  if (intrinsicW <= 0 || intrinsicH <= 0) {
    return {
      left: container.left,
      top: container.top,
      width: container.width,
      height: container.height,
    };
  }
  const ar = intrinsicW / intrinsicH;
  const car = container.width / container.height;
  if (car > ar) {
    const height = container.height;
    const width = height * ar;
    return {
      left: container.left + (container.width - width) / 2,
      top: container.top,
      width,
      height,
    };
  }
  const width = container.width;
  const height = width / ar;
  return {
    left: container.left,
    top: container.top + (container.height - height) / 2,
    width,
    height,
  };
}

export function toNormalized(
  clientX: number,
  clientY: number,
  box: Box
): { x: number; y: number } {
  return {
    x: (clientX - box.left) / box.width,
    y: (clientY - box.top) / box.height,
  };
}

export function toCanvas(
  p: { x: number; y: number },
  box: { width: number; height: number }
): { x: number; y: number } {
  return { x: p.x * box.width, y: p.y * box.height };
}
