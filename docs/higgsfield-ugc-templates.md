# AYARI — Higgsfield UGC Generation Templates
# Used by: n8n Workflow A (content_type = "ugc")
# Last updated: 2026-06-01

---

## WHAT GOOD AI UGC LOOKS LIKE

Great AI UGC passes the "did a real person film this?" test.
The brands that do it best (AG1, Ritual, Lemme, LYMA) follow the same rules:

**Looks real because:**
- Slightly imperfect natural lighting — kitchen window, bathroom, desk lamp
- Model is mid-action (pouring powder, reaching for a bottle, drinking)
- Background has life in it — dishes, plants, books, unmade bed
- Not looking directly into camera OR looking naturally, not posed
- Clothes are normal — oversized shirt, gym wear, casual everyday

**Looks fake because:**
- Studio lighting, perfect backdrop
- Model stares directly at camera holding product like a trophy
- Setting is completely empty/white
- Skin is airbrushed beyond recognition
- Expression is frozen smile

---

## LEGAL RULE — CRITICAL

**Never attach a fake name to AI UGC.**
"Anna M., Berlin — dieses Produkt hat mein Leben verändert" = illegal under German UWG.

AI UGC shows a person using the product.
The caption tells the story — written in AYARI's voice, not as a fake customer.

✅ Correct: AI video of woman making morning coffee + AYARI Magnesium Komplex
Caption: "Deine Abendroutine entscheidet, wie du morgens aufwachst. Magnesium Komplex — die Formel für echte Regeneration."

❌ Wrong: Same video + "Sarah K.: Seit 3 Wochen schlafe ich endlich durch!"

---

## AVATAR GUIDELINES

When selecting avatars in Higgsfield Marketing Studio:

**Target for @ayari.longevity:**
- Women 28–45 (primary audience)
- Natural appearance — not model-perfect, relatable
- Diverse representation — not always the same face
- Style: minimal makeup or no makeup, natural hair, everyday clothing

**Avoid:**
- Hyper-glamorous looks
- Very young (under 25) for supplement content
- Overly masculine — the audience is primarily women

---

## SCENE TEMPLATES BY PRODUCT

Use these with `higgsfield generate create marketing_studio_video --mode ugc`

---

### Magnesium Komplex — Evening / Sleep Scenes

**Scene A: Abendroutine**
```
Prompt: Woman in her late 30s, casual home clothes, soft warm lamp light,
sitting on a bed or couch in the evening. She opens a dark amber glass jar,
pours two capsules into her palm, takes them with a glass of water.
Natural, relaxed gesture. Not looking at camera.
Background: soft bedroom, blurred fairy lights, book on nightstand.
Feel: calm, intentional, premium wellness routine.
```

**Scene B: Nach dem Sport**
```
Prompt: Woman in gym clothes, standing in a naturally lit kitchen.
She holds a dark amber glass jar (capsules), opens it and takes two capsules.
Post-workout feeling — slightly flushed cheeks, hair in a bun.
She looks at the jar briefly then sets it down.
Background: kitchen counter, water bottle, fruit.
Feel: recovery, natural, everyday athlete.
```

---

### Kollagen+ — Morning / Beauty Scenes

**Scene A: Morgenkaffee**
```
Prompt: Woman in her early 40s, silk robe or oversized shirt.
She scoops a spoonful of powder from a premium pouch and stirs it into
her morning coffee or warm water. Soft morning window light from the side.
She wraps her hands around the mug — content, unhurried.
Background: marble kitchen counter, soft natural light, plant in corner.
Feel: luxurious morning ritual, beauty from within.
```

**Scene B: Smoothie Routine**
```
Prompt: Woman, natural no-makeup look, adding a scoop of collagen powder
to a blender with fruits. She laughs slightly at the powder cloud.
Bright natural kitchen light. Authentic, slightly imperfect.
Background: real kitchen, not styled — a normal home.
Feel: effortless health habit, genuine.
```

---

### NMN+ — Performance / Focus Scenes

**Scene A: Morgen-Setup**
```
Prompt: Woman or man in their late 30s to mid 40s, business casual or
home office setting. Opens a small premium pouch, measures a tiny scoop
of white powder, stirs it into a glass of water. Looks focused, purposeful.
Background: standing desk, laptop, morning light.
Feel: high performer, intentional, science-backed routine.
```

**Scene B: Pre-Workout**
```
Prompt: Athletic woman in her late 30s, gym bag visible, pre-workout moment.
She mixes NMN powder into water in a clear glass.
Purposeful gesture, she knows what she's doing.
Background: kitchen or gym entrance, natural light.
Feel: serious about performance, not a beginner.
```

---

### Kreatin+ — Energy / Workout Scenes

**Scene A: Pre-Training**
```
Prompt: Woman in gym wear, kitchen setting, mixing a scoop of white powder
into a shaker bottle. She looks energized, focused. Shakes it briefly.
Natural kitchen light, slightly messy counter (real life).
Background: gym bag on chair, keys on counter.
Feel: ready to train, real person not fitness model.
```

---

### Vitamin D3/K2 — Foundation / Daily Habit Scenes

**Scene A: Morgen-Routine**
```
Prompt: Woman in her late 30s, natural morning light from window.
She holds a small dark dropper bottle, drops one drop onto a spoon or
directly into her mouth. Simple, clean gesture. One second.
Background: bathroom counter or kitchen, toothbrush/coffee cup visible.
Feel: effortless daily habit, invisible health foundation.
```

---

### Omega-3+ — Lifestyle / Daily Routine Scenes

**Scene A: Mit dem Mittagessen**
```
Prompt: Person at a kitchen table eating a light lunch.
They reach for a dark amber softgel bottle, pop one capsule, take it
naturally with water — while reading or looking out the window.
Not looking at camera. Background: real dining setting, natural light.
Feel: seamlessly integrated into daily life.
```

---

## PROMPT TEMPLATE (reusable structure)

Fill in the blanks for any product:

```
[Woman/Person], [age range], [setting — kitchen/bedroom/desk/gym].
[Action with product — specific gesture].
[Lighting — morning window light / warm lamp / natural daylight].
[What they're doing around the product — multi-tasking or focused].
[One authentic imperfection — messy background, natural hair, slight movement].
Background: [real home detail — plant, book, coffee cup, laptop].
Feel: [emotion/mood — calm / focused / intentional / effortless].
Do NOT: direct camera stare, perfect backdrop, stock photo feel, obvious AI.
```

---

## n8n IMPLEMENTATION

In the n8n Code Node, pull the product and content type from today's plan,
then select the matching template above and pass it as the `--prompt` flag:

```javascript
// Pseudo-code: select UGC template by product
const product = todayPost.product_focus; // e.g. "Magnesium Komplex"
const ugcTemplates = {
  "Magnesium Komplex": "Woman in her late 30s, casual home clothes...",
  "Kollagen+": "Woman in her early 40s, silk robe...",
  "NMN+": "Woman or man in their late 30s to mid 40s...",
  // etc.
};
const prompt = ugcTemplates[product] || ugcTemplates["default"];
```

Then the HTTP Request node calls Higgsfield:
```
POST marketing_studio_video
--mode ugc
--prompt [selected template]
--product_ids [AYARI product registered in Higgsfield]
--duration 15
--aspect_ratio 9:16
--resolution 720p
```

---

## QUALITY CHECK BEFORE ✅

Before tapping ✅ in Telegram, ask yourself:
1. Could this be a real person? → Yes = good
2. Does the background look lived-in? → Yes = good
3. Is the product visible but not "hero-posed"? → Yes = good
4. Does the lighting look natural? → Yes = good
5. Would I scroll past this thinking it's organic? → Yes = post it

If any answer is No → tap ✏️, regenerate with adjusted prompt, or swap to a product lifestyle image instead.
