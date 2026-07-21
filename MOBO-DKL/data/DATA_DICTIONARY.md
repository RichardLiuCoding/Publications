# PZTO-(111) compact data dictionary

## Provenance

The release combines two MOBO-DKL experiments on separately pre-poled PZTO-(111) regions. Area 1 contains 215 measurements acquired on 2026-06-14. Area 2 contains 212 measurements acquired on 2026-06-12. Seed events occur first in each area's measurement order.

Raw Igor Binary Wave files were reduced to aligned 32 x 32 arrays. The compact files retain the numerical values required to recompute the switched-area masks and reproduce the manuscript's Pareto, descriptor and VAE post-analyses. They omit instrument headers and redundant raw channels.

Local field of view: 500 nm x 500 nm. Pixel size: 15.625 nm. Pixel area: 0.000244140625 um^2.

## `PZTO111_MOBO_DKL_maps_v1.npz`

All event-level arrays use the order Area 1 followed by Area 2 and contain 427 entries.

| Key | Shape | Unit / definition |
|---|---:|---|
| `phase_before_deg`, `phase_after_deg` | `(427, 32, 32)` | Raw lateral-PFM phase in degrees |
| `amplitude_before`, `amplitude_after` | `(427, 32, 32)` | Raw lateral-PFM amplitude channel in instrument units |
| `voltage_V` | `(427,)` | Signed out-of-plane pulse voltage |
| `dwell_s` | `(427,)` | Pulse dwell time in seconds |
| `coordinates_px` | `(427, 2)` | Selected position on the 128 x 128 global candidate map |
| `area_id` | `(427,)` | 1 for Area 1, 2 for Area 2 |
| `measurement_order` | `(427,)` | Zero-based order within each area |
| `is_seed` | `(427,)` | Seed-measurement flag |
| `switched_area_full_px` | `(427,)` | Whole-frame switched-pixel count |
| `switched_area_localized_px` | `(427,)` | Center-localized switched-pixel count used for the primary post-analysis |
| `switch_mask_full_packed` | `(427, 128)` | `np.packbits` representation of each 32 x 32 whole-frame mask |
| `switch_mask_localized_packed` | `(427, 128)` | Packed center-localized masks |
| `phase_flip_corrected` | `(427,)` | Whether the 180-degree global phase-offset guard was applied |
| `global_map_area1`, `global_map_area2` | `(128, 128)` | Global signed lateral-PFM structural maps used to define candidates |
| `n_seed_by_area` | `(2,)` | `[15, 12]` for Area 1 and Area 2 |
| `pixel_size_nm`, `um2_per_pixel` | scalar | Spatial conversion constants |

The packed masks can be recovered with:

```python
mask = np.unpackbits(data["switch_mask_localized_packed"], axis=1)
mask = mask[:, :1024].reshape(-1, 32, 32).astype(bool)
```

## Switched-area definition

1. Compute `abs(wrap(phase_after - phase_before))` over 0-180 degrees.
2. If the median peripheral change is above 120 degrees, subtract 180 degrees from the after-phase map and recompute.
3. A pixel is switched when phase change is above 45 degrees and `abs(amplitude_after)` exceeds 0.5 times the frame median.
4. Label four-connected switched components.
5. Retain components touching a radius-4-pixel central disk. If none touch it, retain the nearest component when its centroid lies within eight pixels of the center.

## `PZTO111_MOBO_DKL_analysis_v1.npz`

| Key | Shape | Definition |
|---|---:|---|
| `descriptor_names` | `(15,)` | Names of physically interpretable before-pulse descriptors |
| `descriptor_matrix` | `(427, 15)` | Descriptor values, Area 1 followed by Area 2 |
| `vae_latent_6d` | `(427, 6)` | Unsupervised VAE latent means |
| `vae_latent_pca_2d` | `(427, 2)` | Leading PCA scores of standardized latent means |
| `vae_structure_axis` | `(427,)` | Oriented latent structure coordinate used in post-analysis |
| `vae_input_normalized` | `(427, 32, 32)` | Globally normalized signed lateral-piezoresponse inputs in `[0,1]` |
| `vae_reconstruction` | `(427, 32, 32)` | VAE reconstructions |
| `vae_decoded_grid` | `(7, 7, 32, 32)` | Decoded two-dimensional latent grid |
| `vae_grid_axis_1`, `vae_grid_axis_2` | `(7,)` | Coordinates of the decoded grid |

The VAE was trained on all 427 before-pulse maps without voltage, dwell, switched area or efficiency labels. The full schedule used a six-dimensional latent, binary cross-entropy, Adam at 0.001, batch size 64, 500 epochs and a KL weight ramp to 0.4 over the first 120 epochs.

## `PZTO111_MOBO_DKL_events_v1.csv.gz`

The table contains one row per event. It includes acquisition metadata, voltage, dwell, pulse dose, both area definitions, write-dose efficiency, all 15 descriptors, six VAE latent means, the two displayed latent PCs, the structure axis and in-plane order `S = 2 * mean(abs(I - 0.5))`.

`|V|t` is a pulse-dose proxy. It is not electrical energy because current was not measured.
