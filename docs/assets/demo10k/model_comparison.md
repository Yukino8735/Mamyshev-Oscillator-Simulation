| Version / saved experiment | Unique training designs | New test designs | Target | MAE | P95 absolute error | Within tolerance |
|---|---:|---:|---|---:|---:|---:|
| v42_T2_K64_A0001 | 1024 | 2048 | compressed_energy_nJ | 0.159472 nJ | 0.534899 nJ | 2048/2048 |
| v42_T2_K64_A0001 | 1024 | 2048 | compressed_duration_fs | 0.0335371 fs | 0.0967493 fs | 2048/2048 |
| v42_T2_K64_A0001 | 1024 | 2048 | compressed_peak_power_MW | 0.0032583 MW | 0.0116808 MW | 2048/2048 |
| demo_10k_v1 | 10000 | 2048 | compressed_energy_nJ | 0.119167 nJ | 0.438245 nJ | 2048/2048 |
| demo_10k_v1 | 10000 | 2048 | compressed_duration_fs | 0.0233742 fs | 0.0851587 fs | 2048/2048 |
| demo_10k_v1 | 10000 | 2048 | compressed_peak_power_MW | 0.00247457 MW | 0.00982841 MW | 2048/2048 |

These are different fixed synthetic test sets. Meeting tolerances is not zero error, real-solver accuracy, or a controlled sample-size ablation. Both versions keep diagnostic intervals limited.
