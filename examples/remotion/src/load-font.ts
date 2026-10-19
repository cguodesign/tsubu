// Holds the render until the Japanese font has loaded, the FontFace way from Remotion's font
// docs. Put NotoSansJP-Regular.woff2 (or any Japanese font, renamed here) in the project's public/
// folder. Without it the render waits and then times out: to use the system's fonts instead,
// delete this file and its import in TsubuSentence.ts.
import { continueRender, delayRender, staticFile } from "remotion";

export const FONT_FAMILY = "Noto Sans JP";

const waitForFont = delayRender();
const font = new FontFace(FONT_FAMILY, `url('${staticFile("NotoSansJP-Regular.woff2")}') format('woff2')`);

font
  .load()
  .then(() => {
    document.fonts.add(font);
    continueRender(waitForFont);
  })
  .catch((err) => console.log("Error loading font", err));
