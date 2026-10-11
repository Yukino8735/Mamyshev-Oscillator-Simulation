# Git 发布预审清单（未执行 Git 写操作）

完整逐文件相对路径、大小、SHA-256、tracked/staged/ignored 状态、ignore 规则、用途和建议见本地 `reports/local/demo_10k_release_001/git_release_manifest.json`。
这里只记录当前工作树、索引与可用本地历史；没有联网核对远程，不能声称远程从未含数据。公开状态 `public_release_blocked`。

逐文件SHA256对应当前工作树字节；索引检查记录tracked/staged状态，未另审查不同的staged blob内容。JSON结构检查只针对可识别的逐点/ID数组，不是所有编码数据或秘密的完备探测。

| 分类 | 当前文件数 | 后续动作 |
|---|---:|---|
| keep_local | 1884 | 详见逐文件清单；均未自动 stage/commit/push |
| include | 243 | 详见逐文件清单；均未自动 stage/commit/push |
| review_sensitive | 40 | 详见逐文件清单；均未自动 stage/commit/push |
| needs_untrack_approval | 149 | 详见逐文件清单；均未自动 stage/commit/push |
| blocked_license | 860 | 详见逐文件清单；均未自动 stage/commit/push |

索引当前跟踪 1017 个路径，staged 0 个路径；可用本地历史中发现 340 个相关数据/文档对象。

分类按保守路径规则预审：149个needs_untrack_approval路径包括归档脚本，并非149份数据集。
此分类不要求删除/取消跟踪源码；归档代码的拟公开范围及署名须逐项确定。
blocked_license也不表示每个引擎包文件都是当前运行所需材料。机器清单为收尾时点
快照，本文和最终报告随后补充说明；最终文档hash另存本地final_document_hashes.txt。

## A. 拟提交工程文件

`demo/app.py`、`demo/ui_logic.py`、`src/mamyshev_ml/demo_inference.py`、`src/mamyshev_ml/demo10k_experiment.py`、本批计划/训练/检查 scripts 与 tests、`configs/` 小型协议、README/指南、聚合 metrics 和 docs/assets 图。每个实际文件的摘要与敏感路径命中在机器清单；include 是建议，不是发布授权。

## B. 仅本地

`reports/local/`、完整 train/dev/cal/test/候选池、全部 10k plan、逐点评分/预测、SQLite/JSONL/CSV、原复场 MAT 和私人日志全部 keep_local。数据换成 JSON、ZIP 或 Git LFS 仍然是数据发布，不接受该绕行。

## C. 轻量推理工件

`demo/assets/models/` 下明确受信的权重、原类、域/schema、必要 q、聚合 model card 与独立 manifest；不得夹带训练 X/Y、ID 排除表或旧整个 ZIP。功能副本含许可待审工件，不等同获准公开版本。需先确认模型/配方/源码归属。

## D. 已跟踪数据、历史和第三方

`.gitignore` 只影响未跟踪项，不能清除现有索引或历史。以下实际已跟踪数据需要单独审批；本批未删除、未 git rm --cached、未取消 stage 或改写历史。

| 已跟踪数据路径 | 大小（字节） | SHA-256 |
|---|---:|---|
| `archive/original_experiment_folder/Linear1.m` | 19246 | `6cb8b45127ac3c041462d2afcfd7138fefd27695290983a645ebdfe65e5ba0ec` |
| `archive/original_experiment_folder/Mamyshev4.m` | 7183 | `c01e69e44f9c4e8d4c7a377a054a93cebb547b8a492db92f49bbdd384fea6870` |
| `archive/original_experiment_folder/Mamyshev_Oscillator_ring_cavity.m` | 13703 | `2a7529faff485299fb4cf80f67869d638365ceaab02b757eb11acb228a63abff` |
| `archive/original_experiment_folder/Mamyshev_Oscillator_ring_cavity_1.m` | 13608 | `4644afd3bf30469f2d5eab037c17c4788bfa17da13a478efbde97a0c9d2189ae` |
| `archive/original_experiment_folder/New_Mamyshev.m` | 11567 | `88bccf09ecd05bad3c0e1761fbe2eefd731b9bfc9c61b86fd282853562688a0c` |
| `archive/original_experiment_folder/New_Mamyshev_2.asv` | 10858 | `06500398e93c783c2e0e46b5ba9e66d0868c347e8cfbb5d14fa4f8129653bb77` |
| `archive/original_experiment_folder/New_Mamyshev_2.m` | 12067 | `e2983148425dd82f1f56102bab6bf6f999f6f1e206c229d133f5a2ba054237cc` |
| `archive/original_experiment_folder/New_Mamyshev_3.m` | 14549 | `442621700134832db61a4ac9be1e282da0ef56343bd9cf4f2751dc9238ddb315` |
| `archive/original_experiment_folder/New_Mamyshev_linear.m` | 14596 | `23c8a9cb5131404262a2896bebdce244eb26552337a7ee3f9cf83265c1825ccb` |
| `archive/original_experiment_folder/bandwidth_central_wavelength.png` | 140419 | `99bf6a2a45bb43dc390d3ea27ab9470091ae309a4c3cae5283519a4147262d0d` |
| `archive/original_experiment_folder/bandwidth_energy_peak_power.png` | 163108 | `7c14d7d895e058692cafc7778314962b55ebb6f981fec38f653c5fbaa12360fa` |
| `archive/original_experiment_folder/bandwidth_pulse_duration.png` | 97404 | `2dde0a3434e64923290f3c627e6bf286376ebf4672456418da7fbae9561963db` |
| `archive/original_experiment_folder/gain_central_wavelength.png` | 167644 | `e36e7dbd2e61f6821438dd08a3b7ce43b9b2ed39de88d5186f12ee8b6a1acbd9` |
| `archive/original_experiment_folder/gain_energy_peak_power.png` | 147847 | `1bc4135e67bb5f2c33c019abc5f6979e36401ac310977e860f5d58dca0f68518` |
| `archive/original_experiment_folder/gain_pulse_duration.png` | 110482 | `2a455cd6795dd92e32ff97d37c4fe202376bbc28a9d1b57e989f0be240e2e378` |
| `archive/original_experiment_folder/mamyshev_phase_scan.mat` | 1693 | `fe073d212f18a56f426ef2525f01eae708db885e36bffae986e69b5e302b2bba` |
| `archive/original_experiment_folder/offset_central_wavelength.png` | 139567 | `a45e5ac5683c392c70290f0707871318c8c3f40210119800e3cc79f9f15730af` |
| `archive/original_experiment_folder/offset_energy_peak_power.png` | 163130 | `e6ff0ba61e042b10e78308aab2f1ea9f48941ecfa2095060f1960183f1d603a0` |
| `archive/original_experiment_folder/offset_pulse_duration.png` | 100205 | `4ee868586a50285b4eb61db698c5565ebda1e1a0d5a7bab89e70220800f4c045` |
| `archive/original_experiment_folder/processed_scan_figures/FBG_offset_scan.png` | 306108 | `27916cc6034333c05c819b2455bacb2ba6f9cc721e0ed2b0ba0e31ff497cf602` |
| `archive/original_experiment_folder/processed_scan_figures/LR_FBG_bandwidth_scan.png` | 307403 | `d6af2bc8a185e02066ad98e0d810d3570952a18c06702a553c9ff248a1ea8e98` |
| `archive/original_experiment_folder/processed_scan_figures/gain_fiber_length_scan.png` | 280535 | `26c7ba4af31f8a811210f6d2f717a763ea885c19efe3f2f0f8e32d059e67ceae` |
| `archive/original_experiment_folder/processed_scan_figures/processed_FBG_offset.csv` | 564 | `29e9514e6f5fc0dbda90b4e3a469b78bbeb6820ec09d2c7f9c382f72ad68643f` |
| `archive/original_experiment_folder/processed_scan_figures/processed_LR_FBG_bandwidth.csv` | 284 | `6529f68389cfdbf8820cbbdf6d6201dcff5ba892ddaa29da52ed0c7099a3e1bd` |
| `archive/original_experiment_folder/processed_scan_figures/processed_all_scan_data.mat` | 3419 | `c4538fda4c92644d04616f1b84152eec3433581e648664e8e9a2707fb27ac88f` |
| `archive/original_experiment_folder/processed_scan_figures/processed_gain_fiber_length.csv` | 593 | `7faed5c6fddfdbd67a18aca0d74bb9312e1053e438262ec70f23baaf7115285c` |
| `archive/original_experiment_folder/processed_scan_figures/processed_pump_power.csv` | 645 | `b109ce22d3e03c2f4910d298687b82282b5869d11a7908aac80290fb5fb38b61` |
| `archive/original_experiment_folder/processed_scan_figures/pump_power_scan.png` | 300196 | `740f127c4d7f5571933e326b12a3c4a328071d2c2b756c820e59081bcae1f4b7` |
| `archive/original_experiment_folder/pump_central_wavelength.png` | 179438 | `ccabcd5be496ab78d0803ed734d61c2683f00e35dbc5549281d1509dd1469591` |
| `archive/original_experiment_folder/pump_energy_peak_power.png` | 158584 | `014f79e56342727ff7123e941048cfb4d56559158a148726758d1347640bcaa7` |
| `archive/original_experiment_folder/pump_pulse_duration.png` | 98165 | `880b7416ea496b049f3c08467ce89ec96d685b82b9968676f2716d97928c467b` |
| `archive/original_experiment_folder/run_mamyshev.m` | 11628 | `aceb1935b46839725431abac5ffa30e883d02fac4d8f3bb3fd8a959020ef06b6` |
| `archive/original_experiment_folder/scan_linear_FBG_mamyshev.m` | 17378 | `f5a1b0be25905254ab65f0e948b46c82888d1d07327e01b4988a6e73b55b26d7` |
| `archive/original_experiment_folder/scan_mamyshev.m` | 2236 | `53f75e6af819f97c8db617d356e19d44b9c6930c92f18edfc8b0e42806be208f` |
| `archive/original_experiment_folder/scan_results_linear_FBG/FBG_offset_central_wavelength.png` | 69598 | `f2bd5d6bfc202e72c982e34c174e9f5c643e6463b76e070057f07ef1e1895cae` |
| `archive/original_experiment_folder/scan_results_linear_FBG/FBG_offset_peak_power.png` | 47995 | `b6875addbb803fe21f97f101cd14d62b9175fc4c7854fba03f7422b4a122295f` |
| `archive/original_experiment_folder/scan_results_linear_FBG/FBG_offset_pulse_duration.png` | 47573 | `442fc7387bca312fc8bff03b684d01e37e67ca9040395e8f31db819a7d18452c` |
| `archive/original_experiment_folder/scan_results_linear_FBG/FBG_offset_pulse_energy.png` | 54603 | `8ee5fe4c93e16394e08e12b2e4bbfad41f5ffbadea5e47ff5693c8cf3827fdc6` |
| `archive/original_experiment_folder/scan_results_linear_FBG/LR_FBG_bandwidth_central_wavelength.png` | 57840 | `c46008b9e133e16b4f09db3e6c1f3560c484d9a19ab87b8750dba0f012a1fab3` |
| `archive/original_experiment_folder/scan_results_linear_FBG/LR_FBG_bandwidth_peak_power.png` | 47118 | `018ca5e752fe3be69e2bcf40a43b327233f87b262b8c8da710323f1ea524a361` |
| `archive/original_experiment_folder/scan_results_linear_FBG/LR_FBG_bandwidth_pulse_duration.png` | 47851 | `1367b9f4762dacaaa1d5ef0e45c07a146c361763133b61bf7633542cf06c9748` |
| `archive/original_experiment_folder/scan_results_linear_FBG/LR_FBG_bandwidth_pulse_energy.png` | 38646 | `0f44ff70003a7898795ab25ab8b78f9ed9166ef76d2af2ab662f855a7a334ecd` |
| `archive/original_experiment_folder/scan_results_linear_FBG/all_scan_results.mat` | 14739 | `d29e0b5ca8483d260c2c1b0dc7eebf40a349ec715bf3db00a88993d90c1c14ea` |
| `archive/original_experiment_folder/scan_results_linear_FBG/gain_fiber_length_central_wavelength.png` | 57680 | `db2f0aee559ae8e434602fd0e77b5c740bab2fd5cde3f919fa0cd9ecb9cbefa8` |
| `archive/original_experiment_folder/scan_results_linear_FBG/gain_fiber_length_peak_power.png` | 41174 | `280c2ef3c3233ffed00b107aa843fc100c91c833dd471a96ab1f3887a5bfb46f` |
| `archive/original_experiment_folder/scan_results_linear_FBG/gain_fiber_length_pulse_duration.png` | 51962 | `9f3b757c7e59725bdde9c0ef41405f815bb59251cd85638ce9643d10dcbf4b3a` |
| `archive/original_experiment_folder/scan_results_linear_FBG/gain_fiber_length_pulse_energy.png` | 41274 | `9592b836bd6a4b3691ad26f51f56d9c8e07a89d6832411c6f520cce8a31ec9ed` |
| `archive/original_experiment_folder/scan_results_linear_FBG/pump_power_central_wavelength.png` | 57422 | `fbc34c496abc6c4f3bb4023cf2add9db3fe0c1d77df20e778fc40237b1e72d3e` |
| `archive/original_experiment_folder/scan_results_linear_FBG/pump_power_peak_power.png` | 41859 | `0daaa16f8c1717e9b6e9bd613273c411b148732027927a7a9590e5411b9fde67` |
| `archive/original_experiment_folder/scan_results_linear_FBG/pump_power_pulse_duration.png` | 44510 | `87d8ab2c5312160bf45928368c131e7f9c7532723f88e88116ed9da650ce71dc` |
| `archive/original_experiment_folder/scan_results_linear_FBG/pump_power_pulse_energy.png` | 45329 | `630ec6bc24342c2dc75a3653a1b129bb214af7dac2037de51b8b3265b0254654` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_LRbw_0p7500.mat` | 361 | `f3e497dfeefd7f01f59ecc03d6dfb53e178b5bf4baea73ec921d1ecd8663208f` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_LRbw_1p0000.mat` | 361 | `756bc1ecb8136e24c4bea65b1f3187b9ca7c66aa95c9f2767328b54189fd7032` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_LRbw_1p2500.mat` | 361 | `4a0d65fe21c9faca0b2fa5dbe1f68ebc1a398411804538c6f4e8639561b0c697` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_LRbw_1p5000.mat` | 362 | `b856fdf1d6fb8e8c56c94d9e1d658ef83c1aed01edeb51f8e53b170e9d7481ce` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_LRbw_1p7500.mat` | 362 | `ef206330cc5215b1d9f74926141f99f93ac44abb064e37d23feb9f3f80a5aba1` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_LRbw_2p0000.mat` | 361 | `8daa440bbca621a42279e1facdf7da3721b89f18ba9a0e04fce19ba256d9ec27` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_gainL_0p5000.mat` | 359 | `fa714ce00e5f553086b114d01c26ae9bce15883cc73b360cb0a8ebe1aa42fd13` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_gainL_0p6000.mat` | 359 | `cb1f4f3a6673579f9fa41fa92e44a928c5d09dbc0bb98f1477ae2447f56c815c` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_gainL_0p7000.mat` | 361 | `c70a86565a42689486948fcffab4a64f0c345cc4e8d2359c8e9e8761187119ce` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_gainL_0p8000.mat` | 361 | `90bd55f9647cc6866875d02e5e3dad6fc4caf454cf2fbbba8d90a2e290b12fda` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_gainL_0p9000.mat` | 361 | `d9e73872a0f5fc0142b2339f24496ca849280ec4cc55f3ff4aae0c512e402045` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_gainL_1p0000.mat` | 361 | `d390aad5d7dc4d08cc8869f8ea8a3c08c7bae488647dab8e80cee9e5f17f04b6` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_gainL_1p1000.mat` | 361 | `1d8db246f0311f5cb22614db179a32bfe9a6749501ed54017955d634d19a8762` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_gainL_1p2000.mat` | 361 | `29643745e4a090916dce633cfb189b28179257d1a9e0940bdfbe6376ec2dd285` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_gainL_1p3000.mat` | 361 | `25c2a814092606aa42c37909a520f236e6e479452f0a0564e9dfd5dadef62a06` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_gainL_1p4000.mat` | 361 | `8ee30897bc08cea1bb3466a469695089f187674164ad437d62ef004c06bbe9ed` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_offset_10p0000.mat` | 361 | `6aa25b9b77b2106e26f1505200d8bc489fc9db56fb89971b848e2c15553da549` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_offset_3p0000.mat` | 361 | `c4939875fb841753fde69c951230017a60a62b0a5758a4fe3038ed0c68da6e3a` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_offset_3p5000.mat` | 361 | `6a5b1c2b3dcc77a2f25a17236e109f9541a458e818e39bcb7eff51cdd5761969` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_offset_4p0000.mat` | 361 | `71e12c2d8f307fbc812a8f77af2905a702bbef9d99b8d478a92ebff615644578` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_offset_4p5000.mat` | 361 | `f0445dd18e3d6b6a90cba14d598da34c400b7a90e0441716072df28697fd7289` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_offset_5p0000.mat` | 361 | `c6e6b17bb3f2bd64757e8949ee6da6cd903c5ee6d932a6dbb74907956d422e1a` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_offset_5p5000.mat` | 361 | `3587250362d90a4874f37ffad01c5a632b06da04817ff7074d4f3ade2490e7f1` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_offset_6p0000.mat` | 361 | `598f2eaf40694bc48ded8685603e0fc6b534d6d3ee7bb2b45925545ee40543e0` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_offset_6p5000.mat` | 362 | `a68213e1ab1f71e95e9dd05169daad86c3df6c953e63cbcf737a3d684facccc2` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_offset_7p0000.mat` | 361 | `0d464d799a030c5547fc4252573c3ae97eba07f08aa1e9722b5071e8136bf3a3` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_offset_7p5000.mat` | 362 | `62e3904649e862618f7de2e44451d32ca0974cb1abf0e803e5b3b564c7047093` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_offset_8p0000.mat` | 361 | `830851d88b983b346f98ceb9238f9ea822a952d80c73d468d8d06988c800cca8` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_offset_8p5000.mat` | 361 | `c35e26c82558cc315b776b55b97a87ce730f3cc3c76ff78b60b0b11d6eecc26d` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_offset_9p0000.mat` | 361 | `327a5b9943b18b349e4371147cb0f6affc8d86bd596ab30df397c062a4670571` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_offset_9p5000.mat` | 361 | `9533567333eaf7d70d677e44882f458eb5fee472d2163556b0afbddbd1b1b2e3` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_pump_3p0000.mat` | 361 | `c3d3186267ce27d550236580b1849932c12b51e2cf034eeba30c0d63718bce14` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_pump_3p2500.mat` | 361 | `8a2731e918263fad4f4e4994272c5fbf5d9d03b06319e2d18ae30a4ab0127cba` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_pump_3p5000.mat` | 361 | `004bb1848d474e8f15e34309c0d16fa5dda9bd4ddc89d0f634eb5fbaa29d1c8e` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_pump_3p7500.mat` | 361 | `aacc70a322696d053bb9c0b99a502ed36f41bf6423e77c7ab47c3a5243a448ff` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_pump_4p0000.mat` | 361 | `3a184b0344fb5bf5ecc0dc03cf38c305326f1841ed1402694548f1ad0bda7bf1` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_pump_4p2500.mat` | 360 | `a8d183d83b44fcd62a39ed09ceb37dac8561f0fc68f4873a2d250d67a2e28df2` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_pump_4p5000.mat` | 361 | `792b2a3d08673f10dd16dc1e4222a32f0d89fda5dab93aa962d574b7eba93943` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_pump_4p7500.mat` | 362 | `0b5e6ae43b3e70d9d9264053306d61a88a0df98e8508cf83f1213128cd6764aa` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_pump_5p0000.mat` | 361 | `2ec0fffafb2b37b90672301bf8cc32aeeff61ae8378eceb2ac4156e50359b3d3` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_pump_5p2500.mat` | 361 | `f280df2427bcf9fe6a8ea91a3d656a56d106695bf8e635508674e1f19936341c` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_pump_5p5000.mat` | 361 | `c68f2b9ee41f6ede526940f15782e4522414afb29f419142485d5eb9560bb366` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_pump_5p7500.mat` | 361 | `7c29d093ad82859a88291f811abe33eb547b53d96499aa98c39d21635d07bea9` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_pump_6p0000.mat` | 362 | `32620947947db9989ae8396f1e6f881a22b85b5a4259540ec8e253cd5ddb32c2` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_pump_6p2500.mat` | 360 | `06ccacb933432a14dfa2e24694b0a8dbc7bdb9a1b70d9396094c6e75165ff752` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_pump_6p5000.mat` | 361 | `4399761ee935f3674bcdbb98e92a81a54c167f7cb88007bc1e39e9943b0c59a3` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_pump_6p7500.mat` | 361 | `30b05b658a95046c8adbdb64f1d8a026da3f91025f513d9cede7fc318bf790dd` |
| `archive/original_experiment_folder/scan_results_linear_FBG/result_pump_7p0000.mat` | 361 | `d0369ba64b608ddd649e73a13fb3373d2fef5cd7bbf13890427586b083499998` |
| `archive/original_experiment_folder/scan_results_linear_FBG/scan_FBG_offset.csv` | 2009 | `d74eaa407ef1b1729f8ebb9ca70962448bd131ed8178b3e0317fd6f42acae32a` |
| `archive/original_experiment_folder/scan_results_linear_FBG/scan_FBG_offset.mat` | 3990 | `f2fee46d1043c063bc8ca372d8e5fc34e153ce95f6484ad9e02f7874c157756d` |
| `archive/original_experiment_folder/scan_results_linear_FBG/scan_LR_FBG_bandwidth.csv` | 2081 | `9975e2110de80aa116e2aa6c479616176846176c4edb5f4d70f2c5b1a21e3f49` |
| `archive/original_experiment_folder/scan_results_linear_FBG/scan_LR_FBG_bandwidth.mat` | 3726 | `8ff28d7d793f43c7b6fb820c0698bdb0ae22523c4aa8f91d7d297bef9c2d34d5` |
| `archive/original_experiment_folder/scan_results_linear_FBG/scan_gain_fiber_length.csv` | 2906 | `0a5aa5818231704df05f6ae7a55238519bb010de320daf4370cb72ea7fd81aab` |
| `archive/original_experiment_folder/scan_results_linear_FBG/scan_gain_fiber_length.mat` | 4859 | `fa4399e9b9f9ef5ac7498bd271299780d9c0b98cf5538931fa073f923ce335ce` |
| `archive/original_experiment_folder/scan_results_linear_FBG/scan_pump_power.csv` | 2235 | `96131a00303e467150e29f72a166f66039d85495971bc5eaab63e588c2eb9312` |
| `archive/original_experiment_folder/scan_results_linear_FBG/scan_pump_power.mat` | 4106 | `fa019f0ecebbfc516e4d7c2a08c3b23fc0405db6da7566cded63ddb9a9e6ec6b` |
| `archive/original_experiment_folder/trend_guided_mamyshev_figures/FBG_offset_scan.png` | 285303 | `18f67a1296cd460baf26d29db4f7bd6cbf49f466d5b0931854f620c88ca285b6` |
| `archive/original_experiment_folder/trend_guided_mamyshev_figures/LR_FBG_bandwidth_scan.png` | 302961 | `6ffcdd7eae131f07438aaccec7ab2c42c697c531d2233c52aec9f72df4ede5d7` |
| `archive/original_experiment_folder/trend_guided_mamyshev_figures/gain_fiber_length_scan.png` | 278042 | `07577758588463c3a75c5906d1ad0538a7e8d9fac0cf947df7b36f92e6994550` |
| `archive/original_experiment_folder/trend_guided_mamyshev_figures/pump_power_scan.png` | 278601 | `76813c78dc64b33c7b5cd0a3994667e6547a007c07c7f9d2b8b14143a693d2a4` |
| `archive/original_experiment_folder/trend_guided_mamyshev_figures/trend_guided_FBG_offset.csv` | 463 | `2a7d3489da9a7ffda29afd8d93eb2edb1a053b7a6394dc550cc8b6274469d848` |
| `archive/original_experiment_folder/trend_guided_mamyshev_figures/trend_guided_LR_FBG_bandwidth.csv` | 475 | `bcc516fb6ae3c53bdc44f4103af060ba126419d43f64f4fdbe95633eba51a7fe` |
| `archive/original_experiment_folder/trend_guided_mamyshev_figures/trend_guided_all_scan_data.mat` | 2990 | `d13f5b9662a1f40f435fd052e04bbd2b92d4b7c921fc059fce6928697a6d7e0c` |
| `archive/original_experiment_folder/trend_guided_mamyshev_figures/trend_guided_gain_fiber_length.csv` | 496 | `5d1f2a4f0c2287d07f5a3b57ba6a22b648f860fb9fce8a2fc98b55f814b10050` |
| `archive/original_experiment_folder/trend_guided_mamyshev_figures/trend_guided_pump_power.csv` | 527 | `3debd8e50f47f1fc0c38bc3a174416b2d7903bb56d4ff79b45a78c2d19aa8839` |
| `archive/original_experiment_folder/数据.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `data/linear_cavity/trend_guided/FBG_offset_scan.png` | 285303 | `18f67a1296cd460baf26d29db4f7bd6cbf49f466d5b0931854f620c88ca285b6` |
| `data/linear_cavity/trend_guided/LR_FBG_bandwidth_scan.png` | 302961 | `6ffcdd7eae131f07438aaccec7ab2c42c697c531d2233c52aec9f72df4ede5d7` |
| `data/linear_cavity/trend_guided/gain_fiber_length_scan.png` | 278042 | `07577758588463c3a75c5906d1ad0538a7e8d9fac0cf947df7b36f92e6994550` |
| `data/linear_cavity/trend_guided/pump_power_scan.png` | 278601 | `76813c78dc64b33c7b5cd0a3994667e6547a007c07c7f9d2b8b14143a693d2a4` |
| `data/linear_cavity/trend_guided/trend_guided_FBG_offset.csv` | 463 | `2a7d3489da9a7ffda29afd8d93eb2edb1a053b7a6394dc550cc8b6274469d848` |
| `data/linear_cavity/trend_guided/trend_guided_LR_FBG_bandwidth.csv` | 475 | `bcc516fb6ae3c53bdc44f4103af060ba126419d43f64f4fdbe95633eba51a7fe` |
| `data/linear_cavity/trend_guided/trend_guided_all_scan_data.mat` | 2990 | `d13f5b9662a1f40f435fd052e04bbd2b92d4b7c921fc059fce6928697a6d7e0c` |
| `data/linear_cavity/trend_guided/trend_guided_gain_fiber_length.csv` | 496 | `5d1f2a4f0c2287d07f5a3b57ba6a22b648f860fb9fce8a2fc98b55f814b10050` |
| `data/linear_cavity/trend_guided/trend_guided_pump_power.csv` | 527 | `3debd8e50f47f1fc0c38bc3a174416b2d7903bb56d4ff79b45a78c2d19aa8839` |
| `data/ring_cavity/mamyshev_phase_scan.mat` | 1693 | `fe073d212f18a56f426ef2525f01eae708db885e36bffae986e69b5e302b2bba` |
| `results/linear_cavity/trend_guided/FBG_offset_scan.png` | 285303 | `18f67a1296cd460baf26d29db4f7bd6cbf49f466d5b0931854f620c88ca285b6` |
| `results/linear_cavity/trend_guided/LR_FBG_bandwidth_scan.png` | 302961 | `6ffcdd7eae131f07438aaccec7ab2c42c697c531d2233c52aec9f72df4ede5d7` |
| `results/linear_cavity/trend_guided/gain_fiber_length_scan.png` | 278042 | `07577758588463c3a75c5906d1ad0538a7e8d9fac0cf947df7b36f92e6994550` |
| `results/linear_cavity/trend_guided/pump_power_scan.png` | 278601 | `76813c78dc64b33c7b5cd0a3994667e6547a007c07c7f9d2b8b14143a693d2a4` |
| `results/ring_cavity/2015.png` | 419716 | `a446866686e925a9886b81a71444f76c1946f28ed3f4a7d2538340f400b66e43` |
| `results/ring_cavity/final.png` | 86212 | `ef6bdbaa36eb81e61ad93dc2c8395a4914fd1e3a2a734e93d531f0830cc2c1ff` |
| `results/ring_cavity/legacy_root/pumppower_E.png` | 61319 | `90abad546f985559e6e3a0b6bb132fa9ecb8a403eb301e4f9bdeb9f34962746b` |
| `results/ring_cavity/legacy_root/pumppower_FWHM.png` | 46568 | `eb0a9ae47c7de3d1417f95188273e15390a96982b772483f39ed3df35e1df9df` |
| `results/ring_cavity/legacy_root/pumppower_wave.png` | 54275 | `e5f4a205e3c3d4b7d1c75f870f3a36645528fb0958932fab14f92f58cf378564` |
| `results/ring_cavity/legacy_root/untitled.fig` | 23543 | `d72b5c6f98cc67f4da4e53b056f347121ae38e2a26cd8f38bc350f804f89f134` |
| `results/ring_cavity/parameter_scans/bandwidth_central_wavelength.png` | 140419 | `99bf6a2a45bb43dc390d3ea27ab9470091ae309a4c3cae5283519a4147262d0d` |
| `results/ring_cavity/parameter_scans/bandwidth_energy_peak_power.png` | 163108 | `7c14d7d895e058692cafc7778314962b55ebb6f981fec38f653c5fbaa12360fa` |
| `results/ring_cavity/parameter_scans/bandwidth_pulse_duration.png` | 97404 | `2dde0a3434e64923290f3c627e6bf286376ebf4672456418da7fbae9561963db` |
| `results/ring_cavity/parameter_scans/gain_central_wavelength.png` | 167644 | `e36e7dbd2e61f6821438dd08a3b7ce43b9b2ed39de88d5186f12ee8b6a1acbd9` |
| `results/ring_cavity/parameter_scans/gain_energy_peak_power.png` | 147847 | `1bc4135e67bb5f2c33c019abc5f6979e36401ac310977e860f5d58dca0f68518` |
| `results/ring_cavity/parameter_scans/gain_pulse_duration.png` | 110482 | `2a455cd6795dd92e32ff97d37c4fe202376bbc28a9d1b57e989f0be240e2e378` |
| `results/ring_cavity/parameter_scans/offset_central_wavelength.png` | 139567 | `a45e5ac5683c392c70290f0707871318c8c3f40210119800e3cc79f9f15730af` |
| `results/ring_cavity/parameter_scans/offset_energy_peak_power.png` | 163130 | `e6ff0ba61e042b10e78308aab2f1ea9f48941ecfa2095060f1960183f1d603a0` |
| `results/ring_cavity/parameter_scans/offset_pulse_duration.png` | 100205 | `4ee868586a50285b4eb61db698c5565ebda1e1a0d5a7bab89e70220800f4c045` |
| `results/ring_cavity/parameter_scans/pump_central_wavelength.png` | 179438 | `ccabcd5be496ab78d0803ed734d61c2683f00e35dbc5549281d1509dd1469591` |
| `results/ring_cavity/parameter_scans/pump_energy_peak_power.png` | 158584 | `014f79e56342727ff7123e941048cfb4d56559158a148726758d1347640bcaa7` |
| `results/ring_cavity/parameter_scans/pump_pulse_duration.png` | 98165 | `880b7416ea496b049f3c08467ce89ec96d685b82b9968676f2716d97928c467b` |

实际 GMMNLSE 与 third_party 中的 MAT/CSV/截面材料输入单列为引擎依赖，保留文件和逐文件声明，不用全局 *.mat/*.csv 忽略/删除破坏后端。MMTools GPLv3 不自动覆盖实际定制引擎。论文/毕业论文/第三方示例输出的许可逐项待审。

下一步需用户批准：拟公开模型/配方/自有图及源码许可范围；哪些已跟踪数据取消跟踪（如需）；历史是否需要另行处理及影响；精确提交allowlist。当前不执行这些操作。
