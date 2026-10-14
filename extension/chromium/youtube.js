// YDM - tombol unduh di halaman video YouTube (content script)
(function () {
  "use strict";
  const QUALITIES = [
    { q: "1080", label: "1080p" },
    { q: "720", label: "720p" },
    { q: "480", label: "480p" },
    { q: "360", label: "360p" },
    { q: "best", label: "Terbaik" },
    { q: "audio", label: "Audio MP3" }
  ];
  let lastVideoId = "";

  function videoId() {
    const u = new URL(location.href);
    if (u.hostname === "youtu.be") return u.pathname.slice(1);
    if (u.pathname.startsWith("/shorts/")) return u.pathname.split("/")[2] || "";
    return u.searchParams.get("v") || "";
  }

  function canonicalUrl() {
    const id = videoId();
    return id ? `https://www.youtube.com/watch?v=${id}` : location.href;
  }

  function findAnchor() {
    return (
      document.querySelector("ytd-watch-metadata #actions") ||
      document.querySelector("#above-the-fold #actions") ||
      document.querySelector("ytd-video-primary-info-renderer #info") ||
      document.querySelector("#info-contents")
    );
  }

  function buildUI() {
    const wrap = document.createElement("div");
    wrap.className = "ydm-wrap";
    const btn = document.createElement("button");
    btn.className = "ydm-btn";
    btn.type = "button";
    btn.textContent = "Unduh dengan YDM";
    const panel = document.createElement("div");
    panel.className = "ydm-panel";
    panel.hidden = true;
    const title = document.createElement("div");
    title.className = "ydm-panel-title";
    title.textContent = "Pilih kualitas:";
    panel.appendChild(title);
    const status = document.createElement("div");
    status.className = "ydm-status";
    for (const item of QUALITIES) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "ydm-q";
      b.textContent = item.label;
      b.addEventListener("click", () => {
        status.textContent = "Mengirim ke YDM...";
        chrome.runtime.sendMessage(
          { type: "ydm-youtube", url: canonicalUrl(), quality: item.q },
          (resp) => {
            status.textContent = resp && resp.ok
              ? "Terkirim. Unduhan berjalan di aplikasi YDM."
              : "Gagal: aplikasi YDM / native host belum siap.";
          }
        );
      });
      panel.appendChild(b);
    }
    panel.appendChild(status);
    btn.addEventListener("click", () => { panel.hidden = !panel.hidden; });
    wrap.appendChild(btn);
    wrap.appendChild(panel);
    return wrap;
  }

  function inject() {
    const id = videoId();
    if (!id) return;
    if (id === lastVideoId && document.querySelector(".ydm-wrap")) return;
    lastVideoId = id;
    const old = document.querySelector(".ydm-wrap");
    if (old) old.remove();
    const anchor = findAnchor();
    if (!anchor) return;
    anchor.appendChild(buildUI());
  }

  setInterval(inject, 1200);
  document.addEventListener("yt-navigate-finish", () => { lastVideoId = ""; inject(); });
  inject();
})();
