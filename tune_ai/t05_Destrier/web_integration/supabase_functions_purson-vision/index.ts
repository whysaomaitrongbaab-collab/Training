// supabase/functions/purson-vision/index.ts
//
// Purson (our own fine-tuned drawing-extraction model) dispatcher.
// Two actions:
//   "single" — forward ONE model call to the OpenAI-compatible GPU endpoint named by
//              the PURSON_ENDPOINT_URL secret (mode A: a rented server with a stable
//              URL). Returns 503 when no direct endpoint is configured — callers then
//              fall back to the job queue (mode B), which the browser reaches by
//              inserting into purson_jobs directly via supabase-js + RLS.
//   "submit" — enqueue a house_extract job on behalf of the caller (equivalent to a
//              direct table insert; kept so both modes share one invoke() surface).
//
// Secrets: PURSON_ENDPOINT_URL (e.g. https://gpu.example.com), PURSON_API_KEY
// (optional bearer for that endpoint), PURSON_MODEL (served model / LoRA module
// name, default "purson").
import { serve } from "https://deno.land/std@0.208.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const endpointUrl = Deno.env.get("PURSON_ENDPOINT_URL");
const endpointKey = Deno.env.get("PURSON_API_KEY");
const modelName = Deno.env.get("PURSON_MODEL") || "purson";

// Lesson from tpso-sync (2026-07-27): supabase-js attaches apikey/x-client-info to
// every functions.invoke(); omitting them from Allow-Headers makes the browser
// silently drop the POST after a 200 preflight.
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, apikey, x-client-info",
};
const MAX_IMAGE_BASE64_CHARS = 7_000_000;
const MAX_TOTAL_BASE64_CHARS = 20_000_000;

function json(body: Record<string, unknown>, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

  try {
    const body = await req.json();
    const action = body.action || "single";

    if (action === "submit") {
      const { project_id, drawing_upload_id, pages, options } = body;
      if (!Array.isArray(pages) || pages.length === 0) {
        return json({ error: "Missing pages" }, 400);
      }
      // Insert as the calling user so RLS ownership holds.
      const supa = createClient(
        Deno.env.get("SUPABASE_URL")!,
        Deno.env.get("SUPABASE_ANON_KEY")!,
        { global: { headers: { Authorization: req.headers.get("Authorization")! } } },
      );
      const { data, error } = await supa
        .from("purson_jobs")
        .insert({
          project_id: project_id ?? null,
          drawing_upload_id: drawing_upload_id ?? null,
          job_type: "house_extract",
          payload: { pages, options: options ?? {} },
        })
        .select("id")
        .single();
      if (error) return json({ error: error.message }, 400);
      return json({ mode: "queued", job_id: data.id });
    }

    // action === "single": one model call, direct mode only.
    if (!endpointUrl) {
      return json({ error: "No direct Purson endpoint configured — use the job queue" }, 503);
    }
    const { images, prompt } = body;
    if (!prompt) return json({ error: "Missing prompt" }, 400);

    const content: unknown[] = [];
    let totalChars = 0;
    for (const img of images || []) {
      if (!img || typeof img.data !== "string" || !img.data) {
        return json({ error: "Invalid image entry" }, 400);
      }
      if (img.data.length > MAX_IMAGE_BASE64_CHARS) {
        return json({ error: "Image too large (max ~5MB)" }, 413);
      }
      totalChars += img.data.length;
      if (totalChars > MAX_TOTAL_BASE64_CHARS) {
        return json({ error: "Total image payload too large" }, 413);
      }
      const mime = img.mime_type || "image/png";
      content.push({ type: "image_url", image_url: { url: `data:${mime};base64,${img.data}` } });
    }
    content.push({ type: "text", text: prompt });

    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (endpointKey) headers["Authorization"] = `Bearer ${endpointKey}`;

    const response = await fetch(`${endpointUrl}/v1/chat/completions`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        model: modelName,
        messages: [{ role: "user", content }],
        max_tokens: 6000,
        temperature: 0,
        repetition_penalty: 1.15,
        // vLLM builtin JSON grammar (xgrammar backend) — the standing t03/t04 rule:
        // JSON-constrain every subtask (มะขามสั่ง 2026-08-29).
        response_format: { type: "json_object" },
      }),
    });
    if (!response.ok) {
      const error = await response.text();
      console.error("Purson endpoint error:", error);
      return json({ error: "Purson endpoint error" }, 502);
    }
    const data = await response.json();
    const text = data?.choices?.[0]?.message?.content || "";
    let result: unknown;
    try {
      result = JSON.parse(text);
    } catch {
      return json({ mode: "direct", result: null, raw_text: text, valid: false });
    }
    return json({ mode: "direct", result, valid: true });
  } catch (error) {
    console.error("Error:", error);
    return json({ error: (error as Error).message }, 500);
  }
});
