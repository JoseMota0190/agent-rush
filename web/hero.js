/* ============================================================
   AGENT RUSH — landing hero
   Reuses the real 3D escape room in a cinematic camera mode.
   No stock art, no duplicated scene.
   ============================================================ */

import { initScene, setMode, setEnvironmentState } from "./scene.js?v=48";

const canvas = document.getElementById("hero-canvas");
if (canvas) {
  try {
    initScene(canvas, null);
    setMode("hero", true);
    setEnvironmentState("ready");

    // Keep the landing decorative: the real mission state lives in game.html.
    // Slow down the render loop when the hero is off-screen to save GPU.
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver(
        ([entry]) => {
          canvas.style.visibility = entry.isIntersecting ? "visible" : "hidden";
        },
        { threshold: 0.02 }
      );
      io.observe(canvas);
    }
  } catch (err) {
    console.warn("Hero 3D unavailable, using gradient fallback.", err);
    canvas.style.display = "none";
  }
}
