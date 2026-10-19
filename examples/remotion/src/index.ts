// The entry point: it registers the root, and nothing else, as Remotion's docs advise.
//   npx remotion studio examples/remotion/src/index.ts
//   npx remotion render examples/remotion/src/index.ts TsubuSentence out.mp4
import { registerRoot } from "remotion";
import { RemotionRoot } from "./Root";

registerRoot(RemotionRoot);
