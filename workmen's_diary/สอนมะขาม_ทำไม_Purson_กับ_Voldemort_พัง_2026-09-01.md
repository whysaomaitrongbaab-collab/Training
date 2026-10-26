# Teaching Makham — why Purson and Voldemort didn't work (and what the model-merging equation is)

> Explained as simply as possible, no jargon unless necessary · content from the workmen's diary, Aug 29–31, 2026
> Written 2026-09-01

---

## Part 0 — Groundwork first: how we train a model

Try to imagine that the AI model is an **intern**.

We wanted him to **read construction drawings and type them up as a table**, so we:

1. Took real drawings from 40 houses
2. Had **a person read them and write the answer key first** (these are the files in `json_แก้ไขแล้ว/`)
3. Crammed "drawing image + answer key" in front of the intern over and over until he memorized how he's supposed to answer

That repeated cramming is exactly what's called **"training"**.

Then we named each training run t01, t02, t03, **t04 (nickname Purson)**,
**t44 (nickname Voldemort)**, t05 (nickname Courser → now renamed **Destrier**).

---

## Part 1 — Purson (t04) failed because of "the wrong pair of glasses"

### What happened

Training finished, several thousand THB spent, we tested it, and the result came out:

```
plan_beam    read correctly 0%
plan_footing read correctly 0%
```

**Zero percent**, even though it looked as if everything was correct.

### At first the model looked smart

Every time, it answered with beautiful JSON, **96–100%** correctly formatted.

But once we actually opened the answer files and looked (not just at the score numbers), we found that —

> **Feed it a foundation plan, and it answers with the roof plan of a different house**

It wasn't a case of answering slightly wrong; it **had no idea at all what it was looking at**.

### The real cause: one missing line

The config file had one line that **had to be written but wasn't**:

```yaml
crop_to_patches: true      # ← this line was missing
```

This line means *"when an image is fed in, slice it into small pieces and look at them one piece at a time"*.

**Leaving this line out = the model shrinks the whole sheet down to 448×448 pixels and looks at it just once, and that's it**

### A comparison to help you picture it

| | What it's like |
|---|---|
| **What should have happened** | Lay the A1 drawing on a table, then walk around and look at one corner at a time with a magnifying glass |
| **What actually happened** | Shrink the entire A1 drawing down to **a postage-stamp-sized picture** and then ask it to read the beam names |

A postage-stamp-sized picture like that is definitely unreadable, no matter how good your eyes are.

### 3 layers of proof, not a guess

1. **Counted the real numbers in the training log** — 768 tokens per 3 images = **exactly 256 tokens per image**
   (256 tokens ≈ a very, very small image · a real construction drawing needs thousands)
2. **Read through the library's code** (`mm_plugin.py`) → found that image slicing really does have to be switched on by that line
3. **Tried it with our own eyes** — shrank a real beam plan down to 448×448 and opened it to look →
   **couldn't read a single beam name, size, or rebar**

### So what did it learn instead

It learned **"what the answer looks like"**, not **"how to read the drawings"**.

It memorized that *"when you see a drawing image like this, you have to answer in JSON with the fields element_id, count, grid_refs"*
and **memorized the answers for the houses it had seen during training** — but as soon as it met a new house it had never seen, it immediately started making things up.

Like a kid who has memorized every old exam but doesn't understand the material at all.

### ⚠️ The most expensive lesson: this is the same kind of bug, for the **3rd time**

| Run | Same symptom |
|---|---|
| t01 | Unsloth secretly shrank the images to 512px without telling anyone |
| t02 | The data-prep tool shrank the images, and nobody checked how much they'd been shrunk |
| t04 | Didn't know the `crop_to_patches` switch existed |

**Every time it was "the images got shrunk without anyone knowing"**, and every time **no error showed up at all** — dead silent.

So we set a new rule (`rule_of_tune.md` rule 15):

> **Before every real training run, first measure "1 image = how many tokens"**
> It can be measured on a CPU, no need to start a GPU, and it doesn't cost even 1 THB.

---

## Part 2 — Voldemort (t44) failed, for a completely different reason

After learning that Purson died because the images were too small, we started a new arm called **Voldemort**,
using a different model (InternVL3-78B, a much bigger one) **and with the image-slicing problem already fixed**.

Image slicing really did work correctly — 13 pieces per page, 3,482 tokens ✅

**But it died of a second disease**

### The second disease: compressing the model until it went blind

The big model eats a huge amount of memory, so we **"compressed" it (4-bit quantization)**
to make it smaller so it would fit on the GPU.

The problem is — the model has 2 parts:

| Part | Job |
|---|---|
| **Eyes** (InternViT-6B) | Look at the image |
| **Brain** | Think + answer |

Our compression **squeezed both parts at the same time, eyes included**.

And InternVL's official documentation **warns directly, word for word**, not to compress the eyes:

> *"produce nonsensical outputs and fail to understand images"*
> (it gives nonsense answers and doesn't understand the images)

### The most darkly comic evidence in the whole project

We asked it what it saw in the image:

| What we fed in | What it said it saw |
|---|---|
| Foundation plan of a Thai house | *"a round document, pink background, Facebook/Apple/Barbie logos, the text **Happy Birthday**"* |
| Beam plan of a Thai house | *"a logo of **BB-8 from Star Wars**, surrounded by Facebook/Twitter/Instagram/Snapchat"* |
| "ตัวหนังสือใหญ่สุดบนหน้าคืออะไร" ("What is the largest text on the page?") | *"Happy Birthday"* / *"Facebook"* |

**This isn't "can't read the small text" — this is total blindness, then hallucinating something completely unrelated**

### 💰 The most worthwhile $2 gate

Before full training, we set up a **"check-before-you-pay gate"** (go/no-go gate) costing about **$2**,
which just means starting up the model and having it look at 3 real drawing pages.

- If it can read them → go ahead with full training
- If it can't read them → stop

**Result: failed 0/3 → stopped immediately, saving $60–70**

### ⚠️ The trap that nearly fooled us

**The gate's first round came up green!** But it was green for the wrong reason.

In the prompt Claude wrote for the test, it went and put in the example *"เช่น F1, B2, C1, ผ2"* (e.g. F1, B2, C1, ผ2)
and **F1 and ผ2 just happened to be real answers in the answer key**.

So the model **copied the example from the question back as its answer** — and the script counted it as a "match!" ✅

On another page it answered B1, B2, B3 … all the way to B34 (just counting upward), and by coincidence the first 3 matched the answer key.

> **Trusting the first round's result = burning money all night on a model that can't see anything at all, an exact repeat of t04**

**New rule: never put examples that are in the answer key into a prompt used for testing**

---

## Part 3 — Side-by-side summary of the two

|  | **Purson (t04)** | **Voldemort (t44)** |
|---|---|---|
| What it was sick with | Images shrunk until they were too small | Compressed until its eyes broke |
| Image slicing | ❌ Not turned on | ✅ Turned on correctly |
| Symptom | Pretty answers, but they were another house's answers | Saw Barbie and BB-8 in the construction drawings |
| When it was caught | **After** training finished (money already spent) | **Before** training, at the $2 gate |
| How much was lost | Several thousand THB | ~$2 |

**Takeaway:** the second one hurt far less, not because we got better
but because we **set up a cheap check gate before spending big** — a lesson taken straight from the first one

---

## Part 4 — The model-merging equation (what Claude used to merge things)

### The problem first: why merge at all

We have 40 houses. If we train on all 40 → **there are no houses left to test on at all**
It's like having a kid memorize every exam question and then testing them with that same exam — they score 100%, but you don't know whether they're really any good

### The fix: k-fold (split into piles that take turns being the exam)

Split the 40 houses into **5 piles of 8 houses each**

| Round | Used for training | Held out for testing |
|---|---|---|
| fold 0 | Piles 2,3,4,5 (32 houses) | **Pile 1** (8 houses) |
| fold 1 | Piles 1,3,4,5 | **Pile 2** |
| fold 2 | Piles 1,2,4,5 | **Pile 3** |
| fold 3 | Piles 1,2,3,5 | **Pile 4** |

In the end you get **4 models**, each of which has seen 32 houses (a different set each)
and test scores you can **trust**, because each was tested on houses it had never seen

### So how do the 4 get merged into one — **the equation**

```
merged model  =  (1/k) × model₁  +  (1/k) × model₂  +  ...  +  (1/k) × model_k
```

`k` = number of models · ours is **k = 4** → each gets a weight of **0.25**

```
merged model = 0.25×A + 0.25×B + 0.25×C + 0.25×D
```

The English name for this method is **"model soup"** (a soup of models — everything poured into one pot)

### Why the weights all have to be equal

Because **every model saw exactly the same amount of data (32 of the 40 houses)**
None of them has a structural advantage → **there's no reason to give any one more weight than another**

> If you want to weight them differently, **you need test results to back it up first** — never weight by gut feeling

### ⚠️ A critical condition you must not get wrong (same-basin)

This kind of merge works **only if every model starts from the same starting point**

Analogy: if you have 4 people draw the same house **all starting from the same rough sketch** →
stack their drawings on top of each other and it's still a house ✅

But if each person **starts from their own separate blank sheet of paper** → stacking them gives you a smudge ❌

In technical terms: **they must all use the same LoRA A init** — we nearly got this wrong once before
and it's recorded as a lesson in the Aug 30 diary

### Why we don't evaluate the merged one

Because once the 4 are merged together = **it has already seen all 40 houses**
There are no clean houses left to test it on at all

So we decided (Makham made the call):
- **Evaluate one fold at a time** on the houses that fold has never seen → numbers you can trust
- **The merged one (soup) is not evaluated**, but it's labeled plainly as `unbenchmarked` (not yet measured)
- Saved **$6–9** in eval costs

**A label that tells the truth matters more than a pretty number that means nothing**

---

## Part 5 — Something Makham caught independently (and got right)

> **"Don't use t04's folds, because t04 has no system for tuning pass0/2.5/3"**

Exactly right — and when we went and counted the actual files, that's just what we found:

| fold (split the t04 way) | Held-out test houses: pass1 | pass0 | pass2.4 | pass3 |
|---|---|---|---|---|
| fold1 | 204 | **0** | **0** | **0** |
| fold2 | 204 | **0** | 9 | 2 |
| fold3 | 204 | **0** | 9 | 1 |

**Cause:** t04 split the 40 houses **without knowing that only 10 houses have pass0/2.4/3 data**
(pass0 has only 5 houses!) When the split was randomized, the special houses ended up piled almost entirely on the "train" side

The result: **no special houses left for testing at all → no way to measure whether the model learned to do pass0/pass3 or not**

If we kept using the old folds = even after training we would **still not know** whether it worked

---

## Part 6 — All the lessons summed up in 6 lines

1. **The most expensive bug is the silent one** — not a single error, yet the output is all garbage
2. **A pretty number doesn't mean it's right** — the JSON was correctly formatted 96-100% of the time, yet it couldn't read the drawings at all
3. **You have to open the answer files and look with your own eyes**, not just look at the scores
4. **Always put a cheap gate in place before spending big** — $2 saved $70
5. **Never put the answer key into the questions used for testing**, otherwise you get a fake green result
6. **Before every training run, first measure how many tokens 1 image becomes** (done on a CPU, for free)

---

## Appendix — Where we stand now (Sep 1, 2026)

| Model | Status |
|---|---|
| Purson (t04) | ☠️ Dead — images too small |
| Voldemort (t44) | ☠️ Dead — compressed until it went blind (failed the $2 gate) |
| **Destrier (t05)** | ✅ Training finished, soup merged, on HF (`dacarokann/destrier`) |

**Destrier still has more to prove:** recall has been measured only once, at ~43% (scored leniently on name formatting)
and it **has never once been run through the full pipeline on a real GPU**

On the software side (Constistant) — today, Sep 1, we simulated a run of a whole house without renting a GPU
and **found 8 real bugs, all fixed now**; details are in today's diary
