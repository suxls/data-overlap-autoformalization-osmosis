# HuggingFace Model Card Descriptions

Copy-paste the appropriate description into each model's HuggingFace model card.

---

### xiaolesu/OsmosisProofling-SFT

Experimental checkpoint from "Data Overlap as a Post-Training Hyperparameter for Autoformalization." This is the **SFT-only** variant (Qwen3-8B, thinking disabled) trained on 20K heterogeneous (natural-language, Lean 4) pairs. See the [paper repo](https://github.com/suxls/data-overlap-autoformalization) for details, results, and all artifacts.

---

### xiaolesu/OsmosisProofling-GRPO-NT

Experimental checkpoint from "Data Overlap as a Post-Training Hyperparameter for Autoformalization." This is the **GRPO-only** variant (Qwen3-8B, thinking disabled) trained directly on the base model without SFT priming. See the [paper repo](https://github.com/suxls/data-overlap-autoformalization) for details, results, and all artifacts.

---

### xiaolesu/OsmosisProofling-SFT-NT-GRPO-NT-No-Overlap

Experimental checkpoint from "Data Overlap as a Post-Training Hyperparameter for Autoformalization." This is the **SFT+GRPO with 0% overlap** variant (Qwen3-8B, thinking disabled) -- the best-performing condition, where SFT and GRPO data are fully disjoint. See the [paper repo](https://github.com/suxls/data-overlap-autoformalization) for details, results, and all artifacts.

---

### xiaolesu/OsmosisProofling-SFT-NT-GRPO-NT

Experimental checkpoint from "Data Overlap as a Post-Training Hyperparameter for Autoformalization." This is the **SFT+GRPO with 30% overlap** variant (Qwen3-8B, thinking disabled). See the [paper repo](https://github.com/suxls/data-overlap-autoformalization) for details, results, and all artifacts.

---

### xiaolesu/OsmosisProofling-SFT-NT-GRPO-NT-Overlap

Experimental checkpoint from "Data Overlap as a Post-Training Hyperparameter for Autoformalization." This is the **SFT+GRPO with 100% overlap** variant (Qwen3-8B, thinking disabled) -- the control condition where GRPO reuses SFT data entirely. See the [paper repo](https://github.com/suxls/data-overlap-autoformalization) for details, results, and all artifacts.
