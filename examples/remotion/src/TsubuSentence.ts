// One tsubu sentence as a Remotion component. Each frame is a pure function of the frame number:
// t = from + frame / fps, and the frame is s.htmlAt(t), written whole into a fresh element. Nothing
// is carried from one frame to the next, so Remotion may render the frames in any order, or in
// parallel.
//
// Written with createElement rather than JSX so that tsubu's tests can parse it with Node's
// built-in TypeScript type stripping. In a .tsx file the component reads as JSX the same way.
import { createElement } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import "../../../tsubu.css";
import { FONT_FAMILY } from "./load-font";
// @ts-ignore: tsubu.js is a plain script without type declarations
import Tsubu from "../../../tsubu.js";
// @ts-ignore: as is tsubu-frames.js
import TsubuFrames from "../../tsubu-frames.js";
import input from "../../sentence.json";

export const FPS = 30;
const PAD = 0.5; // seconds shown before the first segment and after the last

const s = Tsubu.sentence(input, { theme: "light" });
const from: number = TsubuFrames.span(input).start - PAD;
export const DURATION_IN_FRAMES: number = TsubuFrames.frameCount(input, FPS, PAD);

export const TsubuSentence = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const html: string = TsubuFrames.htmlAtFrame(s, frame, fps, from);
  return createElement(
    AbsoluteFill,
    { style: { justifyContent: "center", alignItems: "center", background: "#ffffff", fontFamily: `"${FONT_FAMILY}", sans-serif`, fontSize: 96 } },
    createElement("div", { dangerouslySetInnerHTML: { __html: html } }),
  );
};
