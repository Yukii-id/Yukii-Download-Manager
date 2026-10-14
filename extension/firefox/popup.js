const urlEl = document.getElementById("url");
const st = document.getElementById("st");
const cb = document.getElementById("intercept");
chrome.storage.local.get({ intercept: true }).then(d => { cb.checked = !!d.intercept; });
cb.addEventListener("change", () => chrome.storage.local.set({ intercept: cb.checked }));
document.getElementById("add").addEventListener("click", () => {
  const url = urlEl.value.trim();
  if (!url) { st.textContent = "Isi URL dulu."; return; }
  chrome.runtime.sendMessage({ type: "ydm-add", url }, resp => {
    st.textContent = resp && resp.ok ? "Terkirim ke YDM." : "Gagal: YDM / native host belum terpasang.";
  });
});
