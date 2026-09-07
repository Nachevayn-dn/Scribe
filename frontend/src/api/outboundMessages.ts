import { api } from "./client";
import type { OutboundMessageLog } from "../types";

export function listOutboundMessages() {
  return api.get<OutboundMessageLog[]>("/outbound-messages");
}
