/**
 * Service worker (Manifest V3 — event-driven, no persistent memory across
 * restarts, so the last-copied note is kept in chrome.storage.local, not
 * a plain JS variable).
 */
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "STORE_NOTE") {
    chrome.storage.local.set({ lastNote: message.text, lastNoteAt: Date.now() });
    return; // no response needed
  }

  if (message?.type === "PASTE_INTO_ACTIVE_TAB") {
    pasteIntoActiveTab().then(sendResponse);
    return true; // keep the message channel open for the async response
  }
});

async function pasteIntoActiveTab() {
  const { lastNote } = await chrome.storage.local.get("lastNote");
  if (!lastNote) {
    return { ok: false, error: "No note copied yet — click \"Copy for PMS\" on a note in MedicDesk.ai first." };
  }

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    return { ok: false, error: "No active tab found." };
  }

  try {
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: pasteIntoFocusedElement,
      args: [lastNote],
    });
    return result;
  } catch (err) {
    // Most commonly: the active tab is a page Chrome doesn't allow
    // scripting on (chrome://, the Chrome Web Store, a PDF viewer, etc.).
    return { ok: false, error: `Couldn't access this page: ${err.message || err}` };
  }
}

// Runs inside the target page (the PMS tab), not the extension — must be
// a plain, self-contained function (no closures over background.js's
// scope) since chrome.scripting.executeScript serializes it over.
function pasteIntoFocusedElement(text) {
  const el = document.activeElement;
  if (!el) {
    return { ok: false, error: "Click into a field in your PMS first, then try again." };
  }

  const tag = el.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA") {
    const start = el.selectionStart ?? el.value.length;
    const end = el.selectionEnd ?? el.value.length;
    el.value = el.value.slice(0, start) + text + el.value.slice(end);
    el.selectionStart = el.selectionEnd = start + text.length;
    // Most web apps (React/Vue/Angular PMS UIs included) listen for these
    // rather than reading .value directly, so they notice the change.
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return { ok: true };
  }

  if (el.isContentEditable) {
    document.execCommand("insertText", false, text);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    return { ok: true };
  }

  return { ok: false, error: "The focused element isn't a text field." };
}
