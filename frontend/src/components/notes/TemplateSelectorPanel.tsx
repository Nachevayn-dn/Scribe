import { useEffect, useState } from "react";
import * as templatesApi from "../../api/templates";
import type { NoteTemplate } from "../../types";

interface Props {
  value: string | null;
  onChange: (templateId: string) => void;
  disabled?: boolean;
  label?: string;
}

export function TemplateSelectorPanel({ value, onChange, disabled, label }: Props) {
  const [templates, setTemplates] = useState<NoteTemplate[]>([]);

  useEffect(() => {
    templatesApi.listTemplates().then(setTemplates).catch(() => setTemplates([]));
  }, []);

  return (
    <label className="row" style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
      {label ?? "Template"}
      <select
        className="input"
        style={{ width: 220 }}
        value={value ?? ""}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      >
        {templates.map((t) => (
          <option key={t.id} value={t.id}>
            {t.name}
          </option>
        ))}
      </select>
    </label>
  );
}
