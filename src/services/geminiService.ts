import { GoogleGenAI } from "@google/genai";

let ai: GoogleGenAI | null = null;

function getAI(): GoogleGenAI {
  if (!ai) {
    const apiKey = import.meta.env.VITE_GEMINI_API_KEY;
    if (!apiKey) throw new Error('VITE_GEMINI_API_KEY is not set');
    ai = new GoogleGenAI({ apiKey });
  }
  return ai;
}

export async function getChatResponse(message: string, botType: string, history: { role: 'user' | 'model', parts: { text: string }[] }[] = []) {
  try {
    const contents = [
      ...history.map(h => ({
        role: h.role,
        parts: h.parts
      })),
      {
        role: 'user',
        parts: [{ text: message }]
      }
    ];

    const response = await getAI().models.generateContent({
      model: "gemini-2.0-flash",
      contents: contents,
      config: {
        systemInstruction: `You are the ${botType} for Nexus, a business growth platform.
        Your goal is to help users scale their business, find funding, and manage operations.
        Be professional, encouraging, and highly practical.
        If you are the Funding Bot, focus on capital and grants.
        If you are the Advisor, focus on strategy and growth.
        If you are the Setup Bot, focus on business formation and compliance.
        Keep responses concise and actionable.`
      }
    });

    return response.text || "I'm sorry, I couldn't generate a response.";
  } catch (error) {
    console.error("Gemini API Error:", error);
    return "I'm sorry, I'm having trouble connecting to my brain right now. Please try again in a moment.";
  }
}
