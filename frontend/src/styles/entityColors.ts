import type { EntityType } from "../types";

interface EntityColor {
  label: string;
  bg: string;
  border: string;
  text: string;
}

// Single source of truth for the entity color mapping from the product
// spec: Medications=Red, Procedures=Teal, Diagnostics=Yellow, Symptoms=Green,
// Allergies=Mint. Consumed by both EntityHighlightedLine and EntityLegend.
export const ENTITY_COLORS: Record<EntityType, EntityColor> = {
  MEDICATION: { label: "Medication", bg: "#fdecec", border: "#e5484d", text: "#7a1f22" },
  PROCEDURE: { label: "Procedure", bg: "#e6f7f6", border: "#12a594", text: "#0b5f56" },
  DIAGNOSTIC: { label: "Diagnostic", bg: "#fef8e1", border: "#e6b800", text: "#7a5f00" },
  SYMPTOM: { label: "Symptom", bg: "#e9f7ec", border: "#30a46c", text: "#1a5c3a" },
  ALLERGY: { label: "Allergy", bg: "#e6faf3", border: "#4cc9a5", text: "#1f6b53" },
};
