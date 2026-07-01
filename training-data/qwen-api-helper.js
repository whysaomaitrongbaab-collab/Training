/**
 * Qwen API Helper — Integration with Constistant's existing Qwen pipeline
 *
 * This helper connects qwen-processor.js to the actual Qwen API via:
 * 1. Supabase Edge Function (preferred): supabase.functions.invoke('qwen-vision', ...)
 * 2. Fallback: Direct Qwen API call via js/ai/qwenVision.js
 *
 * Usage in qwen-processor.js:
 *   const { callQwenAPINative } = require('./qwen-api-helper');
 *   const result = await callQwenAPINative(payload);
 */

const https = require('https');
const path = require('path');
const fs = require('fs');

/**
 * Call Qwen via Supabase Edge Function
 * Requires: supabase.js config at project root with URL + anon key
 */
async function callQwenViaSupabase(payload) {
  // Read Supabase config from project root
  const supabaseConfigPath = path.join(__dirname, '..', 'supabase.js');

  if (!fs.existsSync(supabaseConfigPath)) {
    throw new Error(
      `Supabase config not found: ${supabaseConfigPath}\n` +
      'Copy config/supabase.example.js to supabase.js and fill in your project URL + key'
    );
  }

  // Extract URL from supabase.js (basic parsing)
  const configContent = fs.readFileSync(supabaseConfigPath, 'utf-8');
  const urlMatch = configContent.match(/supabaseUrl\s*[=:]\s*['"](.+?)['"]/);
  const anonKeyMatch = configContent.match(/supabaseAnonKey\s*[=:]\s*['"](.+?)['"]/);

  if (!urlMatch || !anonKeyMatch) {
    throw new Error(
      'Could not extract supabaseUrl/supabaseAnonKey from supabase.js\n' +
      'Ensure config format: export const supabaseUrl = "..."; export const supabaseAnonKey = "...";'
    );
  }

  const supabaseUrl = urlMatch[1];
  const supabaseAnonKey = anonKeyMatch[1];

  // Call Supabase Edge Function
  console.log('   Calling Supabase Edge Function: qwen-vision');

  return new Promise((resolve, reject) => {
    const url = new URL(`${supabaseUrl}/functions/v1/qwen-vision`);
    const options = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${supabaseAnonKey}`
      }
    };

    const req = https.request(url, options, (res) => {
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
      });

      res.on('end', () => {
        try {
          const result = JSON.parse(data);
          if (res.statusCode >= 400) {
            reject(new Error(`Qwen API error (${res.statusCode}): ${data}`));
          } else {
            resolve(result);
          }
        } catch (e) {
          reject(new Error(`Failed to parse Qwen response: ${data}`));
        }
      });
    });

    req.on('error', (e) => {
      reject(new Error(`Network error calling Qwen: ${e.message}`));
    });

    req.write(JSON.stringify(payload));
    req.end();
  });
}

/**
 * Call Qwen directly via OpenAI-compatible API (fallback)
 * Requires: QWEN_API_KEY + QWEN_API_HOST environment variables
 */
async function callQwenDirect(payload) {
  const apiKey = process.env.QWEN_API_KEY;
  const apiHost = process.env.QWEN_API_HOST || 'https://dashscope.aliyuncs.com/api/v1';

  if (!apiKey) {
    throw new Error(
      'QWEN_API_KEY not set.\n' +
      'Set environment: export QWEN_API_KEY="your_key" (Windows: set QWEN_API_KEY=your_key)'
    );
  }

  console.log('   Calling Qwen Direct API');

  return new Promise((resolve, reject) => {
    const url = new URL(`${apiHost}/chat/completions`);
    const options = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      }
    };

    const req = https.request(url, options, (res) => {
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
      });

      res.on('end', () => {
        try {
          const result = JSON.parse(data);
          if (res.statusCode >= 400) {
            reject(new Error(`Qwen API error (${res.statusCode}): ${data}`));
          } else {
            resolve(result);
          }
        } catch (e) {
          reject(new Error(`Failed to parse Qwen response: ${data}`));
        }
      });
    });

    req.on('error', (e) => {
      reject(new Error(`Network error calling Qwen: ${e.message}`));
    });

    req.write(JSON.stringify(payload));
    req.end();
  });
}

/**
 * Main entry point: tries Supabase first, falls back to direct API
 */
async function callQwenAPINative(payload) {
  // Try Supabase Edge Function first (preferred)
  try {
    return await callQwenViaSupabase(payload);
  } catch (supabaseError) {
    console.warn(`   ⚠️  Supabase Edge Function not available: ${supabaseError.message}`);
    console.log('   Falling back to direct Qwen API...');

    try {
      return await callQwenDirect(payload);
    } catch (directError) {
      throw new Error(
        `Both Qwen API calls failed:\n` +
        `1. Supabase: ${supabaseError.message}\n` +
        `2. Direct: ${directError.message}`
      );
    }
  }
}

/**
 * Format Qwen's response to match training dataset structure
 */
function formatQwenResponse(qwenResponse, recordId, sourceFile) {
  // Handle different response formats
  let extractedContent = qwenResponse;

  // If Supabase Edge Function wraps response
  if (qwenResponse.body) {
    extractedContent = JSON.parse(qwenResponse.body);
  }

  // If API returns in message format
  if (qwenResponse.choices && qwenResponse.choices[0]) {
    const message = qwenResponse.choices[0].message;
    if (typeof message.content === 'string') {
      try {
        extractedContent = JSON.parse(message.content);
      } catch {
        extractedContent = { raw_content: message.content };
      }
    } else {
      extractedContent = message.content;
    }
  }

  return {
    record_id: recordId,
    source_file: sourceFile,
    extraction_date: new Date().toISOString(),
    qwen_model: 'qwen-vl-max',
    qwen_extraction: extractedContent,
    raw_response: qwenResponse
  };
}

module.exports = {
  callQwenAPINative,
  callQwenViaSupabase,
  callQwenDirect,
  formatQwenResponse
};
