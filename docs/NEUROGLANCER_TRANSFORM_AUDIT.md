# Official MaleCNS layer coordinate audit

Executed in MoLab foreground cell `neuroglancer_transform_audit`, 2026-10-05. Dataset configuration bytes were rechecked against the already archived SHA-256 before interpretation. Source and report were published and verified before advancing.

The official `male-cns:v1.0.json` state sets x/y/z dimensions to 8e-9 meters and includes `brain-neuropil-subcompartments` from `precomputed://gs://flyem-male-cns/rois/malecns-subcompartments-v3`. Neither that layer nor its source specifies an additional transform. The original segmentation, presynaptic and postsynaptic layers share this state. The micro-CT layer separately specifies a transform and explicitly warns that it is unaligned; it must not be substituted for this registration evidence.

Combined with the atlas metadata, this supports an explicit candidate mapping from 8-nm source voxel coordinates to the 256-nm v3 grid, subject to verifying the contact coordinate convention. It does not establish each synapse's compartment or anatomical boundary uncertainty. The remaining task is source-pinned sparse volume sampling of contact coordinates and independent checks around boundaries. No contact mask or learning was enabled.

Verified private HF dataset `TryDotAtwo/faithful-fly-artifacts`: source commit `2aa3da88938be286ecf7c05dab09be99b1282eb2`, manifest `e7c08d3ac565324a4acd35781eeda1bdcc9c4e4ac7d12478720ddc7228838ffc`; final report commit `11f6b1af10975783a204af1ced093314615be40f`, manifest `b7a28fecd7ed040e84030acbcddf89e106fb5cbe5d57d95649383b597d65b66b`.

The first attempted cell was rejected by marimo before execution because its SOURCE global conflicted with the previous cell. Renaming the global resolved the compile-time conflict; validation was not bypassed.
