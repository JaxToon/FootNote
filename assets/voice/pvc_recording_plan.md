# Professional Voice Clone (PVC) Recording Plan — F/N Narration

Use this plan only for the owner's own voice. PVC is created and verified in the owner's ElevenLabs account; this repository does not upload PVC training data automatically.

## Target dataset

- Provider guidance: 30 minutes is a practical lower bound; the current Professional Voice Cloning guide recommends at least 1 hour and ideally close to 3 hours. Aim for 1–3 hours only when consistent recording quality and delivery can be maintained. Clean, consistent audio is more important than padding the duration.
- Prioritize clean, consistent audio over duration. Do not pad the dataset with noisy, reverberant, or differently processed recordings.
- Record in the language and accent used in production: natural Indonesian with the English technical vocabulary you use when explaining data and technology.
- Keep the performance style consistent: friendly, thoughtful, conversational, clear, and confident without sounding like a formal newsreader or advertisement.

## Recording setup

- Quiet, acoustically controlled room; no fan, traffic, keyboard, music, or other speaker.
- Same microphone, position, distance (approximately 15–20 cm), pop filter, input gain, and room for all sessions.
- Capture dry speech without reverb, EQ, aggressive denoising, compression, or normalization baked into the source.
- Avoid clipping, plosives, mouth clicks, long silences, and abrupt edits.
- Record at a stable sample rate and use high-quality MP3 (192 kbps or above) or a provider-accepted WAV source.

## Suggested session structure

Make multiple 10–20 minute sessions, not one exhausting marathon. Keep the same recording setup and baseline delivery. A practical dataset can include:

1. **Core explanation (35%)** — define concepts in everyday Indonesian, explain cause/effect, compare ideas, and walk through examples.
2. **Data and technical narration (25%)** — say SQL, Python, statistics, machine learning, API, dashboard, model metrics, and common English technical terms naturally.
3. **Question and hook delivery (15%)** — short questions, myth-busting lines, and curiosity-led hooks, still in the same natural voice.
4. **Careful reasoning (15%)** — limitations, assumptions, uncertainty, caveats, and evidence-based explanation.
5. **Recap and CTA (10%)** — concise summaries and invitations to continue learning, without sales-like shouting.

Do not switch between whispering, shouting, comedic acting, and formal reading in the same dataset unless that range is genuinely part of the intended channel narration style.

## Quality control

- Listen to every session before upload. Remove bad takes and noisy sections rather than relying on post-processing.
- Do not mix old phone recordings with new microphone recordings unless the quality and tone are genuinely consistent.
- Keep a private backup of all source recordings and a note of which files were used in each clone version.
- After PVC training completes, test it with the exact same 30–60 second Indonesian F/N audition script used for IVC/model comparisons.
- Reject the clone if the accent, consonants, sentence endings, or cadence do not sound recognizably like the owner. Record better source material and retrain rather than trying to hide the mismatch with editing.

## Suggested audition lines

Use the following lines consistently for comparisons:

> Pernah nggak, kamu melihat dua hal bergerak bersama, lalu langsung menyimpulkan bahwa salah satunya menyebabkan yang lain? Di data science, pola seperti ini menarik, tapi kita tetap perlu bertanya: apa yang sebenarnya terjadi di balik hubungan tersebut? Kita akan membedah konsepnya pelan-pelan, menggunakan contoh sederhana, lalu melihat kapan kesimpulan itu bisa dipercaya.


## Local preflight

After recording the dataset, place the clips in `private/voice_samples/pvc/` and run:

```powershell
fnvideo voice check-samples --profile pvc --samples private/voice_samples/pvc/*.mp3
```

This checks file readability and duration only. It cannot judge whether the room, mic, accent, or vocal delivery is clean and consistent; listen to all source clips before upload.
