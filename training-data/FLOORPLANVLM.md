# FLOORPLANVLM: A Vision-Language Model for Floorplan Vectorization

**Yuanqing Liu\*, Ziming Yang\*, Yulong Li, Yue Yang†**
Beike — {liuyuanqing006, yangziming006, liyulong008, yangyue092}@ke.com

*\*Equal contribution. †Corresponding Author.*
arXiv:2602.06507v1 [cs.CV] 6 Feb 2026

## Abstract

Converting raster floorplans into engineering-grade vector graphics is challenging due to complex topology and strict geometric constraints. To address this, we present FLOORPLANVLM, a unified framework that reformulates floorplan vectorization as an image-conditioned sequence modeling task. Unlike pixel-based methods that rely on fragile heuristics or query-based transformers that generate fragmented rooms, our model directly outputs structured JSON sequences representing the global topology. This "pixels-to-sequence" paradigm enables the precise and holistic constraint satisfaction of complex geometries, such as slanted walls and curved arcs. To support this data-hungry approach, we introduce a scalable data engine: we construct a large-scale dataset (FLOORPLAN-2M) and a high-fidelity subset (FLOORPLAN-HQ-300K) to balance geometric diversity and pixel-level precision. We then employ a progressive training strategy, using Supervised Fine-Tuning (SFT) for structural grounding and quality annealing, followed by Group Relative Policy Optimization (GRPO) for strict geometric alignment. To standardize evaluation on complex layouts, we establish and open-source FPBENCH-2K. Evaluated on this rigorous benchmark, FLOORPLANVLM demonstrates exceptional structural validity, achieving 92.52% external-wall IoU and robust generalization across non-Manhattan architectures.

**Figure 1 (Paradigm comparison):** Pixel-based methods suffer primitive mismatch from heuristic post-processing; query-based methods leave gaps between individually generated rooms. FLOORPLANVLM reframes vectorization as sequence modeling, directly outputting a structured JSON sequence (e.g. `{"id": "wall_1", "coords": [[117,319],[194,319]], "width": 10, "curvature": 21}, ...`) representing the global topology.

## 1 Introduction

Floorplan vectorization requires transforming rasterized images into structured geometric primitives (e.g., walls and rooms) while maintaining strict topological consistency [Gupta and Upmanyu, 2024]. Unlike natural image captioning, this task demands precise geometric alignment and logical correctness—walls must connect, and rooms must form closed loops. Traditional workflows heavily rely on manual tracing, creating a labor-intensive bottleneck for scalable architectural modeling [Skrzypczak et al., 2022; Salah et al., 2025].

Existing approaches typically treat vectorization as segmentation or isolated polygon detection [Kalervo et al., 2019; Yue et al., 2023]. While effective on simple layouts, these paradigms face significant challenges in scalability and structural coherence. As illustrated in Figure 1, pixel-based methods often struggle with resolution limits and require complex heuristics to assemble vector graphs. Similarly, query-based methods generating independent room polygons often suffer from structural decoupling to resolve shared boundaries in complex, non-Manhattan designs.

In this work, we introduce FLOORPLANVLM, a novel framework that reformulates vectorization as an image-conditioned sequence modeling task. Diverging from pixel-based methods that rely on fragile heuristics and query-based approaches that suffer from structural decoupling, our model directly synthesizes a unified JSON sequence describing the global topology. Central to this paradigm is a dependency-ordered serialization strategy: by explicitly defining a shared wall skeleton first and subsequently characterizing rooms as references to these structural primitives, we enforce topological consistency by design. This strategy eliminates the geometric gaps inherent in independent polygon predictions, while effectively capturing complex non-Manhattan geometries, such as slanted walls and curved arcs.

However, a fundamental tension exists: the probabilistic token generation of VLMs inherently conflicts with the deterministic precision required for architectural engineering. We resolve this by integrating a robust Data Engine with a geometric alignment strategy. Addressing the scarcity of diverse training data, we introduce a scalable Data Engine. We observe that raw industrial data, while abundant, often suffers from coordinate misalignment between raster screenshots and real-world structural labels. To leverage this scale, we first construct FLOORPLAN-2M via structure-aware clustering to capture long-tail geometric distributions despite spatial noise. We then bridge the precision gap by distilling FLOORPLAN-HQ-300K, a hybrid of human-recaptioned and synthetic re-rendered samples, to ensure strict pixel-aligned grounding.

Our contributions are summarized as follows:

- **End-to-End Sequence Modeling:** We propose a framework that reformulates vectorization as image-conditioned sequence generation, directly outputting render-ready JSON floorplans and enabling the holistic reconstruction of complex layouts without heuristic post-processing.
- **Scalable Data Engine & Open Benchmark:** We introduce a hierarchical data strategy, leveraging the large-scale FLOORPLAN-2M for structural diversity and the re-rendered and re-labeled FLOORPLAN-HQ-300K for pixel-aligned precision. Furthermore, we establish and release FPBENCH-2K, a rigorous open-source benchmark encompassing various complex floorplans, providing the community with a standardized testbed for topological reasoning.
- **Geometric Alignment via RL:** We bridge the non-differentiable gap between discrete tokens and continuous geometry using GRPO, reducing spatial hallucinations and achieving 92.52% External Wall IoU on FPBENCH-2K.

## 2 Related Work

### 2.1 Floorplan Vectorization

Floorplan vectorization has evolved from traditional low-level image processing to two dominant deep-learning paradigms: pixel-based and query-based methods.

**Pixel-based Approaches.** Methods such as CubiCasa5K [Kalervo et al., 2019] and L-CNN [Zhou et al., 2019] treat vectorization as segmentation or heatmap detection. While effective at extracting local features, they exhibit a fundamental representation mismatch: they output discrete raster maps while vectorization requires continuous graphs. Consequently, these methods rely on heavy, heuristic post-processing rules to assemble vector primitives, which often fail when encountering non-Manhattan geometries (e.g., slanted walls) that defy rigid connectivity assumptions.

**Query-based Approaches.** More recent works (e.g., RoomFormer [Yue et al., 2023] and PolyRoom [Liu et al., 2024]) utilize Transformers with fixed-size queries to predict vector sets. However, these methods typically operate in a room-wise manner, generating individual polygons independently. While these models capture global context, their room-centric parameterization fails to enforce the uniqueness of shared structural elements. This frequently results in structural inconsistencies—such as gaps between shared walls or overlapping rooms—that require complex, error-prone merging algorithms to resolve.

### 2.2 Vision-Language Models for Geometric Generation

Recent Large Vision-Language Models (VLMs) [Achiam et al., 2023; Bai et al., 2025] have demonstrated impressive semantic reasoning but often struggle with precise spatial generation, a phenomenon known as "geometric hallucination" [Chen et al., 2025]. While adaptation efforts like ChartLlama [Han et al., 2023] have applied VLMs to structured data extraction (e.g., charts), architectural drawings impose significantly stricter constraints: outputs must not only be syntactically valid JSON but also geometrically watertight (e.g., closed loops, aligned coordinates). Current literature lacks a scalable data synthesis framework capable of grounding the probabilistic generation of VLMs into the strict, verifiable geometric constraints required for engineering-grade vectorized floorplan reconstruction.

### 2.3 Reinforcement Learning for Geometric Alignment

While Reinforcement Learning from Human Feedback (RLHF) [Ouyang et al., 2022] excels at aligning models with subjective human preferences, geometric vectorization demands adherence to strict, objective constraints. This requirement aligns with recent advancements in mathematical reasoning, where frameworks like DeepSeekMath [Shao et al., 2024] introduce Reinforcement Learning with Verifiable Rewards (RLVR) to optimize for deterministic correctness (e.g., answer compilation) rather than learned reward proxies. Extending this paradigm to the geometric domain, recent works such as SpaceR [Ouyang et al., 2025] and ReCAD [Li et al., 2025] utilize geometric fidelity metrics as reward signals. These approaches demonstrate the capability of RLVR to transform VLMs from probabilistic token generators into rigorous geometric reasoners.

## 3 Problem Formulation

### 3.1 Sequence Modeling

We cast floorplan vectorization as an image-conditioned sequence modeling task. Given a rasterized floorplan image *I*, our goal is to generate a sequence of discrete tokens *T* = (t₁, t₂, …, t_L) that deterministically parses into a structured geometric graph *S*. We model the conditional probability P_θ(T|I) autoregressively:

> P_θ(T|I) = ∏_{j=1}^{L} P(t_j | t_{j−1}, …, t₁, I)  **(1)**

where θ denotes the learnable parameters of the model. The token sequence *T* is deterministically converted into the structured geometric graph *S* via a parsing function, i.e., *S* = parse(T).

### 3.2 Geometric Alignment

While sequence modeling maximizes token likelihood, our ultimate goal is to ensure the reconstructed geometry *S* aligns with the ground truth structure *S_gt*. We formalize this as minimizing a geometric discrepancy metric *D*:

> θ* = argmin_θ 𝔼_{T∼P_θ(·|I)}[D(parse(T), S_gt)]  **(2)**

where *D* is a composite metric that evaluates both geometric fidelity (e.g., Intersection over Union) and topological validity. Crucially, the transformation parse(·) and the metric D(·) involve non-differentiable operations. This creates a fundamental disconnect between token-level training objectives and geometry-level evaluation, necessitating an optimization strategy beyond standard maximum likelihood estimation.

### 3.3 Floorplan Representation

To ensure topological consistency and support complex non-Manhattan geometries, we define *S* = (W, O, R) via a dependency-ordered parameterization.

**Walls.** The floorplan skeleton is a set of walls W = {w₁, …, w_N}. We parameterize each wall w_i to accommodate curved and slanted geometries:

> w_i = (p_start, p_end, τ, κ, O_i)  **(3)**

where p_start, p_end ∈ ℝ² denote the endpoint coordinates, and τ ∈ ℝ⁺ represents the wall thickness. The curvature parameter κ defines the wall geometry: κ = 0 indicates a straight wall, while κ ≠ 0 indicates a curved arc connecting the endpoints; the sign determines the curvature direction relative to the wall vector.

**Openings.** Openings (doors and windows) are modeled as attributes nested within their parent walls rather than as independent entities. The set of openings O_i associated with wall w_i contains elements parameterized as:

> o = (c, δ, ω)  **(4)**

where c ∈ {door, window} denotes the semantic class, ω is the opening width, and δ specifies the coordinate of the opening center along the wall centerline. This hierarchical design constrains openings to lie on their parent walls, significantly reducing geometric inconsistencies.

**Rooms.** We define rooms as functional zones derived from the wall graph. Each room r_k ∈ R is characterized by:

> r_k = (ℓ, E_k)  **(5)**

where ℓ is the semantic label (e.g., bedroom), and E_k = (i₁, i₂, …, i_m) is an ordered sequence of indices that reference walls in W and form a closed topological cycle.

## 4 Methodology

### 4.1 Framework Overview

FLOORPLANVLM is a unified generative framework designed to transcribe rasterized architectural drawings into precise, topology-aware vector code. To address the challenge of aligning probabilistic token generation with strict geometric constraints (as formulated in Sec. 3), we integrate three core components:

1. **Sequence Serialization (Sec. 4.2):** A token-efficient JSON serialization schema that maps hierarchical geometric primitives (walls, rooms, and openings) into a discrete sequence, using a custom vocabulary to reduce sequence length and improve stability.
2. **Data Engine (Sec. 4.3):** A scalable pipeline that constructs the FLOORPLAN-2M dataset via topological clustering and curates a high-fidelity subset, FLOORPLAN-HQ-300K, for precision refinement.
3. **Progressive Training (Sec. 4.4):** A three-stage optimization strategy. The model first learns syntactic rules and visual patterns via SFT, and then transitions to GRPO, a reinforcement learning algorithm that directly optimizes the non-differentiable geometric objectives defined in Eq. (2).

Figure 2 illustrates the overall pipeline, with Qwen2.5-VL-3B as the foundational vision-language model [Bai et al., 2025].

**Figure 2 (Framework Overview):** The model accepts a raster floorplan + prompt ("Please vectorize this floorplan.") and transforms it into a discrete token sequence via Qwen2.5-VL. A progressive training pipeline bridges visual perception and geometric logic: **Stage 1 SFT (Syntax)** → **Stage 2 SFT (Quality)** → **Stage 3 GRPO (Geometry)**. Output is a structured, hierarchical JSON sequence that deterministically parses into a precise vector floorplan (walls with coords/width/curvature/openings; rooms referencing wall IDs as boundaries).

### 4.2 Geometric Sequence Serialization

To enable the VLM to generate precise geometric vector graphics, we bridge the modality gap between continuous 2D coordinates and discrete 1D text tokens. We propose a token-efficient serialization strategy that maps the hierarchical layout *S* (defined in Sec. 3) into a compact JSON sequence.

**JSON Schema.** To strictly enforce topological consistency, we adopt a declarative JSON schema with a "Structure-First, Semantics-Second" serialization order, as shown in Figure 2:

1. **Geometric Skeleton (W):** The sequence begins by defining all walls and their nested openings. Each wall w_i is assigned a unique identifier (e.g., `"wall_1"`) and explicit attributes, including coordinates, curvature κ, thickness τ, and its openings O_i.
2. **Functional Zones (R):** Rooms are then defined by referencing the identifiers of their enclosing walls (e.g., `["wall_1", "wall_2"]`).

This dependency-ordered approach prevents common topological errors, such as floating rooms or gaps between shared boundaries, because each room definition is strictly grounded in the pre-defined wall skeleton.

**Token Compression and Representation.** Standard JSON is verbose, which can destabilize long-sequence generation. We address this via a hybrid representation strategy:

- **Coordinate Normalization:** To align geometric data with the visual encoder resolution, we normalize all floorplan coordinates by scaling the longer image edge to 1024 while preserving the aspect ratio. These coordinates are serialized as plain text tokens. This approach leverages the VLM's inherent capability to process numerical text, avoiding the complexity of defining a separate positional vocabulary while maintaining sufficient precision for architectural reconstruction.
- **Semantic Token Compression:** While coordinates remain plain text, we introduce a vocabulary of 1,391 custom special tokens to encode high-frequency JSON syntax and semantic keys. For instance, repeated attribute keys such as `"curvature"` or `"openings"` are compressed into single tokens (e.g., `<cv>`, `<op>`). This strategy reduces the total sequence length by approximately 25%, significantly lowering computational cost and ensuring the model operates within a manageable context window.

### 4.3 Scalable Data Engine

Training a generalist VLM requires data at scale. However, existing datasets are limited in both quantity and diversity. We introduce a scalable data engine that constructs FLOORPLAN-2M, the largest dataset to date, and refines it into a high-fidelity subset, FLOORPLAN-HQ-300K, for precision tuning.

**Figure 3 (Data Engine Overview):** Pipeline: Raw Data (20M) → *Structure-Aware Clustering & Sampling* → FLOORPLAN-2M (2M) → *Human Recaption & Synthetic Rendering* → FLOORPLAN-HQ-300K (300K) → Test Benchmark FPBENCH-2K (2K). Dual-view features for balanced sampling: **Geometry Contour** (Fourier Descriptors capturing global boundary invariance) and **Layout Topology** (graph embeddings encoding internal spatial logic of room connections via a floorplan adjacency matrix, e.g., distance between Bed1/Kitchen/Bed2/Living/Bath nodes, flattened into an embedded topology vector).

**FLOORPLAN-2M: Structure-Aware Clustering.** We start with a pool of over 20 million raw vector floorplans from an industrial interior design platform. Naive random sampling would bias the dataset toward repetitive, standard layouts (e.g., Manhattan-style apartments). To better cover long-tail geometries (e.g., slanted walls and curved balconies), we propose an unsupervised Structure-Aware Clustering framework:

*Feature Extraction* — we characterize floorplan similarity from two complementary perspectives:
1. **Geometric Contour:** Fourier Contour Descriptors (FCD) [Zhang et al., 2002] capture the global shape of the external boundary. By transforming the boundary's 1D shape signature into the frequency domain, we obtain a feature vector invariant to translation, rotation, and scaling.
2. **Internal Spatial Structure:** To encode room-arrangement logic, we construct a dual graph where nodes represent functional zones (e.g., bedrooms) and edges represent adjacency. We extract a layout vector based on the sorted pairwise distances between room centroids, making it invariant to room permutation.

*Clustering and Sampling* — using a weighted concatenation of these features, we perform Hierarchical Agglomerative Clustering (HAC) [Müllner, 2011]. We upsample rare clusters and downsample dominant ones, yielding a balanced FLOORPLAN-2M dataset with 2 million pairs.

It is important to note that the raw images are sourced as screenshots from the design platform, while the ground truth labels rely on real-world structural coordinates (e.g., in millimeters). Since the spatial transformation (scale and shift) of the screenshots are unknown, a coordinate gap exists between the visual pixels and the geometric labels. Despite this alignment noise, this scale enables the model to learn generalized structural topology, even if pixel-perfect precision is limited by the source data.

**FLOORPLAN-HQ-300K: High-Precision Refinement.** While FLOORPLAN-2M provides scale, the aforementioned coordinate gap precludes engineering-grade training. To support high-precision alignment, we curate FLOORPLAN-HQ-300K, where all samples possess strictly pixel-aligned coordinates:

- **Human-Recaptioned Subset (20K):** We sample diverse raw images and employ professional designers to manually redraw the vector graphs over the raster background. This ensures semantic correctness and eliminates the coordinate gap through human visual alignment.
- **Synthetic-Rendered Subset (280K):** To scale up pixel-perfect data, we leverage the structural vector graphs from FLOORPLAN-2M but discard the original screenshots. Instead, we re-render these vectors using an internal engine into CAD-style images. Since the rendering process provides access to the exact transformation matrix (scale and shift), we analytically project the real-world structural coordinates into the image pixel space, guaranteeing mathematical watertightness.

By combining human-corrected real data with geometrically precise synthetic data, this 300K subset serves as a rigorous "Gold Standard" for fine-tuning the model's geometric precision.

**Statistical Distribution Analysis.** (Figure 4) The raw FLOORPLAN-2M is dominated by standard Manhattan layouts (63.7%). Our structure-aware active sampling effectively rebalances the training distribution: in FLOORPLAN-HQ-300K, the proportion of non-Manhattan geometries (e.g., slanted walls and arcs) increases from 36.3% to **42.7%**. Crucially, the distribution of geometric primitive counts remains consistent with the source long-tail distribution, confirming that watertight filtering retains structurally complex samples rather than biasing toward simple layouts. This rebalanced, high-complexity training set is essential for the model to generalize beyond simple rectangular forms.

**Figure 4 — Statistical Distribution of Training Datasets**

*(a) Geometry distribution of FLOORPLAN-2M:*
| Category | Count | % |
|---|---|---|
| Manhattan | 1,396,673 | 63.7% |
| Non-Manhattan | 795,980 | 36.3% |
| — Slant Only | 643,527 | 29.3% |
| — Arc Only | 17,881 | 0.8% |
| — Both | 134,572 | 6.1% |

*(b) Primitive Count Distribution in FLOORPLAN-2M:* histogram over bins 10–19, 50–59, 100–109, 150–159, 200–209 primitives/floorplan, peaking around the 10–19 / 50–59 range and long-tailing out to 200+.

*(c) Geometry distribution of FLOORPLAN-HQ-300K:*
| Category | Count | % |
|---|---|---|
| Manhattan | 172,805 | 57.3% |
| Non-Manhattan | 128,719 | 42.7% |
| — Slant Only | 81,816 | 27.1% |
| — Arc Only | 5,388 | 1.8% |
| — Both | 41,515 | 13.8% |

*(d) Primitive Count Distribution in FLOORPLAN-HQ-300K:* same bin structure as (b), rescaled to the 300K subset.

### 4.4 Progressive Training Pipeline

Generating engineering-grade floorplans requires the model to master two distinct capabilities: understanding JSON syntax and reasoning under strict geometric constraints. We propose a three-stage progressive training regimen that transitions from broad semantic understanding to precise geometric alignment.

**Stages 1 & 2: Supervised Fine-Tuning (SFT).** The initial phases focus on likelihood maximization to ground the visual encoder and align the language model with our custom serialization format.

- *Stage 1 — Structural Grounding:* We first train the model on the large-scale FLOORPLAN-2M dataset. Due to the coordinate misalignment inherent in the screenshot-based data, explicitly optimizing for pixel-perfect vertex placement is infeasible at this stage. Instead, the primary objective is to adapt the VLM to the broad visual-structural distribution of architectural drawings. This stage grounds visual patterns to approximate geometric primitives, establishing a generalized layout understanding before precision refinement.
- *Stage 2 — Quality Annealing:* To reduce hallucinations and stabilize the output distribution, we perform a second round of SFT on the high-fidelity FLOORPLAN-HQ-300K subset.

In both stages, we optimize the standard autoregressive cross-entropy loss:

> L_SFT(θ) = −∑_{j=1}^{L} log P_θ(t_j | t_{<j}, I)  **(6)**

While SFT provides a strong initialization, it optimizes for token-level prediction accuracy, which correlates poorly with holistic geometric validity (e.g., a single wrong coordinate token can break a wall's connectivity).

**Stage 3: Geometric Alignment via GRPO.** To enforce hard physical constraints, we employ reinforcement learning in the final stage. We adopt Group Relative Policy Optimization (GRPO) [Shao et al., 2024], a variant of PPO [Schulman et al., 2017] that eliminates the need for a separate value network, thereby reducing memory overhead and improving training stability.

For each input image *I*, we sample a group of *G* outputs {T_k}_{k=1}^{G} from the old policy π_θold. Let ρ(T) = π_θ(T|I) / π_θold(T|I) be the policy ratio. We optimize the current model π_θ by maximizing the advantage of outputs with higher geometric rewards:

> J_GRPO(θ) = 𝔼_{I∼D, {T_k}∼π_θold(·|I)} [ (1/G) ∑_{k=1}^{G} ( min(A_k ρ(T_k), A_k clip(ρ(T_k))) − β D_KL(π_θ‖π_θold) ) ]  **(7)**

where A_k is the advantage score computed by standardizing the rewards within the group and clip(·) denotes ratio clipping. This forces the model to "self-correct" by contrasting better geometric generations against worse ones for the same input.

**Hierarchical Reward Modulation.** Designing a dense reward signal is crucial for stable RL training. We propose a hierarchical reward function R(T) that decomposes the objective into three levels of abstraction:

1. **Validity Check (R_val):** A binary reward ensuring the output is valid JSON and able to form a watertight closed polygon.
2. **External Geometry (R_ext):** The Intersection-over-Union between the predicted and ground truth external polygons. To prevent the model from optimizing internal details within a broken boundary, we use R_ext to compute a gating factor α:

> α = 0.1, if R_ext < 0.3;  lerp(0.1, 1.0, (R_ext − 0.3)/(0.7 − 0.3)), if 0.3 ≤ R_ext < 0.7;  1.0, if R_ext ≥ 0.7  **(8)**

where lerp(a, b, t) represents the linear interpolation between a and b weighted by factor t.

3. **Internal Structure (R_int):** This term evaluates F1 score and IoU metric of internal walls, openings, and room loops. Crucially, this reward is modulated by α (i.e., α · R_int), strictly penalizing the model if the global boundary is incorrect.

The final composite reward, guiding the model to prioritize global structural correctness before refining local internal details, is as follows:

> R(T) = w_val·R_val + w_ext·R_ext + α·w_int·R_int  **(9)**

where the balancing coefficients are empirically set to w_val = 0.1, w_ext = 0.5, and w_int = 0.4.

## 5 Experiments

Since existing benchmarks primarily focus on simplified rectilinear layouts, they fail to capture the full potential of our end-to-end vectorization paradigm. Therefore, we evaluate models on our custom benchmark to validate the effectiveness of the proposed architectural components, training stages, and data strategies.

### 5.1 Experimental Setup

**Dataset: FPBENCH-2K.** To rigorously assess topological reasoning, we evaluate all models on FPBENCH-2K, a held-out set of 2,000 samples. We stratify this benchmark into two subsets:

- **Manhattan Subset (1,040):** Layouts consisting strictly of orthogonal walls.
- **Non-Manhattan Subset (960):** Complex layouts featuring slanted walls, curved balconies, and irregular polygons. This subset serves as the primary stress test for geometric generalization.

**Figure 5 — Statistical Distribution of FPBENCH-2K**

*(a) Geometry distribution:*
| Category | Count | % |
|---|---|---|
| Manhattan | 1,040 | 52.0% |
| Non-Manhattan | 960 | 48.0% |
| — Slant Only | 682 | 34.1% |
| — Arc Only | 33 | 1.7% |
| — Both | 245 | 12.2% |

*(b) Primitive Count Distribution:* bins 10–19, 50–59, 100–109, 170–179 primitives/floorplan, confirming a wide range of primitive counts. Coupled with the increased non-Manhattan proportion, this provides a comprehensive stress test for geometric generalization across varying structural complexities.

**Metrics.** We employ a suite of vector-oriented metrics to measure structural validity:

- **Validity Rate (ρ_val):** The percentage of generated samples that are both syntactically valid JSON and geometrically watertight (i.e., forming closed polygons without topological gaps).
- **Ext-IoU (IoU_ext) & Room-IoU (IoU_room):** The Intersection-over-Union for the external boundary and individual rooms.
- **Room-F1 (F1_room) & Opening-F1 (F1_op):** The harmonic mean of precision and recall for semantic element detection. A prediction is considered a true positive only if it satisfies both strict geometric alignment (e.g., IoU > 0.5) and correct semantic classification.

**Implementation Details.** We use Qwen2.5-VL-3B [Bai et al., 2025] as the base model. Training is performed on 32×H200 GPUs. Stage 1 uses the full FLOORPLAN-2M dataset for 2 epochs, Stage 2 fine-tunes on FLOORPLAN-HQ-300K for 10 epochs, and Stage 3 (GRPO) samples G = 8 outputs per input with a KL coefficient of 0.01.

### 5.2 Main Results: Geometric Generalization

We report the performance of our final model after our three-stage training on the FPBENCH-2K test set. To assess geometric robustness, we break down performance by topological complexity (Manhattan vs. Non-Manhattan).

**Table 1: Main Results on FPBENCH-2K.** Structural validity (ρ_val), geometric fidelity (IoU), and semantic detection accuracy (F1). The model demonstrates exceptional generalization on complex non-Manhattan geometries.

| Subset | ρ_val (%) | IoU_ext | IoU_room | F1_room | F1_op |
|---|---|---|---|---|---|
| Manhattan | 97.02 | 0.9459 | 0.9089 | 0.8385 | 0.7739 |
| Non-Manhattan | 95.10 | 0.9027 | 0.8738 | 0.8101 | 0.6894 |
| **Overall** | **96.10** | **0.9252** | **0.8920** | **0.8249** | **0.7333** |

As shown in Table 1, FLOORPLANVLM achieves an exceptional 92.52% external-boundary IoU (IoU_ext). Notably, even on the challenging non-Manhattan subset, the model maintains 90.27% IoU_ext. The validity rate (ρ_val) remains robust (> 95%) across both subsets. This confirms that our sequence modeling approach successfully learns the generalized grammar of architectural geometry, rather than merely overfitting to simple rectilinear patterns.

### 5.3 Ablation Studies

To validate our method, we conduct comprehensive ablation studies focusing on the training strategy, data scaling, and sequence representation.

**Impact of Progressive Training Strategy.** We analyze the contribution of each training stage. Table 2 compares the performance of models stopped at different phases.

**Table 2: Ablation of Training Stages.** Stage 1 ensures structural generalization, Stage 2 refines visual alignment, and Stage 3 (GRPO) enforces strict geometric constraints.

| Configuration | ρ_val (%) | IoU_ext | IoU_room | F1_room | F1_op |
|---|---|---|---|---|---|
| (a) SFT Baseline (Stage 1 + 2) | 90.20 | 0.8567 | 0.8521 | 0.7945 | 0.7073 |
| (b) w/o Quality Annealing (Stage 1 Only) | 67.25 | 0.5238 | 0.4692 | 0.3873 | 0.3945 |
| (c) w/o Structural Grounding (Stage 2 Only) | 85.10 | 0.7598 | 0.7346 | 0.6674 | 0.6458 |
| (d) Ours w/ GRPO (Stage 1+2+3) | **96.10** | **0.9252** | **0.8920** | **0.8249** | **0.7333** |

**Figure 6 (Model Performance vs. Data Scale):** Stage 1 & 2 models trained on 30%, 60%, 100% of FLOORPLAN-2M / FLOORPLAN-HQ-300K (x-axis log scale), tracking ρ_syn, IoU (Exterior), IoU (Room), F1 (Room), F1 (Opening) — all curves rise steadily from ~0.2–0.6 at 30% to ~0.6–0.9 at 100%, with no clear plateau.

*Data Scale vs. Quality* — the ablation results in Table 2 offer a nuanced view of the training dynamics:

- **Quality drives Topological Validity.** Comparing Table 2(b) and (c): the model trained on the noisy 2M dataset (b) fails to learn loop closure (ρ_val = 67.25%) because it overfits to the *coordinate misalignment* and topological errors inherent in the raw screenshot data. In contrast, the pixel-aligned Stage 2 data (c) explicitly teaches the model the physical constraint of "watertightness," boosting the validity to 85.10%.
- **Scale drives Visual Generalization.** However, high-quality data alone reaches a performance ceiling. Comparing Table 2(c) and (a): adding Stage 1 yields a substantial 0.10 gain in IoU_ext (0.76 → 0.86) and further improves validity to 90.20%. This indicates that Stage 1 acts as *structural grounding*: it exposes the model to a vast diversity of wall textures and layout structures, enabling it to "recognize" walls robustly in complex scenes. Stage 2 then refines this robust perception into topologically valid, pixel-precise vectors.

**The Leap with GRPO.** Finally, the comparison between Table 2(a) and (d) highlights the limitations of SFT. While SFT achieves decent performance (ρ_val = 90.20%), it operates via probabilistic imitation; optimizing token likelihood does not strictly penalize small geometric drifts that break topology.

Table 2(d) shows that GRPO overcomes this by introducing *geometric enforcement*. By directly optimizing non-differentiable rewards (R_val, R_ext and R_int), GRPO forces the model to transition from simply "mimicking" valid floorplans to actively satisfying hard physical constraints. This results in a significant leap: a **+5.9% boost in validity** and a **+0.07 surge in Ext-IoU**, confirming that RL is the decisive factor for achieving engineering-grade precision.

**Data Scaling Laws.** Figure 6 illustrates the trajectory of model performance as the training data volume increases from 30% to 100%. We observe a distinct log–linear improvement in geometric metrics, yielding two critical insights:

- **Unsaturated Capacity:** The performance curve shows no sign of plateauing even at 2M samples. This trend suggests that the pixels-to-sequence paradigm has sufficient capacity to absorb far more architectural patterns, and that current performance is likely limited by data scale rather than model architecture.
- **Benefit of Structural Diversity:** Since our dataset is constructed via structure-aware clustering rather than random sampling, increasing data volume effectively introduces more long-tail topological variants rather than mere redundancy. This confirms that scaling diverse data is a direct path to improving geometric generalization.

**Format Selection: Code vs. JSON.** We investigated the optimal sequence representation by comparing a Python-DSL against our JSON schema. To ensure a fair comparison, the Python variant also utilized keyword arguments (e.g., `Wall(width=10, ...)`) to maintain semantic explicitness.

**Table 3: Format Comparison.** JSON outperforms Python despite having a longer sequence length. This can be attributed to the model's stronger pre-training alignment with JSON syntax.

| Format | Len. ↓ | ρ_val (%) | IoU_ext | IoU_room | F1_room | F1_op |
|---|---|---|---|---|---|---|
| Python Code | 2038.4 | 88.15 | 0.8555 | 0.8050 | 0.8079 | 0.6407 |
| JSON (Ours) | 3095.2 | 90.20 | 0.8567 | 0.8521 | 0.8140 | 0.7073 |

*Pre-training Alignment outweighs Token Efficiency.* As shown in Table 3, the Python format is significantly more compact (~2,000 tokens) than JSON (~3,000 tokens). Since both formats utilize keyword arguments, the performance gap cannot be attributed to semantic ambiguity.

Instead, we identify pre-training bias as the decisive factor. Foundation models like Qwen2.5-VL are heavily pre-trained on web-scale data, where JSON is the de facto standard for structured data interchange. Consequently, the model possesses a strong inductive bias toward JSON syntax constraints. In contrast, our specific Python DSL, while syntactically valid, represents a rare distribution in the pre-training corpus. This makes the model less stable when generating long Python sequences, leading to lower validity (ρ_val) compared to the "native-feeling" JSON format.

### 5.4 Qualitative Results

We present qualitative examples to visually substantiate the quantitative metrics reported in Table 1.

**Robustness to Noise and Complexity.** Figure 7 demonstrates the model's capability to distill structural logic from noisy raster inputs. Despite the presence of interfering elements like furniture, dimension lines, and watermarks, FLOORPLANVLM accurately grounds visual patterns to geometric primitives. Notably, the model generalizes well to non-Manhattan topologies, precisely parsing the slanted walls (Col. 2) and curved boundaries (Col. 5) that typically confound traditional rule-based heuristics.

*(Figure 7: six input/rendered-output floorplan pairs across diverse architectural styles, showing accurate reconstruction of slanted walls, curved balconies, and complex non-Manhattan geometries with strict topological connectivity — outputs are fully parametric vector graphs, not raster segmentation masks.)*

**SFT vs. GRPO: Precision beyond Probability.** Figure 8 highlights the critical role of Reinforcement Learning in achieving engineering-grade precision. While SFT provides a strong initialization, it operates on token likelihood, which does not necessarily correlate with pixel-perfect alignment.

- **Topological Closure (Row a):** SFT effectively captures the global shape but often fails at local corner connectivity, leaving "hanging" wall endpoints, because token-level likelihood objectives do not explicitly penalize small coordinate drifts that break topology. GRPO resolves this by integrating the binary validity reward (R_val), effectively forcing the model to "snap" endpoints together to form watertight polygons.
- **Curvature Refinement (Row b):** In curved regions, SFT often correctly predicts the presence of an arc but fails to estimate the exact curvature parameter κ, producing a curve that "looks" roughly correct but deviates from the underlying pixel footprint. GRPO corrects this by directly optimizing the IoU reward, forcing the continuous parameter κ to tightly fit the visual boundary.
- **Structural Integrity (Row c):** SFT struggles with ambiguous internal structures, leading to geometric hallucinations where internal walls are either missed or incorrectly positioned. By incorporating the validity-gated reward (R_int), GRPO effectively suppresses these false positives, ensuring that every generated wall is strictly grounded in image evidence.

*(Figure 8: Input / SFT / GRPO / Zoom-In comparison across three failure-case rows — (a) topological gaps at wall junctions, (b) curvature mismatch, (c) structural hallucination of internal walls — showing GRPO's corrections in each case.)*

In summary, while SFT learns the *syntax* of floorplans, GRPO is essential for enforcing the *physical constraints* and *parametric accuracy* required for downstream architectural applications.

## 6 Conclusion

In this work, we present FLOORPLANVLM, a framework that reformulates floorplan vectorization from a traditional detection-assembly pipeline into an end-to-end image-conditioned sequence generation task. By leveraging the semantic reasoning power of large Vision-Language Models, our approach directly outputs structured, render-ready JSON, streamlining the workflow for architectural design.

Our ablation studies reveal two critical insights for engineering-grade generation:

1. **Scale drives perception:** large-scale structural grounding on industrial data—despite inherent coordinate misalignment—is indispensable for establishing a generalized visual foundation, enabling the model to recognize diverse topologies beyond simple layouts.
2. **RL enforces geometric logic:** while SFT mimics data distribution, it struggles with pixel-perfect precision. Integrating GRPO bridges this gap, transforming probabilistic token generation into a process that actively satisfies hard geometric constraints (e.g., watertight loop closure).

Evaluated on our newly established FPBENCH-2K, FLOORPLANVLM achieves strong performance, particularly on complex non-Manhattan geometries, demonstrating robust topological reasoning for vector graphics generation.

### Limitations and Future Work

While FLOORPLANVLM demonstrates strong performance, we acknowledge limitations that point towards future research directions:

- **Inference Latency:** The autoregressive generation of long JSON sequences (averaging ~3,000 tokens) using a 3B-parameter model incurs higher latency than traditional lightweight CNNs. Future engineering efforts will focus on model quantization and speculative decoding to enable real-time deployment on edge devices.
- **Discrete Precision Bottleneck:** Our strategy of quantizing coordinates to a fixed [0, 1024] integer grid balances training stability with accuracy, but it imposes a theoretical limit on precision compared to continuous floating-point regression. Exploring hybrid discrete-continuous heads could further enhance engineering-grade fidelity.
- **Towards Interactive Agents:** Currently, the model operates as a one-shot translator. Moving forward, we aim to extend this framework to support multi-turn editing, enabling designers to iteratively refine layouts via natural language (e.g., "Move this wall 0.5m to the right"), thereby unlocking the full potential of human-AI collaboration in architecture.

### Ethical Statement

We affirm that our research adheres to ethical guidelines regarding data privacy and usage. The FLOORPLAN-2M dataset originates from an industrial interior design platform, where all personally identifiable information (PII), including homeowner names and specific geospatial coordinates, has been rigorously anonymized and desensitized prior to processing.

Regarding broader societal impact, while FLOORPLANVLM automates the labor-intensive task of vectorization, it is designed as an assistive tool to augment, rather than replace, human expertise. By automating tedious tracing work, we aim to free architects and designers to focus on high-level creative decision-making. We are also committed to releasing our benchmark (FPBENCH-2K) to promote transparency and reproducibility in the community.

### Acknowledgments

We sincerely thank the architectural designers at Beike for their tremendous effort in manually annotating and verifying the high-fidelity floorplan dataset. We are also grateful to the Beike AI Infrastructure Team for providing the essential GPU resources. This research would not have been possible without the open-source community, particularly the Qwen team for the Qwen2.5-VL model.

## References

- Achiam et al., 2023. Josh Achiam, Steven Adler, Sandhini Agarwal, Lama Ahmad, Ilge Akkaya, Florencia Leoni Aleman, Diogo Almeida, Janko Altenschmidt, Sam Altman, Shyamal Anadkat, et al. GPT-4 technical report. *arXiv preprint arXiv:2303.08774*.
- Bai et al., 2025. Shuai Bai, Keqin Chen, Xuejing Liu, Jialin Wang, Wenbin Ge, Sibo Song, Kai Dang, Peng Wang, Shijie Wang, Jun Tang, et al. Qwen2.5-VL technical report. *arXiv preprint arXiv:2502.13923*.
- Chen et al., 2025. Zhiyuan Chen, Yuecong Min, Jie Zhang, Bei Yan, Jiahao Wang, Xiaozhen Wang, Shiguang Shan. A survey of multimodal hallucination evaluation and detection. *arXiv preprint arXiv:2507.19024*.
- Gupta and Upmanyu, 2024. Rajendra Gupta, Smriti Upmanyu. Advancements in learning-based techniques for automated floor plan analysis on raster images: A comparative study. *International Journal of Advanced Networking and Applications*, 16(3):6418–6427.
- Han et al., 2023. Yucheng Han, Chi Zhang, Xin Chen, Xu Yang, Zhibin Wang, Gang Yu, Bin Fu, Hanwang Zhang. ChartLlama: A multimodal LLM for chart understanding and generation. *arXiv preprint arXiv:2311.16483*.
- Kalervo et al., 2019. Ahti Kalervo, Juha Ylioinas, Markus Haikiö, Antti Karhu, Juho Kannala. CubiCasa5K: A dataset and an improved multi-task model for floorplan image analysis. *arXiv:1904.01920*.
- Li et al., 2025. Jiahao Li, Yusheng Luo, Yunzhong Lou, Xiangdong Zhou. ReCAD: Reinforcement learning enhanced parametric CAD model generation with vision-language models. *arXiv preprint arXiv:2512.06328*.
- Liu et al., 2024. Yuzhou Liu, Lingjie Zhu, Xiaodong Ma, Hanqiao Ye, Xiang Gao, Xianwei Zheng, Shuhan Shen. PolyRoom: Room-aware transformer for floorplan reconstruction. In *European Conference on Computer Vision*, pages 322–339. Springer.
- Müllner, 2011. Daniel Müllner. Modern hierarchical, agglomerative clustering algorithms. *arXiv preprint arXiv:1109.2378*.
- Ouyang et al., 2022. Long Ouyang, Jeffrey Wu, Xu Jiang, Diogo Almeida, Carroll Wainwright, Pamela Mishkin, Chong Zhang, Sandhini Agarwal, Katarina Slama, Alex Ray, et al. Training language models to follow instructions with human feedback. *Advances in Neural Information Processing Systems*, 35:27730–27744.
- Ouyang et al., 2025. Kun Ouyang, Yuanxin Liu, Haoning Wu, Yi Liu, Hao Zhou, Jie Zhou, Fandong Meng, Xu Sun. SpaceR: Reinforcing MLLMs in video spatial reasoning. *arXiv preprint arXiv:2504.01805*.
- Salah et al., 2025. Rnin Salah, Nora Géczy, Kitti Ajtayne Károlyfi. Architectural heritage digitization: A classification-driven semi-automated scan-to-hbim workflow. *Buildings*, 16(1):21.
- Schulman et al., 2017. John Schulman, Filip Wolski, Prafulla Dhariwal, Alec Radford, Oleg Klimov. Proximal policy optimization algorithms. *arXiv preprint arXiv:1707.06347*.
- Shao et al., 2024. Zhihong Shao, Peiyi Wang, Qihao Zhu, Runxin Xu, Junxiao Song, Xiao Bi, Haowei Zhang, Mingchuan Zhang, YK Li, Yang Wu, et al. DeepSeekMath: Pushing the limits of mathematical reasoning in open language models. *arXiv preprint arXiv:2402.03300*.
- Skrzypczak et al., 2022. Izabela Skrzypczak, Grzegorz Oleniacz, Agnieszka Lesniak, Krzysztof Zima, Maria Mrówczyńska, Jan K Kazak. Scan-to-BIM method in construction: Assessment of the 3D buildings model accuracy in terms inventory measurements. *Building Research & Information*, 50(8):859–880.
- Yue et al., 2023. Yuanwen Yue, Theodora Kontogianni, Konrad Schindler, Francis Engelmann. Connecting the dots: Floorplan reconstruction using two-level queries. In *IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*.
- Zhang et al., 2002. Dengsheng Zhang, Guojun Lu, et al. A comparative study of Fourier descriptors for shape representation and retrieval. In *Proc. 5th Asian Conference on Computer Vision*, page 35. Citeseer.
- Zhou et al., 2019. Yichao Zhou, Haozhi Qi, Yi Ma. End-to-end wireframe parsing. In *Proceedings of the IEEE/CVF International Conference on Computer Vision*, pages 962–971.
