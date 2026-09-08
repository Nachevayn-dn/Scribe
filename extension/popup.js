const emptyState = document.getElementById("empty-state");
const previewWrap = document.getElementById("preview-wrap");
const preview = document.getElementById("preview");
const pasteBtn = document.getElementById("paste-btn");
const statusEl = document.getElementById("status");

async function load() {
  const { lastNote } = await chrome.storage.local.get("lastNote");
  if (lastNote) {
    emptyState.style.display = "none";
    previewWrap.style.display = "block";
    preview.textContent = lastNote;
  }
}

pasteBtn.addEventListener("click", async () => {
  statusEl.textContent = "";
  statusEl.className = "status";
  pasteBtn.disabled = true;
  try {
    const response = await chrome.runtime.sendMessage({ type: "PASTE_INTO_ACTIVE_TAB" });
    if (response?.ok) {
      statusEl.textContent = "Pasted!";
      statusEl.className = "status ok";
    } else {
      statusEl.textContent = response?.error || "Couldn't paste — try clicking into a field first.";
      statusEl.className = "status error";
    }
  } catch (err) {
    statusEl.textContent = String(err?.message || err);
    statusEl.className = "status error";
  } finally {
    pasteBtn.disabled = false;
  }
});

load();
