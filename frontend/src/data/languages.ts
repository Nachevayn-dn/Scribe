/** English plus the 24 official EU languages, for the encounter-language
 * picker. ISO-639-1 codes are sent to the backend and passed through to
 * Whisper as a transcription hint (see api/encounters.ts, backend
 * services/transcription/whisper_provider.py). English is listed first
 * since it's the most common choice; the rest are alphabetical by label. */
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
  { code: "sk", label: "Slovak" },
  { code: "sl", label: "Slovenian" },
  { code: "es", label: "Spanish" },
  { code: "sv", label: "Swedish" },
];
