/** English plus the 24 official EU languages, and a couple of extras
 * (Russian, Turkish) added for expat-heavy clinics outside the EU list.
 * Used for the encounter-language picker, the doctor's own default
 * language, and the inbound/outbound agents' language settings.
 * ISO-639-1 codes are sent to the backend and passed through to Whisper
 * as a transcription hint (see api/encounters.ts, backend
 * services/transcription/whisper_provider.py) and to Twilio for the
 * inbound agent's speech recognition/voice (see backend api/
 * telephony.py's _TWILIO_LANGUAGE_MAP). English is listed first since
 * it's the most common choice; the rest are alphabetical by label. */
export interface LanguageOption {
  code: string;
  label: string;
}

export const EU_LANGUAGES: LanguageOption[] = [
  { code: "en", label: "English" },
  { code: "bg", label: "Bulgarian" },
  { code: "hr", label: "Croatian" },
  { code: "cs", label: "Czech" },
  { code: "da", label: "Danish" },
  { code: "nl", label: "Dutch" },
  { code: "et", label: "Estonian" },
  { code: "fi", label: "Finnish" },
  { code: "fr", label: "French" },
  { code: "de", label: "German" },
  { code: "el", label: "Greek" },
  { code: "hu", label: "Hungarian" },
  { code: "ga", label: "Irish" },
  { code: "it", label: "Italian" },
  { code: "lv", label: "Latvian" },
  { code: "lt", label: "Lithuanian" },
  { code: "mt", label: "Maltese" },
  { code: "pl", label: "Polish" },
  { code: "pt", label: "Portuguese" },
  { code: "ro", label: "Romanian" },
  { code: "ru", label: "Russian" },
  { code: "sk", label: "Slovak" },
  { code: "sl", label: "Slovenian" },
  { code: "es", label: "Spanish" },
  { code: "sv", label: "Swedish" },
  { code: "tr", label: "Turkish" },
];
