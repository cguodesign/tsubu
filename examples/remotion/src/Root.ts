// The composition: its length in frames comes from the sentence's own times, so the video ends
// PAD seconds after the last segment does.
import { createElement } from "react";
import { Composition } from "remotion";
import { DURATION_IN_FRAMES, FPS, TsubuSentence } from "./TsubuSentence";

export const RemotionRoot = () =>
  createElement(Composition, {
    id: "TsubuSentence",
    component: TsubuSentence,
    durationInFrames: DURATION_IN_FRAMES,
    fps: FPS,
    width: 1920,
    height: 1080,
  });
