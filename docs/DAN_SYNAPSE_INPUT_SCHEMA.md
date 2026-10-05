# DAN synapse input/schema closure — 2026-10-05

MoLab live-state preflight: no running cell; private HF identity TryDotAtwo verified.
Input listing source and results archived:
- Inventory result HF b6b5cbc2c9404e629cc424770ac261d65b3bb745; manifest 46d040102d00be88c1e48e461ec1f7622421e68340a53a6d1c7790f84955b8a7.
- Raw listings HF f07b35802c72b79e687fac9eef4599dc6e8cf1d9; manifest 5d0a1b639ce6f64bdf6e548781dc1cbbf7059c409e4a18e7bd3025f9ba792311.
- Synapses listing first 1000 objects is INCOMPLETE (nextPageToken present). Flat-connectome listing is complete.
- Full syn-points Feather: 13061489098 bytes, GCS generation 1780494991007477.
- Full syn-partners Feather: 6777179098 bytes, generation 1780494942562468.

Generation-pinned small CSV and full ingestion arguments fetched, size and MD5 verified, then archived BEFORE schema inspection:
HF input commit 3e8612e98ffe27a98d9a68f0ed968d0b4446d4e0; manifest 34b305702eb8d0a8f8be831401ec17770558aaaeb68f472bb39f87f7bf3a5044.
Sample Neuprint_Synapses/000001.csv generation 1780895402724677.
Ingestion arguments generation 1780895255342856.
Schema report HF b75d42605143f87d6937a0a0f551910a9c4ba2ae; manifest 4efab0cadef7e4e18033612a5720871ed7182c900ec16d34961370ace8be0e6a.

Sample has 43 rows and columns bodyId:long, type:string, confidence:float, compartment:string, location:point{srid:9157}, ntDopamineProb:float and other transmitter probabilities, ROI booleans. It pertains to AL-VA2(L), NOT the target DAN population. No release-site or gamma1 evidence claimed from this sample.

Next: derive complete PPL101/PPL102 presynapse selection with pinned input closure and archive completed partitions before geometry; avoid arbitrary CSV numbers and incomplete listing. Plasticity/learning remain unadmitted. All computation/data stayed in MoLab.
