/** A curated set of IANA timezones for the dashboard clock widget — not
 * exhaustive, just common EU zones (matching the EU language picker) plus a
 * few major world zones. */
export interface TimezoneOption {
  value: string;
  label: string;
}

const _localTz = Intl.DateTimeFormat().resolvedOptions().timeZone;

const _namedZones: TimezoneOption[] = [
  { value: "UTC", label: "UTC" },
  { value: "Europe/London", label: "London" },
  { value: "Europe/Dublin", label: "Dublin" },
  { value: "Europe/Lisbon", label: "Lisbon" },
  { value: "Europe/Madrid", label: "Madrid" },
  { value: "Europe/Paris", label: "Paris" },
  { value: "Europe/Brussels", label: "Brussels" },
  { value: "Europe/Amsterdam", label: "Amsterdam" },
  { value: "Europe/Berlin", label: "Berlin" },
  { value: "Europe/Rome", label: "Rome" },
  { value: "Europe/Vienna", label: "Vienna" },
  { value: "Europe/Prague", label: "Prague" },
  { value: "Europe/Warsaw", label: "Warsaw" },
  { value: "Europe/Budapest", label: "Budapest" },
  { value: "Europe/Bucharest", label: "Bucharest" },
  { value: "Europe/Sofia", label: "Sofia" },
  { value: "Europe/Athens", label: "Athens" },
  { value: "Europe/Helsinki", label: "Helsinki" },
  { value: "Europe/Stockholm", label: "Stockholm" },
  { value: "Europe/Copenhagen", label: "Copenhagen" },
  { value: "Europe/Riga", label: "Riga" },
  { value: "Europe/Vilnius", label: "Vilnius" },
  { value: "Europe/Tallinn", label: "Tallinn" },
  { value: "America/New_York", label: "New York" },
  { value: "America/Chicago", label: "Chicago" },
  { value: "America/Los_Angeles", label: "Los Angeles" },
  { value: "Asia/Dubai", label: "Dubai" },
  { value: "Asia/Kolkata", label: "Mumbai / Delhi" },
  { value: "Asia/Singapore", label: "Singapore" },
  { value: "Asia/Tokyo", label: "Tokyo" },
  { value: "Australia/Sydney", label: "Sydney" },
];

export const TIMEZONES: TimezoneOption[] = [
  { value: _localTz, label: "Local time (this device)" },
  ..._namedZones.filter((z) => z.value !== _localTz),
];
