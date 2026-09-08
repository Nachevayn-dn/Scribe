/**
 * Runs on MedicDesk.ai pages only (see manifest.json's content_scripts
 * "matches"). Listens for the postMessage the app sends when a doctor
 * clicks "Copy for PMS" on a note (see frontend/src/pages/
 * NoteEditorPage.tsx's handleCopyForPms), and relays the note text to the
 * background service worker so the popup's "Paste into focused field"
 * action has something to paste — even on a page where the browser denied
 * navigator.clipboard access.
 */
window.addEventListener("message", (event) => {
  if (event.source !== window) return; // only trust messages from this same page, not an iframe/extension
  const data = event.data;
  if (!data || data.source !== "medicdesk" || data.type !== "NOTE_COPIED") return;
  if (typeof data.text !== "string" || !data.text) return;

  chrome.runtime.sendMessage({ type: "STORE_NOTE", text: data.text });
});
