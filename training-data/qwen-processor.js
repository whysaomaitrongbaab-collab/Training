/**
 * Qwen Processor for Training Data
 * 1. Takes processed PDF images from processing/ folder
 * 2. Calls Qwen API with structural-focused prompt
 * 3. Saves JSON output to qwen-output/
 * 4. Updates manifest with Qwen extraction metadata
 *
 * Usage:
 *   node qwen-processor.js                    # process all pending
 *   node qwen-processor.js <record-id>        # process specific record
 */

const fs = require('fs');
const path = require('path');

const TRAINING_DATA_DIR = __dirname;
const PROCESSING_DIR = path.join(TRAINING_DATA_DIR, 'processing');
const QWEN_OUTPUT_DIR = path.join(TRAINING_DATA_DIR, 'qwen-output');
const MANIFEST_FILE = path.join(TRAINING_DATA_DIR, 'manifest.json');

// Ensure qwen-output directory exists
if (!fs.existsSync(QWEN_OUTPUT_DIR)) {
  fs.mkdirSync(QWEN_OUTPUT_DIR, { recursive: true });
}

// Structural-focused prompt for Qwen
const STRUCTURAL_PROMPT = `Analyze this Thai residential structural plan (1-2 floor house).
Extract ONLY structural elements from this drawing:

For each element found, provide:
- Element ID (e.g., C1, B1, S1, F1)
- Element type: column | beam | slab | foundation | wall | stair
- Location/Grid reference (e.g., A-1, B-C/2-3)
- Dimensions (width/depth/height/thickness in mm)
- Concrete grade (fc28 value in ksc, e.g., 240, 280, 300)
- Main rebar: grade (SD30/SD40/SR24), diameter (mm), quantity
- Stirrups/secondary rebar: diameter (mm), spacing (mm)
- Any visible notes or specifications
- Confidence score (0.0-1.0) for this extraction

Return JSON only. Format:
{
  "elements": [
    {
      "id": "C1",
      "type": "column",
      "location": "A-1",
      "dimensions": { "width_mm": 400, "depth_mm": 400, "height_mm": 3500 },
      "concrete_grade_ksc": 240,
      "rebar_main": { "grade": "SD30", "diameter_mm": 16, "quantity": 4 },
      "rebar_stirrups": { "diameter_mm": 6, "spacing_mm": 200 },
      "notes": "",
      "confidence": 0.95
    }
  ],
  "page_summary": "description of what this page shows",
  "notes": "any issues, ambiguities, or questions"
}

Ignore: architectural details, finishes, MEP, labels not related to structure.
Be precise with numbers. If unsure, note it in "notes" field.`;

/**
 * Read images from a processing record and convert to base64
 */
function readProcessingImages(recordDir) {
  const metadataFile = path.join(recordDir, 'metadata.json');

  if (!fs.existsSync(metadataFile)) {
    console.error(`❌ Metadata not found: ${metadataFile}`);
    return null;
  }

  const metadata = JSON.parse(fs.readFileSync(metadataFile, 'utf-8'));
  const images = [];

  if (metadata.processing_steps && metadata.processing_steps[0]) {
    const rasterizeStep = metadata.processing_steps.find(s => s.step === 'rasterize');
    if (rasterizeStep && rasterizeStep.images) {
      for (const imagePath of rasterizeStep.images) {
        try {
          const imageBuffer = fs.readFileSync(imagePath);
          images.push({
            path: imagePath,
            filename: path.basename(imagePath),
            base64: imageBuffer.toString('base64')
          });
        } catch (e) {
          console.error(`⚠️  Could not read image: ${imagePath}`, e.message);
        }
      }
    }
  }

  return { metadata, images };
}

/**
 * Build Qwen API request payload (OpenAI-compatible format)
 * Note: This assumes you'll call via supabase.functions.invoke('qwen-vision', ...)
 * from the browser, or via your Supabase Edge Function
 */
function buildQwenPayload(images, prompt) {
  const content = [{ type: 'text', text: prompt }];

  for (const img of images) {
    content.push({
      type: 'image_url',
      image_url: {
        url: `data:image/png;base64,${img.base64}`
      }
    });
  }

  return {
    model: 'qwen-vl-max',
    messages: [
      {
        role: 'user',
        content
      }
    ],
    response_format: {
      type: 'json_object'
    }
  };
}

/**
 * Call Qwen API (requires Supabase Edge Function set up)
 * This is a placeholder — you'll need to adapt this to your actual Qwen caller
 */
async function callQwenAPI(payload) {
  // Placeholder: In production, this would:
  // 1. Call via supabase.functions.invoke('qwen-vision', { body: payload })
  // 2. Or call the Vercel fallback at js/ai/qwenVision.js

  // For now, return a stub so you can test the pipeline
  console.log('⚠️  Note: Qwen API call is a placeholder.');
  console.log('   To integrate: link to your existing qwenVision.js or Supabase Edge Function');

  return {
    status: 'placeholder',
    message: 'Integrate with actual Qwen API caller',
    payload_preview: JSON.stringify(payload, null, 2).substring(0, 500) + '...'
  };
}

/**
 * Process a single record through Qwen
 */
async function processRecord(recordId) {
  const recordDir = path.join(PROCESSING_DIR, recordId);

  if (!fs.existsSync(recordDir)) {
    console.error(`❌ Record not found: ${recordId}`);
    return null;
  }

  console.log(`\n🔄 Processing with Qwen: ${recordId}`);

  // 1. Read images
  const data = readProcessingImages(recordDir);
  if (!data || data.images.length === 0) {
    console.error('❌ No images found');
    return null;
  }

  console.log(`   📸 Loaded ${data.images.length} images`);

  // 2. Build Qwen payload
  const payload = buildQwenPayload(data.images, STRUCTURAL_PROMPT);
  console.log(`   📤 Payload ready (${Math.round(JSON.stringify(payload).length / 1024)} KB)`);

  // 3. Call Qwen
  console.log(`   🧠 Calling Qwen...`);
  let qwenResult;
  try {
    qwenResult = await callQwenAPI(payload);
  } catch (error) {
    console.error(`   ❌ Qwen API error:`, error.message);
    return null;
  }

  // 4. Save Qwen output
  const outputFile = path.join(QWEN_OUTPUT_DIR, `${recordId}-qwen.json`);
  fs.writeFileSync(outputFile, JSON.stringify(qwenResult, null, 2), 'utf-8');
  console.log(`   💾 Qwen output saved: ${outputFile}`);

  // 5. Update manifest
  const manifest = JSON.parse(fs.readFileSync(MANIFEST_FILE, 'utf-8'));
  const recordEntry = manifest.datasets.find(d => d.id === recordId);
  if (recordEntry) {
    recordEntry.qwen_output = outputFile;
    recordEntry.qwen_extraction_date = new Date().toISOString();
    recordEntry.status = 'qwen_complete';
  }
  manifest.stats.qwen_extractions = (manifest.stats.qwen_extractions || 0) + 1;
  fs.writeFileSync(MANIFEST_FILE, JSON.stringify(manifest, null, 2), 'utf-8');

  return { recordId, outputFile, qwenResult };
}

/**
 * List pending records (processed PDFs waiting for Qwen analysis)
 */
function listPendingRecords() {
  const manifest = JSON.parse(fs.readFileSync(MANIFEST_FILE, 'utf-8'));
  const pending = manifest.datasets.filter(d => !d.qwen_output);

  if (pending.length === 0) {
    console.log('✅ No pending records');
    return [];
  }

  console.log(`📋 Pending records (${pending.length}):`);
  for (const record of pending) {
    console.log(`   ${record.id} — ${record.source_file}`);
  }

  return pending;
}

/**
 * Main entry point
 */
async function main() {
  if (process.argv[2] === 'list') {
    listPendingRecords();
  } else if (process.argv[2]) {
    // Process specific record
    await processRecord(process.argv[2]);
  } else {
    // Process all pending
    const pending = listPendingRecords();
    for (const record of pending) {
      await processRecord(record.id);
    }
  }
}

main().catch(console.error);
