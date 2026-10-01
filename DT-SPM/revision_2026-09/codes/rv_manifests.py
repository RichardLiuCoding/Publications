"""Write split manifests and SHA-256 manifests of all inputs and outputs (revision 2026-09)."""
import numpy as np, pandas as pd
from rv_benchmark import block_folds
from rv_common import OUT, REV, ROOT, file_sha256
from rv_tap300 import build_table

T = build_table()
man = pd.DataFrame(dict(condition=np.arange(T["N"]), speed_index=T["si"], drive_index=T["di"],
                        setpoint_index=T["spi"], gain_index=T["gi"], scan_speed=T["speed"], drive_nm=T["drive"],
                        setpoint=T["setpoint"], igain=T["igain"], block=T["group"],
                        submitted_test=T["is_test_submitted"].astype(int)))
for f, te in enumerate(block_folds(T["group"], 5)):
    man.loc[te, "fold_block5"] = f
man["fold_speed"] = T["si"]; man["fold_setpoint"] = np.array([0, 0, 1, 1, 2, 2, 3, 3])[T["spi"]]
(REV / "release_R1" / "splits").mkdir(parents=True, exist_ok=True)
man.to_csv(REV / "release_R1" / "splits" / "alscn_split_manifest.csv", index=False)
g = np.load(ROOT / "output" / "calibration_grating_v2_figures" / "figure_45_data_bundle.npz")
perm = np.random.default_rng(7).permutation(60)
gm = pd.DataFrame(dict(condition=np.arange(60), acquisition_order=np.arange(60), drive=g["drive_exp"],
                       setpoint=g["setpoint_exp"], igain=g["igain_exp"],
                       submitted_test=np.isin(np.arange(60), g["test_idx"]).astype(int),
                       chrono_test=(np.arange(60) >= 40).astype(int)))
for k in range(5):
    gm.loc[np.sort(perm[k::5]), "fold_cv5"] = k
gm.to_csv(REV / "release_R1" / "splits" / "grating_split_manifest.csv", index=False)
inputs = ["data/260507-300kHz-AlScN.npz", "data/Image0002.ibw", "output/Tap300_AlScN.npz",
          "data/250315/pickles/250315_Cali1_MOBO.pickle", "output/cali_fd.npz",
          "calibration_cache/dt_controller_fit/physics_guided_PI_grid_balanced_g3_rms.joblib",
          "calibration_cache/dt_controller_fit/data_driven_records_balanced_g3_rms.joblib",
          "calibration_cache/dt_controller_fit/data_driven_alignment_balanced_g3_rms.joblib",
          "calibration_cache/calibration_grating_v2/local_PI_fits_multi.joblib",
          "output/dt_controller_fit_figures/figure_45_expscan_data_bundle.npz",
          "output/calibration_grating_v2_figures/figure_45_data_bundle.npz",
          "output/descriptor_framework/pinn_step2_predictions.npz", "output/descriptor_framework_Tap300/pinn_step2_predictions.npz",
          "output/descriptor_framework/fd_vocab_v0_1.csv", "output/descriptor_framework_Tap300/fd_vocab_v0_1.csv",
          "output/descriptor_framework_Tap300/qsafety_ap.npz", "output/descriptor_framework_Tap300/step3b_corrected_Q.npz"]
with open(REV / "release_R1" / "MANIFEST_inputs.sha256", "w") as fh:
    for p in inputs:
        fh.write(f"{file_sha256(ROOT / p)}  {p}\n")
with open(REV / "release_R1" / "MANIFEST_outputs.sha256", "w") as fh:
    for p in sorted(list(OUT.glob("*.json")) + list(OUT.glob("*.npz")) + list(OUT.glob("*.csv")) +
                    list((OUT / "bundles").glob("*.npz")) + list((OUT / "bundles").glob("*.json")) +
                    list((REV / "figures").glob("*.png")) + list((REV / "figures").glob("*.pdf"))):
        fh.write(f"{file_sha256(p)}  {p.relative_to(REV)}\n")
print("manifests written")
