# SSS2026 Interactive Learning Reports — production deployment plan

Version 1.0 · 15 September 2026 · prepared from the V4.9 prototype round and the deployment discussions of this session

This document is the working plan for taking the bilingual Interactive Learning Report from a single prototype (Ysgol Penrhyn Dewi, dummy data) to a published set of just under a thousand school reports, plus local authority and regional reports, each reachable at its own unique web link on the Sport Wales website. It records what has been agreed, the reasoning behind each choice, the rules every production build must obey, the figures we have measured, the checks that will run at scale, the order of work, and the decisions that still sit with Sport Wales. It is written so that anyone picking it up can follow it without the conversation that produced it. Every number quoted below was computed during the V4.9 round; where a figure is an estimate derived from those measurements it is marked as such, and where a figure has not yet been measured the plan says so and names the phase in which it will be.

---

## 1. Where we are starting from

The V4.9 prototype is a single self-contained HTML file, `SSS2026_ILR_Report_V4.9_Bilingual.html`, 179,445,060 bytes, sha256 `9eb4006a38a8a77dc74b8b90bcecb5463d0ff98ca6a2f2b1372f69cb6d9fa914`. It carries the whole report for one school of 366 pupils: the template, the client script, the fonts and cover media, and a pre-computed payload of 8,568 filter states (every combination of scope, gender and cohort the reader can select), so that the page never computes a statistic in the browser and never needs a server. The English narrative in that payload is byte-identical to V4.1, proven by the GOV-lock gate and by a record-level comparison of 316,968 English and Welsh records and 41,650 stack sets against V4.8 with zero differences. The Welsh is generated from fact records through the Framework v2.2 workbook and lexicon; nothing in it is translated or invented, and a missing lexicon entry fails the build.

The assurance position at the end of the round is: in-build stamp 69/72 with two gates pending and one disputed; stock gate pack v7 rerun on the shipped file 71/72 in dev mode and 71/75 in release mode (the shortfall being STK-caption-case, a verified pack defect, and the three release-only gates that wait for the translator's 356 values and the owner's signed D69); renderer paths 17/18; jsdom regression 53/53; jsdom port of browser gate v3 with 0 English-without-provenance, 0 typography faults and a 1,848/1,848 fixture toggle; pytest 76 passed, 1 skipped. Selftest of the vendored runner is 68/68.

Two facts about the payload shape drive the architecture. The states are 178.8 MB of the 179 MB file (module narrative 112.3 MB, m 26.8, stacks 13.9, h1 11.2, h2 4.8, scope 4.0, rows 3.5), which is roughly 39 KB per state; everything that is not a state is 0.16 MB. The whole payload compresses to 20.2 MB with gzip. In other words the report is a very small application sitting on top of a large but highly regular and highly compressible block of pre-computed states, and a reader only ever looks at one state at a time.

The build environment facts that matter for planning are also recorded here. The cloud sandbox used for this round has two cores and about 29 GB of free disk. The local Windows sandbox on the working PC has about 3 GB of RAM and 1.6 GB of free disk, and one build needs around 600 MB of working files. Neither is a production build farm; section 6 sets out what is.

---

## 2. The architecture we have agreed

Two options were on the table: a shared template that pulls each school's data from a combined data repository at view time, or one generated report per school. The decision is a specific form of the second option, with the best property of the first borrowed for the client code. The reasoning is as follows.

A report that fetches from a live data repository has a server, a query layer, an authentication layer and a dependency between what a reader sees and what a database returns at that moment. Each of those is a place where a report can change after it has been checked, and none of them is covered by the gate pack, which examines a finished artefact. The whole value of the V4.9 assurance position is that a checked file is the file that is served. That value is preserved only by pre-generating everything.

A monolithic 179 MB file per school, however, is not something a school on an ordinary connection should have to download to read one page, and a thousand such files are awkward to host, check and move. The resolution is to keep the generation model exactly as it is (one complete, gate-checked package per school, produced by one build) and to change only how the finished package is written to disk and read by the browser.

The agreed shape, then, is this.

Every school has its own report directory, produced by its own fresh build from the canonical dataset, and nothing in that directory depends on any other school's build. The directory holds a small core page (the template with the school's static furniture stamped in, the client script, the non-state payload, and the first state inlined so the page renders without a network request), and beside it a set of state chunk files. The client's `DATA.states[key]` lookup, which today reads from an in-memory object, becomes a fetch-and-cache: when the reader selects a filter whose state is not yet loaded, the client fetches the chunk that contains it, caches it, and renders. The reader's experience is unchanged; the initial download drops from 179 MB to the size of the core page plus one chunk.

The client script and template are shared in the sense that every school's build uses the same frozen release of them, so a fix to the client is a fix for every school in the next regeneration. They are not shared at serving time in a way that could let a later change alter an already-published report: each release tag publishes its own immutable copy of the client assets, and each report's core page references the tag it was built with.

The only data source for any build is a canonical, cleansed dataset (parquet) produced once from the response export, filtered by school identifier inside the build. No build reads a spreadsheet, a previous report, a previous package or another build's intermediate files.

A manifest, one row per report, is the register of what exists, what was built from what, what the gates said, and where it is published. It is the source of the links the website shows and the input to every check in section 8.

Hosting is static object storage behind a CDN. There is no application server in the serving path. The website's content management system holds, for each school and each local authority, a link to that report's directory; the report itself is not inside the CMS.

---

## 3. Hosting, links and access

### 3.1 Link scheme

Each report lives at a directory of the form

    https://reports.<sportwales-domain>/2026/<token>/

where `<token>` is derived from the school's identifier by a keyed hash (HMAC-SHA256 over the school id with a secret key held by Sport Wales, truncated to a fixed length). The token is stable for a given school and key, so links can be issued once and reused for the year, but it cannot be guessed from the school's name, number or position in any list, and knowing one school's token reveals nothing about another's. Local authority and regional reports use the same scheme over their own identifiers, under `/2026/la/<token>/` and `/2026/region/<token>/` so that the manifest and the checks can tell the three families apart.

The secret key is not stored in the repository, in the manifest or in any build output. It is held by Sport Wales; the build farm receives the computed tokens through the manifest, never the key. If the key is ever exposed, the response is to compute new tokens and republish the same files under new directories; the report contents do not change and do not need to be rebuilt, because the token is a property of the path, not of the file.

The directory index is the report's core page, so the link above opens the report directly. Within a report the existing URL contract continues to work: the filter state is carried in the fragment (`#scope=…&gender=…&cohort=…&lang=…`), so a reader can bookmark or share a particular view, and the language toggle is preserved.

### 3.2 Storage and delivery

The candidate platforms are Azure Blob Storage with static website hosting, Amazon S3 with CloudFront, or Cloudflare Pages. All three serve static files from a directory tree over HTTPS with a CDN in front, all three support the configuration items below, and the choice can follow whichever provider Sport Wales' web estate already uses. The plan does not depend on the choice.

The serving configuration must provide: HTTPS only; gzip or brotli compression of the JSON chunks (the payload compresses roughly nine to one, which is the difference between a usable and an unusable report on a school connection); long-lived immutable caching for chunk files and tagged client assets, which never change once published; an `X-Robots-Tag: noindex, nofollow` header on everything under `/2026/`, and a matching `robots.txt`, so that the reports are not indexed by search engines; directory listing disabled at every level, so that the set of tokens cannot be enumerated; and a 404 response, not a redirect to anything informative, for an unknown token.

### 3.3 Access control — a decision for Sport Wales

An unguessable link is a form of access control, but it is not authentication. Anyone who is given the link, or who finds it forwarded, can open the report. Sport Wales must decide which of the following it wants, and the decision determines part of the work in section 9.

The first option is unlisted links only. Each school receives its link directly; the CMS shows links to LA and regional reports openly, or behind whatever the website already uses for partner content. This is the simplest option, is fully compatible with static hosting, and is appropriate if the report content is aggregated and suppressed to the level Sport Wales is already comfortable publishing in other formats.

The second option is login-gated access. School reports sit behind a sign-in, most naturally the same Hwb or Sport Wales account a school already uses. This requires either an authenticating proxy in front of the static store or signed short-lived URLs issued after login. It is still compatible with pre-generated reports (the files are unchanged; only who can fetch them is controlled), but it adds a component to operate and to test.

The recommendation is to settle this before the pilot in section 9, because the pilot must exercise the real serving path. The plan is written so that either choice works; it is the suppression rules and the sensitivity of the smallest schools' figures that should drive the decision, and those are matters for the report owner.

### 3.4 Website integration

The Sport Wales website does not host the reports; it links to them. Integration is therefore a data import into the CMS: for each school and local authority, the token URL from the manifest, the report's title in both languages, and the publication status. The import is generated from the manifest by a small script and reviewed before it is applied. A later regeneration that changes files but not tokens needs no CMS change at all; a token rotation is a re-import of the same list.

---

## 4. The data source and the manifest

### 4.1 Canonical dataset

The response export that the prototype consumed is a workbook. For production, the export is cleansed once, by the existing cleansing steps, into a single canonical parquet file with one row per pupil response and a `school_id` column, and that file's sha256 is recorded. This is the only data input any report build may read. The build's loader takes a school id, reads the canonical file, filters to that school, and refuses if the school is absent or if the filtered frame has a shape the framework does not expect. The same loader with an LA or region filter feeds the LA and regional builds.

Producing the canonical file is itself a checked step: the row count per school and the national totals are written to a small reconciliation table at the time the file is made, and section 8 compares every report's headline counts back to it.

### 4.2 The manifest

The manifest is a plain table (CSV for reading, SQLite for querying; both derived from the same source) with one row per report and the following columns: report family (school, LA, region); identifier; display names in English and Welsh; the profile the build uses (see section 7 for LA and regional profiles); the token and the resulting URL; the release tag the report was built with; the canonical dataset sha256; the build start and end times and the machine that built it; the gate results headline (dev and release, and the renderer path count) copied from the report's own stamp; the sha256 of every file in the report directory; the hosting verification result and time; the publication status (built, verified, published, withdrawn); and free text for any exception raised during the build.

The manifest is written by the build runner and the checkers only, never by hand, and it is the single place the state of the whole set is read from. The rollup in section 8 is a query over it.

---

## 5. Guarding against hallucination and compounded error

This section answers the concern raised directly during planning, because it is the concern that matters most in a bilingual public report and because the answer is structural rather than a matter of vigilance.

There is no language model, and no non-deterministic component of any kind, in the path that produces a report. Every sentence of English narrative comes from a fixed template keyed by the fact record it describes; every Welsh sentence is generated by the grammar engine from the same fact record through the workbook's lexicon, frames and rulings. Given the same release tag, the same framework workbook and the same input rows, the output is the same bytes. Hallucination in the sense of a system inventing text it was not given is not possible in this pipeline, because there is no component capable of it.

The risks that do exist are of a different kind, and the pipeline is built to make each of them fail loudly rather than pass silently.

The first is a template path that no report has exercised yet. With 366 pupils in one school, some combinations of values in some modules have simply not occurred, and a thousand schools will exercise combinations the prototype never did. The design response is that the engine does not fall back: a Welsh string with no lexicon entry, a provisional ruling wording the PR_KEYS regexes do not recognise, a count noun phrase not in the sheet 50 table, or a static node without a handoff row each raises and stops the build. The `_MISSES` registry records every miss; in dev mode a `⟪missing:key⟫` marker is rendered so a reviewer sees it, and in release mode the build refuses. The expectation, stated plainly so that it is not mistaken for a failure of the plan, is that the first full run will produce a handful of refusals from schools whose data reach template paths the prototype did not. Each such refusal is fixed at source (a lexicon row, a ruling, a framework decision recorded in the compliance record) and the affected schools are rebuilt from scratch. A refusal is the system working.

The second is drift between the English and Welsh corpora or between two builds of the same school. The lock mechanism (`lock_V49_v7.json`, per-state hashes of both corpora and the FT-11 key set) already proves that V4.9 reproduces V4.8's text exactly. At scale the same mechanism is applied in two ways: the corpus of template strings and static keys is locked per release tag, so any change to what the pipeline is capable of saying is a deliberate, versioned event; and the byte-compare rebuild in section 8 proves that the same input produces the same output on a second machine.

The third is compounding, meaning an error in one output propagating into the next. This is addressed by the build contract in section 6: no build reads any output of any other build, so there is no channel through which an error could propagate. A defect in the release affects every report built from that release identically, which is precisely why it is detectable (the same gate fails on every report, and the rollup shows it) and precisely why the remedy is a new tag and a complete regeneration rather than a patch.

The fourth is a workbook defect. The workbook is the source of truth, and the rule that has governed nine rounds continues: the pipeline implements what the workbook says, and where the workbook is wrong the build raises it in the compliance record for the report owner or the linguist to correct in the workbook. No code ever "corrects" the workbook, and no gate is ever satisfied by matching its pattern rather than by meeting its intent. At scale the mechanism for raising a workbook defect is unchanged; what changes is that the first full run will surface more of them in one go, which the sequence in section 9 allows time for.

The fifth is the human lane. The translator's 356 values and the owner's signed D69 are inputs the pipeline cannot generate. Until they exist every build is a dev build, the review marker shows English under a pending flag for untranslated static furniture, and the release-mode gates CAT-values, CAT-marker and GOV-mode fail by design. Publication requires release mode; the plan therefore has a hard dependency on those inputs, and section 10 lists them.

---

## 6. The fresh-start build contract

These are the rules the production build runner enforces. They are written as rules because they will be encoded as checks in the runner, and because the answer to "is every one of these reports an exact, independent product of the original template and the source data?" must be yes by construction, not by assurance after the fact. A build that violates any rule stops and records the violation in the manifest; it never produces an output.

Rule 1, frozen release. A production build runs only from a tagged release of the repository. The tag's manifest lists the sha256 of every file that participates in a build: the pipeline modules, the client script and template, the framework workbook, the lexicon, the vendored gate packs, the locks, the fonts and cover media. At start-up the runner recomputes every hash and refuses on any mismatch. A working copy with an uncommitted change cannot build a production report.

Rule 2, empty working directory. Each build begins in a directory the runner has just created and verified to be empty, and ends by deleting it after the outputs have been copied to their write-once destination. Nothing survives from one build to the next on the build machine except the frozen release and the canonical dataset.

Rule 3, input allowlist. A build may read exactly three things: the frozen release, the canonical dataset (filtered to its school inside the loader), and its own row of the manifest, which supplies the identifier, the profile and the token. The runner records the sha256 of the release manifest and of the canonical dataset in the report's build identity. Any attempt to open another path, in particular anything under a previous build's output directory, is refused by the loader.

Rule 4, no reuse of intermediates. The staged build's chunk pickles, package pickle and assembled payload exist only inside the build's own working directory. Reusing a state chunk, a lexicon build or a stamped template from another school or a previous run is prohibited in production, and the runner does not expose an option for it. Where the prototype rounds used chunk reuse to save time during development, that path is disabled by the production flag.

Rule 5, full gates every time. Every build runs the complete vendored gate pack (selftest first, then the in-build run, then the two stock reruns on the written file with the bundle asserted) and the jsdom regression and browser-gate port. A blocking failure that is neither in the recorded pending list nor the recorded disputed list stops the build; no output is written. The gate stamp, the evidence files and the bundle are produced for every report exactly as they were for the prototype.

Rule 6, write-once outputs. A report directory is written once, into a location the runner does not have permission to modify afterwards. The sha256 of every file is recorded in the manifest at write time. The hosting verifier (section 8) compares what is served against those hashes, and a mismatch marks the report as withdrawn until it is regenerated.

Rule 7, identity written once. Each report carries a single build identity (release tag, framework sha256, runner version and sha256, gate manifest hash, canonical dataset sha256, mode), and every legacy or display field is derived from it. There is no second place a version can be stated.

Rule 8, change means regenerate. Any change to the release (a lexicon row, a template fix, a client change, a framework decision) is a new tag, and a new tag means every report is rebuilt from scratch under it. There is no partial patch, no editing of a published file, and no mixing of tags within one publication set. The manifest records the tag per report, and the rollup refuses to mark a publication set as complete while two tags are present.

Rule 9, dev until the human inputs exist. The runner will not build in release mode unless the translator's values and the owner's signed D69 are present in the framework it hashes. Dev-mode reports can be built, checked and hosted for internal review and for the pilot, but they carry the review marker and cannot be marked as published in the manifest.

Rule 10, independent reproduction. Five per cent of the set, chosen at random after the full run, is rebuilt from the same tag and the same canonical dataset on a second, separately provisioned machine, and every output file is compared byte for byte, allowing only for the build timestamp fields in the identity. Any other difference stops publication of the whole set until it is explained.

Rule 11, the workbook is not touched by code. This rule from the prototype rounds is restated here because it is the one most likely to be tempted at scale: a refusal caused by a workbook gap is fixed in the workbook by its owner and recorded in the compliance record, never in code, and the affected reports are rebuilt under the tag that includes the corrected workbook.

---

## 7. Local authority and regional reports

The LA and regional reports use the same pipeline, the same template family and the same gate packs, with a different profile in the manifest row. The profile supplies the identifier type (LA or region), the filter applied by the canonical loader, the set of scopes offered (an LA report's scopes are its schools' aggregate views rather than year groups within a single school), and two design decisions that Sport Wales must make before these reports are specified in detail.

The first decision is whether an LA report shows a breakdown by school. If it does, the report identifies individual schools and their figures side by side, which raises the question of whether a school should be able to see its neighbours' results; if it does not, the LA report is a larger version of a school report with the LA's aggregate as its whole-scope view. The two are different reports and the profile must say which.

The second decision is the suppression threshold: the minimum count below which a cell is not shown. The prototype follows whatever the framework workbook specifies for a single school; an LA breakdown by school multiplies the number of small cells, and the threshold and its rule (for example whether a suppressed cell also suppresses its complement so that it cannot be recovered by subtraction) must be stated in the workbook so that the pipeline implements it rather than interprets it.

The regional reports sit above the LA reports and inherit the same two decisions. The number of LA reports is fixed by the twenty-two Welsh local authorities; the number of regional reports depends on the regional grouping Sport Wales uses and is recorded in the manifest when that is confirmed.

Timing for these reports has not been measured. An LA report's state count depends on the profile (more schools means more scopes, but there are no year-group scopes to multiply against), so the per-report time may be higher or lower than a school's. The plan measures it in the LA pilot (section 9, phase 5) on two local authorities before the full LA run is scheduled, and does not quote a figure before then.

---

## 8. Checking at scale

The prototype was checked by reading it. A thousand reports cannot be, and the checking plan is layered so that the machine-checkable properties are checked on every report without exception, and human attention is spent on a stratified sample where it adds something a gate cannot.

Layer one is the per-build assurance, unchanged from the prototype and applied to every report by rule 5: selftest, in-build gate run, two stock reruns, jsdom regression and browser-gate port, bundle and evidence written, identity stamped. This layer is what makes a report eligible to exist.

Layer two is the rollup. After the run, the manifest is queried for every report's gate headline, path count, pending and disputed lists, and identity hashes. The expected values for a release-mode run are known (they are the values the pilot establishes for the tag, and for the V4.9 tag in dev mode they are 71/72, 71/75 and 17/18 with STK-caption-case disputed); every report must show exactly those values with exactly the same runner sha256, framework sha256 and manifest hash. Any report that differs in any field is listed, and the set is not publishable until every listed report is either rebuilt clean or the difference is explained and recorded. The rollup is a script over the manifest and it produces one page that says whether the set is uniform.

Layer three is reconciliation against the canonical dataset. For every report, the headline counts (pupils included in the whole-scope view, and the per-year-group and per-gender counts in the state index) are extracted from the payload and compared to counts computed independently with a plain dataframe query over the canonical file. Every LA report's whole-scope count must equal the sum of its schools' counts, and the sum of all LA counts must equal the national total recorded when the canonical file was made. This layer catches a wrong filter, a duplicated school or a dropped row, none of which a language gate would see.

Layer four is the byte-compare rebuild of rule 10, five per cent of the set on a second machine.

Layer five is the browser gate in real Chromium. The stock `02_browser_gate_provenance.py` harness, which could only be run under jsdom in the build environment, is run on the operations machine over a sample of reports at sixty states each, with the fixture toggle, exactly as the bundle's `RUN.md` describes for the prototype. The sample is stratified by school size band and by local authority so that small and large payloads and both ends of the country are covered.

Layer six is the linguist's sample. The linguist sheet's method (the 150-sentence proofreading sample, the fixtures, the tab 9 checks) is applied to a stratified sample of reports rather than to one. The stratification should cover school size (because small schools exercise the singular and low-count noun phrases that large schools never do), language medium of the school, and local authority, and it should deliberately include any report whose build raised and cleared a refusal, because those are the reports that exercised a path the prototype did not. The English is checked in the same sample against the source data for the reports concerned; the English narrative itself is locked by tag and does not need re-proofreading, but its numbers do need spot-checking against the dataframe.

Layer seven is hosting verification. After publication, a script walks the manifest, fetches every file of every report from its public URL, compares the bytes against the recorded sha256, checks the response headers (compression, cache policy, noindex), confirms that a request for a directory listing and for a wrong token both return 404, and records the result and time in the manifest. This is run at publication and again on a schedule for the life of the publication set.

---

## 9. Sequence and milestones

The order below is the order the work should happen in. Each phase has an exit condition; the next phase does not start until it is met.

Phase 0, decisions. Sport Wales settles: the access-control model (section 3.3); the LA and regional design, meaning the school breakdown question and the suppression threshold and rule, recorded in the workbook (section 7); the hosting platform and domain; and custody of the token secret. Exit: each decision is written into the compliance record and, where it affects the pipeline, into the workbook.

Phase 1, close the prototype. The "few final tweaks" identified on the rebuilt V4.9 are applied as a V4.10 round under the established process (reproduce, change, gate, ship, compliance record). In parallel the human lane completes: the translator's values, the owner's D69, Q17, PR-15 and EN-05 decisions, and the linguist's sheet v6. Exit: a release-mode build of the prototype passes every gate that is not disputed, with the dispute recorded, and the compliance record is current. This is the first tag that could be used for production.

Phase 2, production code. Four contained changes to the pipeline, each with its own tests: the write stage emits the core page and state chunks and a chunk verifier proves that the chunks concatenated are identical to the in-memory states the gates examined, while the monolithic package is still written into the build's assurance directory (not served) so that the stock gate runner, which reads one file, continues to run unmodified; the client's state lookup becomes fetch-and-cache with the first state inlined; the canonical loader replaces the workbook reader and filters by identifier from the manifest row; and the build runner enforces the eleven rules of section 6 and writes the manifest. The rollup, reconciliation and hosting-verification scripts of section 8 are written at the same time. Exit: the prototype school builds through the production runner, produces a chunked report whose gate results equal the monolithic build's, and the jsdom regression passes against the chunked client.

Phase 3, build farm. A cloud virtual machine with eight to sixteen cores, memory sized after measuring one build's peak (that figure is not yet known and is taken in the first pilot build), and a few hundred gigabytes of disk, is provisioned with the frozen release and the canonical dataset and nothing else. Exit: the fresh-start rules pass their own tests on the farm (a deliberately modified file is refused; a non-empty working directory is refused; a path outside the allowlist is refused).

Phase 4, school pilot. Twenty schools, chosen to span size bands and local authorities, are built on the farm, published to the real hosting path under the real link scheme, and put through every layer of section 8 including the linguist's sample and the Chromium browser gate. The per-school build time and peak memory are measured here and replace the estimates in section 10. Exit: all twenty are uniform in the rollup, reconcile to the canonical file, verify on the host, and the linguist's sample raises nothing that requires a tag change; or, if it does, the tag is cut, the twenty are rebuilt, and the exit is re-tested.

Phase 5, LA pilot. Two local authorities are built under the agreed profile, published and checked in the same way, and their build times measured. Exit: as phase 4.

Phase 6, full run. Every school, then every LA, then every region, is built under the single production tag with the concurrency the phase 4 measurements support. Refusals are collected, fixed at source, recorded, and the affected reports rebuilt; if a fix requires a tag change, the whole set is rebuilt under the new tag (rule 8). Exit: the rollup shows one tag and uniform results across the entire set.

Phase 7, verification of the set. Layers three, four, five and six of section 8 run over the full set. Exit: reconciliation is exact, the five per cent rebuild is byte-identical, the browser gate and linguist samples are clean or their findings are resolved by a new tag and a full rebuild.

Phase 8, publication. The manifest export is imported into the CMS, the reports are made reachable, layer seven runs, and the compliance record receives the publication entry naming the tag, the canonical dataset hash, the manifest hash and the date. Exit: every report the CMS links to verifies against its recorded hashes.

Phase 9, after publication. Layer seven runs on a schedule. Any change, from a corrected lexicon row to a rewording, follows rule 8: new tag, full regeneration, full verification, republication. The previous set is retained, unlinked, with its manifest, for the record. The token secret's custody and rotation procedure is tested once, on a non-production path, so that it is known to work before it is ever needed.

---

## 10. Timing and resources

The measured per-school time on the two-core cloud sandbox for the prototype school, running the complete V4.9 process, is between seven and eight minutes: state generation about two minutes, assembly about half a minute, the in-build gates about a minute and a half, the write stage about a quarter of a minute, the HTML build about half a minute, the two stock gate reruns about two minutes together, and the jsdom runs about a minute. These are single-run measurements for a 366-pupil school and will differ with school size, most of all in state generation, whose cost scales with the number of pupils and cohorts.

Run sequentially at that rate, a thousand schools is on the order of 115 to 130 hours (seven minutes over 990 schools is 6,930 minutes, or about 115.5 hours; eight minutes is about 132 hours), which is five to six days of unattended running, and the outputs alone at roughly 179 MB per school would be on the order of 180 GB before compression, far more than the sandbox's 29 GB of free disk. The working PC's local sandbox, with about 3 GB of memory and 1.6 GB free against a 600 MB per-build working set, cannot run even one build reliably. Neither machine is the answer, and the plan does not propose to use either for the production run.

On an eight-core virtual machine running several builds concurrently, the estimate is twelve to eighteen hours for the school set, and roughly half that on sixteen cores, subject to memory: if one build's peak memory is high, concurrency is bounded by memory rather than cores, which is why the peak is measured in the pilot before the farm's size is finalised. Disk on the farm should be a few hundred gigabytes to hold the outputs, the assurance directories and the five per cent rebuilds with margin. These are estimates derived from the two-core measurement and should be replaced by the phase 4 measurements in the manifest before the full run is scheduled.

The elapsed time for the programme as a whole is dominated not by the build but by the human lane in phase 1 and the decisions in phase 0. The pipeline work of phase 2 is bounded and well understood; the pilot phases are each a matter of days including the linguist's review; the full run and its verification are a matter of days on the farm. The dependency that cannot be shortened by machines is the translator's values and the owner's signed decisions.

---

## 11. What stays with humans

The following cannot be produced by the pipeline and are required before a release-mode production build exists. The translator supplies the 356 static values (342 page strings and the fourteen attribute strings, ui217 to ui230) through the handoff workbook. The report owner supplies the signed D69 value and the decisions on Q17, PR-15 and EN-05; EN-05 ("21th") remains the owner's and is not to be touched in code. The linguist supplies sheet v6 covering PR-19 and FT-11, the fixtures, the 150-sentence proofreading sample and tab 9, and later applies the same method to the stratified sample in section 8. Operations run the device, assistive-technology and real-Chromium checks that the build environment could not. Sport Wales makes the four decisions of phase 0 and holds the token secret.

The eight items raised against gate pack v7 in the V4.9 register remain open with the pack owners; the disputed STK-caption-case emulation and the 72/75 denominators in particular determine the exact "uniform" values the rollup expects, and any change to the pack is a new vendored version, a new tag, and a full regeneration like any other change.

---

## 12. Summary of what is fixed and what is open

Fixed by this plan: fully pre-generated reports from a frozen tag; one independent build per report from a canonical dataset; a core page plus lazily fetched state chunks; static hosting behind a CDN; per-report keyed-hash tokens under a dedicated reports domain; a manifest as the single register; eleven build rules enforced by the runner; seven layers of checking with every machine-checkable property checked on every report; a pilot of twenty schools and two local authorities on the real serving path before the full run; and the principle that every change is a new tag and a complete regeneration.

Open, and named as such: the access-control model; the LA and regional design decisions and suppression rule; the hosting platform and domain; token secret custody; the per-build peak memory and the LA build time, both measured in the pilots; the human-lane inputs that gate release mode; and the pack owners' response to the V4.9 register.
