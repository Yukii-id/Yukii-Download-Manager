// YDM extension - service worker (Chromium MV3)
const HOST = "id.yukii.ydm";
const SKIP_EXT = [".html", ".htm", ".php", ".aspx", ".jsp"];

async function cfg() {
  const d = await chrome.storage.local.get({ intercept: true, minSizeMB: 1 });
  return d;
}

async function cookieHeader(url) {
  try {
    const cs = await chrome.cookies.getAll({ url });
    return cs.map(c => `${c.name}=${c.value}`).join("; ");
  } catch (e) { return ""; }
}

async function sendToYDM(payload) {
  return new Promise(resolve => {
    chrome.runtime.sendNativeMessage(HOST, payload, resp => {
      if (chrome.runtime.lastError || !resp || !resp.ok) {
        chrome.notifications.create({
          type: "basic", iconUrl: "icons/icon48.png",
          title: "YDM tidak terhubung",
          message: "Buka aplikasi YDM dan jalankan install_native_host.py terlebih dahulu."
        });
        resolve(false);
      } else resolve(true);
    });
  });
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({ id: "ydm-link", title: "Unduh dengan YDM", contexts: ["link"] });
  chrome.contextMenus.create({ id: "ydm-all", title: "Unduh semua link di halaman", contexts: ["page"] });
  chrome.contextMenus.create({ id: "ydm-page", title: "Unduh halaman ini dengan YDM", contexts: ["page"] });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "ydm-link" && info.linkUrl) {
    const ck = await cookieHeader(info.linkUrl);
    await sendToYDM({ url: info.linkUrl, headers: ck ? { Cookie: ck, Referer: info.pageUrl || "" } : { Referer: info.pageUrl || "" } });
  } else if (info.menuItemId === "ydm-page") {
    await sendToYDM({ url: tab.url });
  } else if (info.menuItemId === "ydm-all" && tab && tab.id) {
    const [r] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => Array.from(document.querySelectorAll("a[href]"))
        .map(a => a.href)
        .filter(h => /\.(zip|rar|7z|iso|mp4|mkv|mp3|pdf|exe|msi|tar|gz)(\?|$)/i.test(h))
    });
    const links = (r && r.result) || [];
    for (const u of links.slice(0, 100)) await sendToYDM({ url: u, headers: { Referer: tab.url } });
    if (links.length) chrome.notifications.create({ type: "basic", iconUrl: "icons/icon48.png", title: "YDM", message: `${Math.min(links.length,100)} link dikirim ke YDM.` });
  }
});

// Tangkap unduhan yang dimulai browser
chrome.downloads.onCreated.addListener(async item => {
  const c = await cfg();
  if (!c.intercept) return;
  const url = item.url || "";
  if (!/^https?:|^ftp:/.test(url)) return;
  if (SKIP_EXT.some(x => url.toLowerCase().split("?")[0].endsWith(x))) return;
  const size = item.fileSize || 0;
  if (size > 0 && size < c.minSizeMB * 1024 * 1024) return;
  try { await chrome.downloads.cancel(item.id); } catch (e) {}
  try { await chrome.downloads.erase({ id: item.id }); } catch (e) {}
  const ck = await cookieHeader(url);
  const headers = {};
  if (ck) headers.Cookie = ck;
  if (item.referrer) headers.Referer = item.referrer;
  const name = (item.filename || "").split(/[\\/]/).pop() || null;
  await sendToYDM({ url, filename: name, headers });
});

// Klik ikon magnet di halaman ditangani lewat context menu link (protokol magnet
// juga muncul sebagai linkUrl). Tambahan: pesan dari popup.
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === "ydm-add" && msg.url) {
    sendToYDM({ url: msg.url }).then(ok => sendResponse({ ok }));
    return true;
  }
  if (msg && msg.type === "ydm-youtube" && msg.url) {
    sendToYDM({ url: msg.url, kind: "youtube", quality: msg.quality || "720" })
      .then(ok => sendResponse({ ok }));
    return true;
  }
});
