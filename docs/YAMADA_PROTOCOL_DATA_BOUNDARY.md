# Yamada 2024 protocol and data boundary

The complete 27-page NSF PAR PDF (DOI 10.1113/JP285745) was acquired, verified and archived in MoLab before extraction. Source PDF HF revision: 085605e4c53704e620f382832364d9a57e1800f2, manifest 2f4c3cac0f9b920f8c39ff517f9ba2b30056a0bd38bae5e3a25afefac1f0ebe7. Extraction source revision e0b880bc4cf22393033cbf61296fa360d90b1835; pinned pypdf 6.1.1 dependency revision 230cbea0a34e08b654ef2703ef72a4d227a618ca. Extracted pages and report revision 5b7ca66fd588c37a322a54d9f32c4a75315b8d4f, manifest aa9c55b7f3460324b13db9fb19cca36fe2540b5d44da96e5732e3a2c0ff43c35. All receipts remotely verified. No local PDF/data download or computation.

## Measurement operator (PDF page 5)

A single 1-ms reference stimulus starts each minute's set. Ten seconds later, four paired stimuli are delivered every 10 seconds, each pair separated by 400 ms. The reference waveform is subtracted from the average of the four paired responses before determining the second EPSC amplitude. PPR is this second amplitude divided by the first. Baseline is recorded for at least three minutes. The current diagnostic's single pair and analytical tail subtraction do not reproduce this observation operator.

## Induction and intervention boundaries

Page 5: focal pressure injection uses 1-second pulses every 2 seconds for one minute; paired KC photostimulation uses 1-ms pulses at 2 Hz for one minute, starting 0.3 seconds before the first injection. Recording resumes 2.5 minutes after injection ends. Bath-drug equilibration takes two minutes, followed by three minutes of drug-only EPSC measurements before pairing.

Pages 6–7: sparse gamma KC activation labels approximately 3–7% of cells. Lower Ca/Mg decreases A1 and increases PPR; higher Ca/Mg increases A1 and decreases PPR. Partial postsynaptic nicotinic block lowers A1 without a detected PPR change. These require separate release dynamics and postsynaptic efficacy; assigning two names to a scalar gain is insufficient.

Page 19 (Figure 8) also supplies alpha/beta KC physiology: dopamine/KC pairing produces an early depression and PPR increase that do not persist at the middle/late comparisons. Gamma and alpha/beta contacts must therefore preserve separate duration constraints. This is an additional primary physiological observation, not permission to assign an arbitrary common plasticity rule to MaleCNS contacts.

## Quantitative availability and next implementation

Page 27 states that original data are available upon reasonable request to the corresponding author. Listed supporting information is peer review history. No openly downloadable preparation-level EPSC dataset was identified by this PDF extraction; no numerical release probability, recovery time, or absolute baseline EPSC has been calibrated. Figure digitization would be a separate, explicitly approximate evidence route.

Next: implement the exact minute-level observation schedule and independent reference-subtraction operator before screening an explicitly separate release/efficacy model. Software agreement and qualitative intervention direction will remain separate from quantitative biological admission. Preserve alpha/beta transient and gamma persistent observations as separate constraints. Learning remains disabled and all whole-project acceptance gates remain open.
