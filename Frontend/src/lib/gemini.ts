

export const ENV_BOT_WHATSAPP_URL = "";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  imageUrl?: string;
  timestamp: number;
}

export interface AttachedImageData {
  base64: string;
  mimeType: string;
  previewUrl: string;
}

interface GenerateReplyOptions {
  history: ChatMessage[];
  currentMessage: string;
  image?: AttachedImageData | null;

  whatsappUrl?: string;
}

const OFFLINE =
  "I can't reach the assistant right now. Message SafeZone on WhatsApp and someone will see it.";

export async function generateGeminiReply({
  history,
  currentMessage,
  image,
}: GenerateReplyOptions): Promise<string> {

  const body = {
    message: currentMessage.trim(),
    history: history.map((message) => ({
      role: message.role,
      text: message.text,
    })),
    image: image?.base64
      ? { base64: image.base64, mimeType: image.mimeType || "image/jpeg" }
      : null,
  };

  let response: Response;
  try {
    response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {

    throw new Error(OFFLINE);
  }

  if (!response.ok) {
    let detail = "";
    try {
      detail = (await response.json())?.detail ?? "";
    } catch {
      detail = "";
    }
    throw new Error(detail || OFFLINE);
  }

  const data = await response.json();
  const reply = typeof data?.reply === "string" ? data.reply.trim() : "";
  return (
    reply ||
    "I wasn't able to answer that. Message SafeZone on WhatsApp and someone will see it."
  );
}
