# Visual feedback causality gate

This is an intervention on the present hybrid model, not a reproduction of a
genetic manipulation in a living fly. All ordinary neurons still use diagnostic
LIF physiology. R7/R8, electrical synapses and several measured physiological
constraints are absent. Passing this gate cannot authorize landing training.

Primary reference: [Pang et al., Current Biology 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC11769683/),
DOI 10.1016/j.cub.2024.11.064. Their ort-neuron TNT experiment blocks release
from photoreceptor-postsynaptic neurons; it is not the same intervention as
zeroing all non-photoreceptor inputs to our two modeled population groups.
Their L2 light response loses its second phase under that intervention, while
the first phase grows and peaks later. Matching these effects requires both
anatomical/genetic scope alignment and an observation model; our initial
intervention establishes only a model-level necessity test.

The intervention blocks chemical input from non-photoreceptors to modeled R1R6
and L1/L2 populations by setting designated transmission gains to zero before
state creation. It retains anatomical arrays, neurons, intrinsic dynamics,
R1R6-to-L1L2, R1R6-to-R1R6 and the remaining CNS pathways.

Affected rows: L1/L2-to-R1R6 3517; ordinary-to-L1/L2 71870;
ordinary-to-R1R6 9517; L1/L2-to-L1/L2 1995. These are retained edge rows,
not counts of distinct synapses.

## Verified engineering checks

Two 100 ms native full-graph runs completed in Molab. The intact mode matched
all six historical output files byte-for-byte. In the blocked mode all sampled
ordinary-to-L1/L2 conductances/currents, ordinary-to-R1R6 currents and L1/L2-to-L1/L2
currents were exactly zero. Total receptor feedback equaled retained R1R6-to-R1R6
current exactly; that retained current was nonzero. This check uses 1 ms recordings
of the final 0.1 ms interval, not observations of every internal integration step.

Source, binary, preregistered scope, outputs and report are archived privately:
commit `b501b6f0cc2a331ea7a6d9c0cbfad12a6bbc3adb`, manifest
`manifests/82dd0f87264a221c3cbe31e1efd0cff16052728d1d38d2bd20fa5f2c728feecf.json`.
18 paths / 16 unique objects; remote object identities verified. A separate
fresh-directory roundtrip has not yet been performed for this archive.

## Full flash protocol

For intact and blocked models run separate gray/light/dark conditions with the
same photon seed 19503: 500 ms gray, 20 ms pulse, 500 ms gray; dt 0.1 ms.
Relative radiance is gray 0.5, light 1, dark 0. Use each model's own gray control.
Compare initial and opposite-sign second response phases in the same identified
L1/L2 populations. Archive every completed condition before starting another.

Hypothesis: non-photoreceptor chemical feedback contributes to the second phase.
If a biphasic response remains after blockade, that feedback is not necessary
for biphasic behavior in this parameterization. That result must not be presented
as proof of the published biological mechanism. One seed, short adaptation and
uncalibrated photon scale limit interpretation even if a feedback effect exists.

The intact gray control completed 10200 steps in 323.7 s and recorded 5378
spikes. All output channels were finite. Its ten files were recovered from HF
with byte counts and SHA256 checks: commit
`d9157677ab17ef926d61c1ac8cc707035a2e02b4`, manifest
`manifests/0624cbe92e1087e292346bee1e0f4feddb3bca7110ee1b8154fa54ed2d5039c6.json`.
The control alone provides no flash response or causal comparison.

The intact light condition also completed 10200 steps (326.3 s, 5377 spikes).
Its ten files are archived at commit
`48eb547dbc6b3b7482df74fea91184817a2988b7`, manifest
`manifests/69230b3e75615618a92f33103cca6a03b726c6a27960a94b5a338e4ccf24b421.json`.
All L1/L2 traces match the gray control exactly before the flash. After
subtraction, 416 exposed L1 cells have a mean initial negative voltage peak
of 1.25905 mV at 36 ms and an opposite extremum of +0.29606 mV at 101–500 ms.
The corresponding L2 values are 1.28762 mV, 36 ms and +0.30256 mV.
These are model voltage diagnostics. The one-file paired diagnostic is archived
at commit `c721af533cbeffd80297f1c814cd366469bdc6ac`, manifest
`manifests/f1e832fd1f3a9d50e1a0d31411f5aaa628ef8be38ad18fa7b6c093360e04bdc7.json`.

The blocked gray control completed 10200 steps in 328.1 s (5377 spikes).
All channels were finite; sampled currents in the targeted blocked pathways
were zero. Its ten files are archived at commit
`c77ba0bbf29730ae19ac93fa69b368e810621735`, manifest
`manifests/b916abef7195a94525c2764f1e79a0e743bde60c7d3f1e3120cd7eb185089e8b.json`.

The blocked light condition completed 10200 steps in 326.6 s (5376 spikes),
with zero sampled currents in every targeted channel. Its ten files are
archived at commit `58c6fa7dedbd76c470ade5d5dcc019de8c87815f`, manifest
`manifests/668b674b97a93156a749fe2e5474f99054d8a63ea5fa68c374c5d8eb3e4a6271.json`.
Preflash traces exactly match each mode's separate gray control.

After matched-gray subtraction, the blocked model remains biphasic for light:
L1 initial peak −1.25873 mV at 36 ms and late opposite maximum +0.29689 mV;
L2 −1.28733 mV at 36 ms and +0.30388 mV. Relative to the intact model, the
maximum absolute difference of population means across the 520 ms analysis
window is only 0.00369 mV for L1 and 0.00436 mV for L2. This **rejects the
necessity of the blocked chemical paths for the second phase in the current
parameterization**. It does not identify the mechanism: intrinsic state and
retained R1R6 pathways can both contribute, and this intervention is not the
same as the published TNT manipulation. The model does not pass the biological
mechanism gate. Comparison report archived at commit
`45795a4a01134bec1e26a7a53666c3040e3b03d5`, manifest
`manifests/3c8df6c3ec5af1af99f36983d43bf595e9ea33638eff51eb51205c9c834de307.json`.

The intact dark run (325.1 s, 5376 spikes) and blocked dark run (325.6 s,
5377 spikes) completed. Their ten-file archives are respectively:

- `e7f4dbb35f570184101a56f630b0385735c18efa`, manifest
  `manifests/d4fc4f7ea6d3aa8446dc5e02bd1e1109723d7f9ebf92ddf0a1b17072c333ea01.json`;
- `f3c486596f103aaab07d6fdf0f72086ad7437c76`, manifest
  `manifests/0926ab6ce611649e8107906f23bda751f8071e680617162e9e2354c9ece755fd.json`.

The six-condition analysis validates all six pinned HF manifests against local
bytes and SHA256, uses matched gray subtraction, and verifies exact preflash
traces within each mode. The exposed population contains 416 L1 and 416 L2
cells. The remaining recorded model responses are:

| Condition | Cell | Initial signed peak, mV | Peak time, ms | Opposite phase, mV | Max absolute intact/blocked difference, mV |
|---|---|---:|---:|---:|---:|
| Dark intact | L1 | +3.50854 | 38 | −0.65067 | 0.00724 |
| Dark blocked | L1 | +3.51322 | 38 | −0.65101 | 0.00724 |
| Dark intact | L2 | +3.62410 | 38 | −0.66800 | 0.00712 |
| Dark blocked | L2 | +3.62927 | 38 | −0.66846 | 0.00712 |

The light comparisons above differ by at most 0.00369 mV (L1) and
0.00436 mV (L2). Both second phases persist with similar timing and size
after the tested blockade. Thus the targeted non-photoreceptor chemical
inputs are **not necessary** for the second phase in the present parameterization.
The cause of the second phase remains unidentified: the model retains
photoreceptor interactions and intrinsic dynamics, and the intervention does
not match Pang et al.'s genetics. One seed and an uncalibrated voltage-to-ASAP2f
observation prevent a biological pass.

The full analysis source, mean voltage traces, report and four-panel plot are
archived at commit `820f4f9e132e0c8aa26e23f6de28277102e74eba`, manifest
`manifests/11c2c4af5f3435a7ff314d711107cab013ba579501f65cb2d3d808eeb11091ff.json`.

## Isolating all modeled visual feedback

The next preregistered intervention also disables the retained R1R6-to-R1R6
graded route. It uses `argv20=off` and
`argv21=nonpr-visual-inputs-blocked` in the same native executable, preserving
direct R1R6-to-L1/L2 transfer, phototransduction and intrinsic L1/L2 dynamics.
The explicit hypothesis and parameters were archived before simulation:
commit `29833abbaa976a95383fa4f1104327971201921e`, manifest
`manifests/4ddfdb78cd8c8ac8b3a678e5746ca39b009b51795480966fb203fd1193545e7d.json`.

The isolated gray control completed 10200 steps (341.8 s, 5376 spikes) with
all sampled feedback and recurrent currents exactly zero; its ten files are at
commit `66d87bbf5d8f42c2e1fb6357e8d1210d00559554`, manifest
`manifests/22abe6156d8a474bcfe6d2868699aff5fe5569dd84f7a38c223ac83a25785201.json`.
The isolated light condition completed 10200 steps (333.3 s, 5377 spikes),
with the same zero-current checks. Its ten files are at commit
`f9de4e30037a6f25b90802dfb9deb67d5fdfe8b9`, manifest
`manifests/ac17f5ab25d57be67dc46f68cbdde3065fe931e729d6858129d33b674fd37689.json`.

After its own gray subtraction, the isolated light response is still biphasic:
L1 −1.25803 mV at 36 ms then +0.29735 mV, L2 −1.28655 mV at 36 ms then
+0.30446 mV. Relative to the prior blocked model (which retained R1R6-to-R1R6),
the maximum population-mean difference over the response is 0.00245 mV for
L1 and 0.00264 mV for L2. The conclusion is limited: the tested feedback is
unnecessary in this parameterization; the remaining source could be
phototransduction, the direct transfer law, or L1/L2 intrinsic dynamics.
The comparison report is archived at commit
`9a3bec9b0f218b996046c98f8b1f9306f02a7c2e`, manifest
`manifests/716bc86343a54d482bd998d1b76464a9983eb0d203fe3d0fa4948da68729778d.json`.

The isolated dark condition completed 10200 steps (330.1 s, 5377 spikes)
with the same zero-current checks. Its ten files are at commit
`f4a1470684be98873817ccb6267cbe35f0b139e9`, manifest
`manifests/8542f70dc9069c65d824fd9607095c8ea9d5a581ae988f7ddc214b3e6c0dca72.json`.
After matched-gray subtraction, the isolated L1 dark response peaks at
+3.51534 mV (38 ms) and reaches −0.65162 mV in the opposite phase; L2
peaks at +3.63159 mV (38 ms) then reaches −0.66901 mV. Compared with the
previous blocked model that retained R1R6-to-R1R6 feedback, the maximum
absolute difference of means is 0.00555 mV for L1 and 0.00567 mV for L2.
All six blocked/isolated condition manifests were rechecked against local
bytes and SHA256 before analysis. The source, report, means and plot are at
commit `62e26a6d5bd9f5b2df393ea0e8f8d27b6e5f92ab`, manifest
`manifests/b00ba2d1ff784b71530205c66bd491928461f80f81d65afc19ee59f42a942c9e.json`.
User-facing figure preview: commit `4be51c614b4ff1e46538c3db22a25e21d71cce2e`,
`previews/isolated_visual_feedback_v1.png`, verified SHA256
`48b79e4d219bb11bd67625a94132357ee42cbbca719f430968b5ed061f57cb47`.

This rejects the necessity of any currently modeled visual feedback for the
second phase in this parameterization. The graph still retains these routes;
the intervention only zeros their gains for diagnostic runs. The next
mechanism test must separately inspect photoreceptor output, the direct
R1R6-to-L1/L2 transfer law, and the L1/L2 intrinsic model. Tuning feedback
gains to make these curves match live fly data would not establish the true
mechanism. Biological validation and landing training remain gated.

## Recorded photoreceptor output

The 1 ms diagnostic voltage channel in the six completed recordings contains
1843 mapped R1R6 cells. With all modeled visual feedback disabled, the
light-minus-gray mean R1R6 response has an initial +8.59173 mV peak at 36 ms
and a later opposite 1.29126 mV extremum (ratio 0.1503). Dark-minus-gray
has an initial signed 19.62436 mV peak at 38 ms and a later opposite
3.19096 mV extremum (ratio 0.1626). Thus the photoreceptor voltage itself is
biphasic under the current, uncalibrated photon rates. This is stronger
localization than the L1/L2 feedback ablation: a postsynaptic-only mechanism
cannot explain the recorded R1R6 voltage phase.

Weighting the R1R6 traces by the retained contacts to 416 exposed L1 or L2
cells gives opposite-to-initial ratios of about 0.15 in light and 0.163 in
dark. The correlation between sign-inverted, contact-weighted R1R6 voltage
and the L1/L2 population mean is 0.978 for light and 0.987 for dark. These
correlations are diagnostic only: they do not isolate the direct synaptic
transfer current or establish its causal gain. The reports and exact analysis
sources are archived at commit `be756597117fd790031d792ddc941ee529f7a272`,
manifest `manifests/2bca1266deadfec702111afe78f97360d006b0a59467631a08d5d521d62c6b5f.json`.

[Pang et al. (2025)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11769683/)
describe photoreceptor impulse responses as monophasic and L1/L2 responses as
biphasic through recurrent feedback. The current model result differs
qualitatively, but our display-to-photon mapping is not calibrated to their
stimulus. We therefore mark the visual biological gate as failed for this
parameterization, not as a proof that the pinned phototransduction model is
wrong at every light level. A standalone photoreceptor flux sweep tests that
sensitivity before any parameter changes to the full graph.

## Photon-rate sensitivity of the standalone receptor model

Molab ran the pinned VisTrans model for 128 receptor cells with 30,000
microvilli each, seed 19503, at four input scales. Each episode used a 500 ms
gray prelude, a 20 ms light or dark pulse, and 500 ms gray recovery. Gray is
half the named maximum in photons/s. The first archived analysis had a coding
error: its gray control used **darkness** during the 20 ms pulse. Its
light/dark raw trajectories are valid, but its response ratios are invalid.
The corrected V2 reran all gray controls, checked exact equality with both
flash traces before the pulse, and archived the combined traces and report.

| Maximum photons/s | Light opposite/initial | Dark opposite/initial |
|---:|---:|---:|
| 1,000 | 0.0234 | 0.0180 |
| 10,000 | 0.0499 | 0.0117 |
| 100,000 | 0.1499 | 0.1666 |
| 1,000,000 | 0.4738 | 0.2748 |

Thus the extra phase varies substantially with photon scale and is already
present in the standalone receptor model at the currently assumed 100,000
photons/s. These are sensitivity results from one seed, not a calibration to
the source experiment or proof of agreement at dimmer levels. The corrected
raw traces, analysis and source were verified in the private HF archive at
commit `d4127b9dd8428e0734ecf7f99861a95f2ebc435d`, manifest
`manifests/dd4b470e95971affbab514062b09e8273effd8b14a06010b797392480abedc76.json`.
The invalid V1 report remains at commit
`9277edd43d1c2f978f2f5d43dbcda4ce5f2737d5` for auditability and must not
be used as a result. The next biological comparison needs a measured
display-to-photon mapping and matched response readout; choosing a convenient
scale from this table would not pass that gate.

## Author stimulus cross-check

The [Pang et al. author stimulus repository](https://github.com/ClandininLab/L1L2-recurrent-feedback)
was pinned at commit `7fa5829e37d566e02beaaa87efd6a0f1de4e48c0`.
Its `fullfield_6contrastA_LDflash20ms_Gray500ms.txt` specifies 20 ms flashes
at relative projector levels 0 and 1 and a 500 ms gray interleave at level
0.5. The accompanying MATLAB class applies these values as projector contrast.
The same pinned author commit also contains B and C variants with dark/light
levels 0.25/0.75 and 0.375/0.625 against the same 0.5 gray, each with
20-ms flashes and 500-ms gray. `tools/audit_pang_20ms_stimulus_family.py`
pins all three configuration files and the implementing MATLAB class in
`data/reference/pang_20ms_stimulus_family/`; parsed relative contrasts and
source SHA-256 values are in `reports/pang_20ms_stimulus_family.json`.
The A/B/C excursions from gray are ±0.5, ±0.25 and ±0.125. The missing
recording-level `stimcode` join prevents assigning a given author L1/L2
trace to one of these variants. Consequently, reproducing A alone does not
establish a matched stimulus for every published mean response.
The [published Pang methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC11769683/)
also report a blue LightCrafter 4500 projector with a 482/18-nm filter,
300-Hz refresh, 64 luminance levels and approximate radiance at 482 nm of
78 mW·sr⁻¹·m⁻². `tools/audit_pang_projector_radiance.py` pins the NCBI
BioC full text and converts that radiance at the center wavelength to
1.893×10^17 photons·s⁻¹·sr⁻¹·m⁻². A nominal 20-ms flash spans six
300-Hz projector frames. This is a source-emission dimensional check,
**not** photons absorbed by any R1–6 cell. The paper does not assign the
quoted approximate radiance to each recording or contrast level; the
recording-specific filters, PWM and stimulus code remain unavailable.
`reports/pang_projector_radiance.json` records this distinction.
The five exact author source files and a scope report were SHA-verified in the
private HF archive at commit `12e57489a9b5630006c6deb3d3ec54bd4dcaf74c`,
manifest `manifests/984418d0213ab218d4552f65caf219e24e8f0c99856aff95c6b3ed16d78fc716.json`.
This supports our **relative** stimulus values and timing; it does not supply
the photon absorption rate at a fly receptor or prove that every recording
used exactly this configuration. The [author Dryad dataset](https://datadryad.org/dataset/doi:10.5061/dryad.ngf1vhj4c)
documents recording-specific settings and states that all imaged flies were
female. Its small metadata spreadsheet returned HTTP 403 to Molab on
2026-09-23 and was not acquired. A 2026-09-24 retry of the public Dryad v3
record identified `L1L2_Metadata.xlsx` as file 3732249 (195431 bytes,
SHA-256 `0c6c428b1a297fb7c63b24a6f1a6e60516320ca6bde550614639d865dcdcfcea`),
but the unauthenticated file API returned HTTP 401, the direct file URL
returned HTTP 403, and clicking Download in the browser produced no local
file. The publicly displayed Dryad README says the workbook supplies each
recording's `seriesID`, fly ID, genotype, optical color and neutral-density
filters, PWM, projector LED current, field of view, and acquisition settings.
It gives LED current in mA as `1.8 * PWM + 140` (blank PWM 200). The analyzed
MAT files carry `roiDataMat` with `seriesID`, `flyID`, `genotype`, reconstructed
stimulus levels and transition times. The required next join is therefore
figure cohort -> MAT `seriesID` -> workbook optical settings, before any
absolute luminance or absorption-rate fit. These fields are documented, not
yet inspected for their per-recording values. Female physiology is a further transfer
limitation for the male MaleCNS specimen. A fit to these curves must account
for the projector spectrum and intensity, receptor absorption, recording
indicator kinetics, individual-flies hierarchy, and sex/specimen transfer.

## Dark-adapted intensity stress test

A separate [in-vivo photoreceptor study](https://www.babraham.ac.uk/sites/default/files/media/files/25673862.pdf)
reports typical R1-R6 resting voltage below −55 mV and roughly 40–60 mV
responses to a saturating 10 ms flash estimated to contain about 10^5 photons
at 20 ± 1 °C. The methods explicitly describe calibration to effectively
absorbed photons for a different, dissociated-cell preparation; they do not
establish that the quoted in-vivo flash count is an absorbed-photon count.
We tested the unchanged native VisTrans photoreceptor module
from dark adaptation using 64 cells, seed 19503, and four nominal 10 ms
photon doses. Equality of the model's input count with photons absorbed by
the in-vivo receptor, as well as temperature matching, is unproved.

| Model photons over 10 ms | Peak rise from preflash | Outcome |
|---:|---:|---|
| 100 | 38.85 mV | Full 1,010 ms episode completed |
| 1,000 | 66.78 mV | Full episode completed |
| 10,000 | 77.66 mV | Full episode completed |
| 100,000 | 88.09 mV before failure | Gate left [0,1] at sample 538 ms, 28 ms into recovery |

The nominal 10^5-photon case cannot be used as a matched biological check:
the simulation fails numerically, and its pre-failure peak exceeds the
paper's stated typical amplitude range. The broad photon-unit and physiology
uncertainties prevent attributing that difference to a specific parameter.
The failed original case and four-dose follow-up were retained; partial traces,
source, failure stage and report are verified in private HF at commit
`1874d5a7bccc6f9c24609cd6910dfd2a6b5fa33c`, manifest
`manifests/dc9a78389198ce5e30ad950d048d53bfb91aa33afea1e32e0239bf3527fe5f3a.json`.
This is a numerical reliability failure to diagnose, not a reason to clip
the gate or redefine success around the lower doses. The biological gate
remains failed.

A separate exact-gate integration diagnostic subsequently completed the high-
intensity episode without a gate violation, while the tenfold smaller Euler
step still failed. The high-dose voltage rise was 92.10 mV; biological
calibration and a voltage-solver convergence check remain open. See
`PHOTON_NUMERICS.md` for the equations, timing, and archived evidence. This
does not change the biological gate status.

Further diagnostics found that the author implementation holds the light
current constant while integrating the membrane over each 0.1 ms receptor
tick. An isolated variant recomputing the TRP driving force from the current
voltage at every membrane substep lowered the strong-flash rise to about
81.19 mV and kept all 64 test receptors below the 0 mV reversal potential
across three new seeds. See `PHOTON_NUMERICS.md`. This variant remains outside
the production model pending biological and CNS validation.

## Coupled-current full-CNS flash diagnostic (2026-09-23)

The isolated within-substep current-coupling candidate was linked into the
same native full-CNS bridge without changing the published MaleCNS graph.
Three independent 1,020 ms episodes used the same seed (19503): 500 ms gray,
20 ms light/gray/dark, then 500 ms gray, with 0.1 ms neural ticks. The gray,
light, and dark raw runs completed in 332.7, 334.2, and 331.1 seconds. Each
condition has a SHA-verified private HF receipt, respectively revisions
`a521eb047fb49fabc2dcd6baa22e36d5c3e87b90`,
`a563c421934a545982d8ac2b317d9e9f6d95de61`, and
`34f5e0f4df68f19e17e7b6f3f81a6a124b5b0d93`. Their manifests are
`manifests/a0b18756d48cca03fd008db5990bf8d86fff7f8ac17a4779ffdf23a150e54859.json`,
`manifests/5bd32ef01d07ae44789de6d5d6df8d24e12ffcb9178757c7b85ed2feb3a63559.json`,
and `manifests/3f78d2accfde258551ae351c5fdd7054cdfd103d48f8f3146c251b06660d55cc.json`.

Gray-subtracted voltage from the 1,843 mapped R1R6 cells retained a +8.599 mV
light peak at 36 ms and a −19.623 mV dark trough at 38 ms. In the 416 exposed
L1 and 416 exposed L2 cells, the light-minus-gray response instead stayed
between roughly −0.000007 and +0.000032 mV, while the dark-minus-gray peaks
were +1.596 and +1.622 mV at 40 ms. Preflash samples were byte-identical
between conditions. The analyzer source, report, and mean traces are archived
at revision `8e4f3e6d1dd28a875336156a04b72bebdbd6e09c`, manifest
`manifests/c0c43f5db6c426d70f4379cab0d6463e8b8f616b1c4d39f7be886b190a26a5cd.json`.

**Correction to the interpretation:** this is *not* a controlled old-versus-new
receptor comparison. The earlier `visual_feedback_ablation` executable used a
different 20-value visual profile and additional graded and event-conductance
routes; the new `explicit_capacitance_bridge_coupled` run used fixed parameters
and omitted those routes. The old profile's direct receptor threshold, slope
and per-contact cap were −70 mV, 0.0002 and 0.01; the new executable used
−80 mV, 0.00002 and 0.0008. Even its lamina membrane parameters differ.
At the preflash sample the all-target mean voltage was −46.532 mV in the old
intact gray run and −51.044 mV in the new gray run. Neither that difference
nor the missing light response can be attributed to the receptor coupling.

A static diagnostic of the **new bridge's direct synapse alone**, using
recorded receptor voltages and baseline target voltages, found identical
L1/L2 conductance for its gray and light states, but lower conductance for
dark. Thus the new bridge's own direct connection is saturated to additional
light at that sample; this does not diagnose the older profile or all times.
The correct next experiment links both receptor libraries into the same
`visual_feedback_ablation` source and uses the same profile, remaining routes,
inputs and graph. The current result still does not validate visual biology;
`biological_gate_passed` remains false.

## Matched configured-bridge correction

The controlled follow-up compiled the **same** `visual_feedback_ablation.cpp`
with the coupled-current receptor library and kept the previous profile,
remaining visual routes, graph, seed and exact input files. The original
source, executable and receptor library were rehashed against the old flash
specification before running. A 100 ms gray pilot had identical spiking
events and a lamina-output RMSE of 0.00159 mV, then gray/light/dark 1,020 ms
episodes completed in 330.6/331.0/328.8 seconds. The pilot is SHA-verified
at private HF revision `b6cf481550811e95a1b0fbdc60c03de761fac9bd`,
manifest `manifests/7d4bba2a734f802d66c5ef431658f4e349d7ff27b3ecf02ac81cd11594e5bf71.json`.
The full gray, light and dark cases are at revisions
`6ca906ab1e24860684b844bebbccb25170fa532a`,
`c0eedf105c1c5fd80537a7ff85e006d4cb23b0e7`, and
`f32b18c5f035f716730b0ac1efc3d9dd8914421d` with manifests
`manifests/74d636724d3441987637bcee3b48ead7e0374d576ecaf316d45ceb532a0be42f.json`,
`manifests/36d7040718542e721594259853b2168a3d49a91a55c8a805e5e4f1fdf8a8e569.json`,
and `manifests/895dd1c24e06aca4df5f2c0b66b9abc211c418b8ab05b23ae711ae257a473c81.json`.

With matched gray subtraction, the original versus corrected L1 light peaks
were −1.25905 versus −1.25779 mV (36 ms), L2 −1.28762 versus −1.28646 mV.
For dark, L1 peaks were +3.50854 versus +3.51006 mV (38 ms), L2 +3.62410
versus +3.62621 mV. Across the full post-flash mean traces, maximum absolute
old/new differences were 0.00582/0.00653 mV for light L1/L2 and
0.00726/0.00700 mV for dark. The mapped R1R6 population responses also
remained close: +8.59694 versus +8.59151 mV to light and −19.59251 versus
−19.59633 mV to dark. All three new conditions were checked against the HF
manifests before analysis; the report and traces are at revision
`0ebb7ec54ac632d46bf7bf85f95986f3b21e04f5`, manifest
`manifests/a451fa65e2aab77d8c79861987340af4ed10b017b65dca96dba9a2c6de598bde.json`.

Thus the earlier near-zero L1/L2 light response resulted from comparing
different bridge configurations, not from the within-substep receptor
correction in a controlled run. The matched result supports numerical
compatibility on this one-seed visual protocol. It does not establish
biological fidelity: the R1R6 response remains biphasic, photon calibration
and a matched physiological readout are missing, and the synaptic and membrane
parameters include engineering choices. `biological_gate_passed` remains false.
