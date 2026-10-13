# Product Requirements Document: AI Audiobook Creator

**Status:** Draft  
**Version:** 0.1  
**Product:** Working title: PageTurn Audio  
**Last updated:** 2026-09-27

## 1. Product summary

Build a web application that turns a user-provided PDF into an audiobook. The application extracts and prepares the text, uses an AI text model to identify narration and dialogue speakers and describe suitable voices, lets the user review those decisions, then uses a separate text-to-speech model to generate and combine speech into a downloadable MP3.

The initial product focuses on text-based PDFs and a reliable, reviewable audiobook workflow. Scanned PDFs, external story links, synchronized reading, mobile clients, and manga image processing are future extensions.

## 2. Problem and opportunity

Reading a long PDF is not always convenient. Existing generic text-to-speech can read the words aloud but often treats a multi-character story as one voice, loses paragraph structure, or misreads dialogue attribution. Users need a way to turn a story into audio while retaining distinct character voices and control over uncertain AI decisions.

The current repository contains experiments in PDF conversion, OCR, panel extraction, LLM analysis, and Qwen TTS. Those demonstrate relevant capabilities but do not yet form an integrated web product. This PRD defines that product independently of the prototype implementation.

## 3. Goals

- Let a user upload a PDF and produce an MP3 audiobook.
- Preserve the original text and reading order as faithfully as practical.
- Identify narration and likely dialogue speakers, with confidence or uncertainty made reviewable.
- Create reusable voice profiles for speakers based on textual characterization and user choices.
- Give users control to correct text, speaker assignments, voice descriptions, and pronunciation before generation.
- Keep generation progress and outputs associated with a project so users can return to them.
- Design the processing pipeline so other text sources and image-based content can be added later.

## 4. Non-goals for the first release

- Importing stories from AO3 or other websites.
- Live audio playback synchronized with word-level highlighting.
- Android/iOS application packaging.
- Manga panel, image, or speech-bubble interpretation.
- Voice cloning from a real person's recording.
- Fully automatic correction of source text or rewriting of the author's prose.
- Collaborative editing, public sharing, or a marketplace for generated audiobooks.

## 5. Target users and key use cases

### Primary users

- Readers who want to listen to novels, fan fiction, or other personal PDF documents.
- Users who prefer character-aware narration over a single generic voice.
- Users who need accessible audio versions of documents they are authorized to process.

### Core use cases

1. Upload a text-based PDF, inspect extracted text, and generate an audiobook.
2. Review detected speakers and assign distinct voices before generating.
3. Correct a dialogue attribution or pronunciation, regenerate affected audio, and download the result.
4. Return to a project later to download its MP3 or continue an interrupted job.

## 6. Product principles

- **User text is authoritative:** AI can label and route text, but must not silently rewrite it.
- **Review uncertainty:** speaker attribution is a best guess; users can inspect and correct it.
- **Stable character voices:** each speaker should keep the same selected voice throughout a project.
- **Incremental processing:** process in manageable passages and retain completed work after recoverable failures.
- **Privacy by default:** make file retention and deletion understandable and controllable.
- **Model replaceability:** text analysis and speech generation are separate services behind interfaces, not assumptions embedded throughout the app.

## 7. Proposed user journey

1. User creates a project and uploads a PDF.
2. The app validates the file and extracts text, page boundaries, and paragraph structure. OCR is used only when selectable text is unavailable or insufficient.
3. The app shows extraction status and a preview. The user can correct extraction errors or exclude front matter and other unwanted sections.
4. The text model analyzes the content in context and returns ordered passages, speaker candidates, dialogue/narration labels, voice descriptions, and confidence/uncertainty indicators. It must return references to source text rather than replacing it.
5. The user reviews speaker labels and voice profiles, merges duplicate speakers, renames speakers, and assigns or edits voice descriptions. The app provides short voice previews where supported.
6. User selects output settings and starts generation.
7. The TTS service generates audio passage by passage. The app reports progress and preserves completed passages for retry.
8. The app combines passages in reading order into an MP3, makes it available for playback/download, and provides project deletion controls.

## 8. Functional requirements

### 8.1 Project and PDF intake

- Create, list, open, and delete user projects.
- Accept PDF upload with a configurable file-size/page-count limit.
- Validate that the upload is a readable PDF; reject unsupported or corrupt files with a useful message.
- Detect whether a PDF has an extractable text layer. Route scanned/image-only pages through OCR or report that OCR is unavailable.
- Preserve source page and passage references for review and future synchronization.
- Show upload, extraction, analysis, and generation states, including actionable errors.

### 8.2 Text preparation and review

- Extract text in reading order and retain page/paragraph boundaries where possible.
- Normalize only technical artifacts such as repeated whitespace; do not paraphrase or remove content silently.
- Show an editable text preview before generation.
- Allow inclusion/exclusion of sections and edits to text.
- Preserve the original extraction and user-edited version as distinct revisions.
- Identify unsupported languages or low-quality extraction and tell the user before expensive generation.

### 8.3 Speaker analysis (text model)

- Analyze the text in bounded passages with enough surrounding context to resolve references.
- Distinguish narration, unattributed dialogue, and attributed dialogue where possible.
- Return structured data for each passage: exact text/source span, speaker ID or narration, confidence, and optional note explaining ambiguity.
- Maintain stable speaker identities across passages; support aliases and duplicate candidates for user review.
- Infer a concise voice direction from textual evidence (for example, measured, warm, or terse), and separate evidence-based traits from uncertain guesses.
- Never infer a real person's voice or create a clone from prose.
- Allow the user to edit speaker assignments, merge/split speakers, rename speakers, and change voice directions.

### 8.4 Voice profile and assignment

- Create one project-level voice profile per speaker and a narration profile.
- Let users choose from supported voices or use a natural-language voice direction when the selected TTS model supports voice design.
- Keep voice choice and direction fixed across all passages for that speaker unless the user changes it.
- Provide a preview generated from sample text and clearly indicate that preview audio may not perfectly match long-form output.
- Allow pronunciation overrides for names and recurring terms.
- Do not expose voice cloning in the initial version.

### 8.5 Speech generation and output

- Convert each passage using its assigned speaker profile, preserving text and reading order.
- Generate and persist passage-level audio so interrupted jobs can resume and edited passages can be regenerated.
- Support pause/spacing controls between passages and basic output quality settings if supported by the chosen model.
- Combine the passages into a downloadable MP3 and retain a project-level audio manifest mapping passages to audio segments.
- Show generation progress, estimated passage count, failures, and retry actions.
- Validate that the final file is playable and that its duration and size are reported.
- First release may generate a complete file before playback; streaming playback is a later capability.

### 8.6 Privacy and project management

- Provide a clear retention policy for PDFs, extracted text, prompts/model outputs, and generated audio.
- Let users delete a project and its associated files.
- Protect project files from access by other users; use authenticated, expiring download access where applicable.
- Do not use user documents to train models unless the user separately and explicitly opts in.
- Avoid logging document contents, API credentials, or signed download URLs.

## 9. AI model responsibilities

The application uses two primary AI model roles. They may be hosted locally or accessed through a provider API; deployment is an implementation decision.

### Text analysis model: Qwen3.8-Flash (Alibaba Cloud Model Studio)

Responsible for passage-level analysis, speaker attribution, stable character identity, uncertainty reporting, and suggested voice directions. It does not generate the audiobook audio and must not silently rewrite source prose. The selected listing is Qwen3.8-Flash in Alibaba Cloud Model Studio.

The model integration must use a strict structured output schema, preserve source-span references, support passage context, and handle long documents by chunking with cross-chunk character memory. Confirm the API model identifier, endpoint, availability in the selected region, language coverage, and cost/latency targets during implementation. The product decision is to use the Model Studio Qwen3.8-Flash listing, subject to a small integration and quality spike.

### Text-to-speech model: Qwen Voice Design (Qwen3-TTS-VD, Alibaba Cloud Model Studio)

Responsible for rendering each approved passage using its assigned voice profile and producing audio that can be assembled into an MP3. The selected listing is Qwen Voice Design (Qwen3-TTS-VD) in Alibaba Cloud Model Studio. The repository's local Qwen3-TTS experiment provides useful background, but the web app will use the Model Studio service specified by this product decision.

Before production rollout, a technical spike must verify persistent voice consistency across many separate passage calls, supported languages, long-form throughput, audio quality, API behavior, pricing, regional availability, licensing/terms, and reliable MP3 assembly. If voice design does not preserve a reusable speaker identity across calls, the implementation must use a supported persistent voice mechanism or maintain a speaker-specific generation strategy. The product decision is to use the Model Studio Qwen Voice Design listing, subject to that integration validation.

### Model boundary and failure handling

- Define independent `TextAnalyzer` and `SpeechGenerator` interfaces.
- Store model name/version and generation settings with each result for reproducibility.
- Validate structured model outputs before using them; retry or surface invalid responses safely.
- Treat AI outputs as suggestions until confirmed by the user or accepted through an explicit project setting.
- Make model/provider failures retryable without losing edited text or completed passage audio.

## 10. UX and accessibility requirements

- Responsive web layout for desktop and mobile browsers.
- Keyboard-operable upload, review, speaker editing, playback controls, and dialogs.
- Clear status labels that do not rely on color alone.
- Accessible labels and focus states for controls; text remains available alongside audio.
- Long documents must remain navigable, with search or section navigation considered for the MVP if document length requires it.
- Show where a speaker assignment is uncertain and make correction straightforward.

## 11. Non-functional requirements

- **Reliability:** jobs survive browser refreshes and can be retried after recoverable failures.
- **Scalability:** PDF extraction, text analysis, TTS generation, and audio assembly run as background jobs rather than blocking web requests.
- **Security:** validate uploaded files, isolate user data, secure secrets, and apply reasonable upload and job limits.
- **Observability:** record job stage, duration, model identifier, passage counts, and error category without recording private source content by default.
- **Cost control:** estimate or communicate generation workload before starting; support cancellation and avoid duplicate work on retry.
- **Portability:** keep stored source text, project metadata, and audio manifest independent from a specific model vendor.

## 12. MVP scope and acceptance criteria

The MVP is complete when a user can:

1. Upload a supported text-based PDF and see extraction complete or receive a clear explanation of failure.
2. Review and edit extracted text without losing the source page references.
3. See proposed speakers, narration, and uncertain dialogue assignments; edit and approve them.
4. Assign a stable voice to narration and each speaker, preview where available, and add pronunciation overrides.
5. Generate speech, observe progress, retry a failed passage, and resume a job after leaving the page.
6. Download a valid MP3 in the original reading order.
7. Delete the project and its stored files.

### MVP success measures

- Percentage of supported PDFs that reach a generated audiobook without manual support.
- Text extraction correction rate and speaker attribution correction rate.
- Percentage of generation jobs completed, retried successfully, or abandoned by stage.
- Median processing time and estimated generation cost per source page/hour of audio.
- User rating for speaker distinction, voice consistency, and pronunciation quality.

Targets should be set after a representative PDF and voice-quality evaluation set has been selected.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Scanned or complex PDFs extract poorly | Detect text quality early; offer OCR and a review screen; report unsupported cases. |
| Speaker attribution is ambiguous | Return uncertainty, use context, and make correction a first-class workflow. |
| Character voices drift between TTS calls | Test long-form consistency before model selection; use stable speaker profiles and reusable voice IDs if available. |
| Long books exceed model context or job limits | Chunk passages, preserve context summaries and IDs, run asynchronous jobs, and checkpoint results. |
| Audio generation is slow or expensive | Estimate workload, process incrementally, allow cancellation, and retry only failed/changed passages. |
| Model/provider versions change | Record model identifiers and settings; isolate providers behind interfaces and run regression samples before upgrades. |
| Copyright or privacy concerns | Restrict user content access, define retention/deletion, and require users to confirm they have rights to process their files. |
| TTS cannot deliver the required MP3 directly | Produce a supported intermediate audio format and transcode in the backend with verified tooling. |

## 14. Future roadmap

### Phase 2: story links

- Accept AO3 links where access and site rules permit.
- Extract story chapters and metadata into the same normalized text and project format as PDFs.
- Support chapter-by-chapter generation and downloads.

### Phase 3: synchronized reading

- Play generated audio in the browser.
- Highlight the current sentence or passage and keep the text view synchronized.
- Preserve passage timing metadata; word-level timing is a later enhancement if alignment quality supports it.

### Phase 4: mobile app

- Package or build an Android client using the same account, project, and generation APIs.
- Support background downloads and offline playback.

### Parallel/future product: manga audiobook

- Add image/PDF page understanding, panel ordering, speech-bubble OCR, speaker linking, and visual context.
- Reuse the project, speaker, voice, TTS, and audio assembly services where possible.
- Treat this as a separate product mode because manga requires visual interpretation beyond the initial text-only workflow.

## 15. Open questions

- Which languages and writing systems are in the first supported release?
- What are the initial PDF size, page-count, and per-user generation limits?
- Is the first deployment expected to run Qwen models locally, through a hosted inference service, or through an API?
- What API model identifiers, endpoint configuration, and availability apply to the selected Model Studio listings in ap-southeast-1?
- Should PDF text editing happen inline, in a chapter/section editor, or both?
- What retention period should apply to uploaded PDFs and generated audio?
- What MP3 bitrate and expected maximum audiobook duration should the product target?
- Is user authentication required for the first usable release, or is this initially a single-user/private deployment?

## 16. Selected model listings

The product decision is to use these two Alibaba Cloud Model Studio listings, configured for the ap-southeast-1 console region and international service site as shown in the supplied links. The console pages could not be independently inspected during this edit, so exact API identifiers, endpoint details, prices, regional availability, and terms must be confirmed in Model Studio before integration. This does not change the selected model choices.

- Text analysis: [Qwen3.8-Flash](https://modelstudio.console.alibabacloud.com/ap-southeast-1/model/market/detail/qwen3.8-flash?serviceSite=international&ref=list)
- Text-to-speech: [Qwen Voice Design / Qwen3-TTS-VD](https://modelstudio.console.alibabacloud.com/ap-southeast-1/model/market/detail/qwen-voice-design?serviceSite=international&ref=search_result&kw=qwen3-tts-vd)
