# MedicDesk.ai → PMS (Chrome extension)

A small Chrome extension that lets a doctor copy a MedicDesk.ai clinical
note and paste it into whatever field they have focused in their Practice
Management System (PMS) — works with **any** PMS, since it doesn't
integrate with a specific vendor's API. It just moves text from one tab
to another, the way you'd copy-paste by hand, minus the hunting for the
right window.

## How it works

1. In MedicDesk.ai, open a signed (or draft) clinical note and click
   **"Copy for PMS"**. This copies the note text to your clipboard as
   normal, *and* remembers it inside the extension.
2. Switch to your PMS's tab, click into the field you want the note in.
3. Click the MedicDesk.ai extension icon in your Chrome toolbar, then
   click **"Paste into focused field"**.

If your browser lets ordinary copy/paste work between the two tabs, you
never need step 3 at all — just paste normally (Cmd/Ctrl+V). The extension
exists for the cases where that's inconvenient, or where a plain paste
doesn't trigger a web-based PMS's own "something changed" listeners
(the extension dispatches proper `input`/`change` events, which most
PMS web apps expect).

## Installing it (not yet on the Chrome Web Store)

This hasn't been published to the Chrome Web Store yet, so it installs
as an "unpacked" extension — completely normal for testing, just a few
more clicks than a Web Store install:

1. Open Chrome and go to `chrome://extensions`
2. Turn on **"Developer mode"** (top-right toggle)
3. Click **"Load unpacked"**
4. Select this `extension` folder (the one this README is in)
5. The MedicDesk.ai icon should appear in your toolbar — click the puzzle-piece
   icon next to the address bar and pin it if you don't see it right away

## If MedicDesk.ai is running somewhere other than localhost:5173

The extension only activates on the pages listed in `manifest.json`'s
`content_scripts`/`host_permissions` — right now that's
`http://localhost:5173` (the usual local dev address) plus
`medicdesk.ai` and any of its subdomains, for once it's deployed. If
you're running it somewhere else (a different port, an ngrok URL, a
staging domain), add that address to both lists in `manifest.json` and
reload the extension (`chrome://extensions` → the refresh icon on this
extension's card).

## Permissions this extension asks for, and why

- **storage** — remembers the last note you copied, so the popup has
  something to show/paste.
- **activeTab** — lets it read/write into whatever tab is active *only*
  when you click the extension icon — it can't touch other tabs, and
  doesn't request access to every website you visit.
- **scripting** — the mechanism used to actually place the text into
  the focused field on your PMS's page.

It never sends anything to MedicDesk.ai's own servers or anywhere else —
the copied text stays on your machine, in the browser's local extension
storage, until you copy a different note.
