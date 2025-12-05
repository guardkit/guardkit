# Content Creation Tools for GuardKit Promotion

## Overview

Research into tools for creating promotional content for LinkedIn, X, CTO Craft Slack, etc. Focus on GIFs, short videos, and meme-style imagery showing the `/feature-plan` workflow.

---

## Quick Recommendation

**For your specific use case (terminal demo GIF):**

1. **Fastest path:** Kap (free, Mac) → Record → Export as GIF
2. **Best quality:** Screen Studio ($89) → Auto-zoom effects, professional look
3. **You already have:** Adobe Premiere Pro → Record with QuickTime, speed up, export as Animated GIF

---

## Screen Recording to GIF Tools

### Free Options (Mac)

| Tool | Pros | Cons | Best For |
|------|------|------|----------|
| **Kap** | Free, open-source, direct GIF export | Basic features | Quick terminal demos |
| **LICEcap** | Records directly to GIF, lightweight | Old UI | Simple captures |
| **GIPHY Capture** | Free on Mac App Store, easy | 30 second limit | Social media GIFs |
| **Gifski** | High quality GIF conversion | Need separate recording | Converting MOV→GIF |

**Kap** (https://getkap.co/)
- Open source, free
- Record screen → Export as GIF, MP4, WebM, or APNG
- Built-in trim tools
- Recommended for quick terminal demos

**LICEcap** (https://www.cockos.com/licecap/)
- Records directly to GIF (no conversion needed)
- Very lightweight
- Free (GPL)

### Premium Options

**Screen Studio** ($89 one-time) - https://screen.studio/
- Specifically designed for product demos
- Auto-zoom on clicks/cursor
- Professional motion effects
- Direct GIF export
- Many indie makers use this for launch videos
- **Highly recommended for polished demos**

**CleanShot X** ($29 or via SetApp)
- Screenshot + recording + GIF
- Quick cloud upload
- Good for frequent use

---

## Using Adobe Creative Cloud (You Have This)

### Workflow: QuickTime → Premiere Pro → GIF

1. **Record with QuickTime** (Cmd+Shift+5)
   - Select area around terminal
   - Record the `/feature-plan` workflow
   - Save as .mov

2. **Import to Premiere Pro**
   - Create new sequence (640x360 or 1:1 square for social)
   - Set frame rate to 15fps for GIF

3. **Speed up the video**
   - Right-click clip → Speed/Duration
   - Set to 200-400% (experiment)
   - Or use Rate Stretch tool for manual control

4. **Export as Animated GIF**
   - File → Export → Media
   - Format: "Animated GIF" (not just "GIF")
   - Keep under 500x500 and 15fps for reasonable file size

### Tips for Premiere Pro GIFs
- GIFs limited to 256 colours - can cause dithering
- Keep clips under 10-15 seconds
- For better quality: export as video, then use Gifski or ezgif.com to convert

### After Effects Option
- More control over motion graphics
- Can add text overlays, annotations
- GIFGun plugin for better GIF export

---

## AI Video Tools Analysis

### Sora 2 (OpenAI)
**Not suitable for this use case.**

Sora 2 is for generating cinematic videos from text prompts (e.g., "a robot walking through neon-lit streets"). It's not for:
- Screen recordings
- Terminal demos
- Product walkthroughs

**When Sora 2 would be useful:**
- Creating atmospheric/conceptual marketing videos
- "Developer working late, AI helping them ship" type content
- Brand videos, not product demos

### Other AI Tools
- **Invideo** - Can use Sora 2 for creative clips
- **Runway** - Video editing with AI features
- **Descript** - Good for editing talking-head videos

---

## The "Take Back Control" Meme Idea

Love this concept - referencing the UK government's Brexit campaign with a developer twist.

### Possible Execution

**Option A: Static Meme Image**
- Recreate the "Take Back Control" poster style
- Replace with "TAME THE BEAST" or "TAKE BACK CONTROL" 
- Subtext: "of your AI-assisted development"
- Show `/feature-plan` command

Tools: Canva (free), Adobe Express, or Photoshop

**Option B: Animated Version**
- Start with chaotic AI code generation (fast, scary)
- Slam to "TAKE BACK CONTROL"
- Show calm, structured `/feature-plan` output

**Tagline Options:**
- "Take Back Control" → of your AI workflow
- "Tame the Beast" → with Feature Plan Development
- "One Command to Rule Them All" → `/feature-plan`
- "Stop the Chaos" → Plan first, build faster

---

## Content Format Recommendations

### For LinkedIn
- **Best:** Native video (gets more reach)
- **Good:** GIF embedded in post
- **Format:** Square (1:1) or 4:5 for mobile
- **Length:** 30-60 seconds max

### For X/Twitter
- **Best:** GIF or short video
- **Format:** 16:9 or 1:1
- **Length:** Under 15 seconds for GIFs
- **Note:** GIFs auto-play, video doesn't always

### For CTO Craft Slack
- **Best:** GIF (loads inline)
- **Keep it:** Short, punchy, technical
- **Audience:** CTOs want to see efficiency, not fluff

---

## Recommended Workflow

### Quick Demo GIF (5 minutes)

```bash
# 1. Install Kap
brew install --cask kap

# 2. Open Kap, select terminal window area

# 3. Record:
#    - Type: /feature-plan "implement dark mode"
#    - Show output being generated
#    - ~10-15 seconds total

# 4. Export as GIF
#    - 15fps
#    - Scale to 640px wide
```

### Polished Demo Video (30 minutes)

1. Record with QuickTime (full quality)
2. Import to Premiere Pro
3. Speed up boring parts (file creation, etc.)
4. Add text annotations if needed
5. Export as MP4 for LinkedIn/YouTube
6. Export as GIF for X/Slack

### "Take Back Control" Graphic (15 minutes)

1. Open Canva or Adobe Express
2. Use bold, campaign-poster style template
3. Main text: "TAKE BACK CONTROL"
4. Subtext: "of your AI-assisted development"
5. Show `/feature-plan` command
6. Export for social

---

## File Size Guidelines

| Platform | Max GIF Size | Recommended |
|----------|--------------|-------------|
| X/Twitter | 15MB | Under 5MB |
| LinkedIn | 200MB (video) | Under 10MB |
| Slack | 128MB | Under 5MB |
| GitHub README | No limit | Under 3MB |

### Compression Tips
- Use ezgif.com/optimize for quick compression
- Reduce colours, frame rate, dimensions
- Consider WebM for better quality at smaller size

---

## Summary: What to Use When

| Goal | Tool | Time |
|------|------|------|
| Quick terminal GIF | Kap | 5 min |
| Polished demo video | Screen Studio | 15 min |
| Speed up existing video | Premiere Pro | 10 min |
| Meme/poster graphic | Canva | 15 min |
| Cinematic brand video | Sora 2 | 30 min |

---

## Resources

- Kap: https://getkap.co/
- Screen Studio: https://screen.studio/
- Gifski: https://gif.ski/
- ezgif.com (online GIF tools): https://ezgif.com/
- Canva: https://canva.com/
