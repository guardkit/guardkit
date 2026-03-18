richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/guardkit/scripts$ docker logs -f vllm-graphiti

==========
== vLLM ==
==========

NVIDIA Release 26.01 (build 257596323)
vLLM Version 0.13.0+faa43dbf
Container image Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.

Various files include modifications (c) NVIDIA CORPORATION & AFFILIATES.  All rights reserved.

GOVERNING TERMS: The software and materials are governed by the NVIDIA Software License Agreement
(found at https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/)
and the Product-Specific Terms for NVIDIA AI Products
(found at https://www.nvidia.com/en-us/agreements/enterprise-software/product-specific-terms-for-ai-products/).

NOTE: CUDA Forward Compatibility mode ENABLED.
  Using CUDA 13.1 driver version 590.48.01 with kernel driver version 580.126.09.
  See https://docs.nvidia.com/deploy/cuda-compatibility/ for details.

/usr/local/lib/python3.12/dist-packages/torchvision/io/image.py:14: UserWarning: Failed to load image Python extension: 'Could not load this library: /usr/local/lib/python3.12/dist-packages/torchvision/image.so'If you don't plan on using image functionality from `torchvision.io`, you can ignore this warning. Otherwise, there might be something wrong with your environment. Did you have `libjpeg` or `libpng` installed before building `torchvision` from source?
  warn(
(APIServer pid=1) INFO 03-18 12:03:55 [api_server.py:1354] vLLM API server version 0.13.0+faa43dbf.nv26.01
(APIServer pid=1) INFO 03-18 12:03:55 [utils.py:253] non-default args: {'model_tag': 'Qwen/Qwen3-30B-A3B-FP8', 'host': '0.0.0.0', 'model': 'Qwen/Qwen3-30B-A3B-FP8', 'trust_remote_code': True, 'max_model_len': 32768, 'reasoning_parser': 'qwen3', 'gpu_memory_utilization': 0.3, 'kv_cache_dtype': 'fp8', 'enable_prefix_caching': True}
(APIServer pid=1) The argument `trust_remote_code` is to be used with Auto classes. It has no effect here and is ignored.
(APIServer pid=1) INFO 03-18 12:03:56 [model.py:514] Resolved architecture: Qwen3MoeForCausalLM
(APIServer pid=1) INFO 03-18 12:03:56 [model.py:1661] Using max model len 32768
(APIServer pid=1) /usr/local/lib/python3.12/dist-packages/torch/library.py:357: UserWarning: Warning only once for all operators,  other operators may also be overridden.
(APIServer pid=1)   Overriding a previously registered kernel for the same operator and the same dispatch key
(APIServer pid=1)   operator: flash_attn::_flash_attn_backward(Tensor dout, Tensor q, Tensor k, Tensor v, Tensor out, Tensor softmax_lse, Tensor(a6!)? dq, Tensor(a7!)? dk, Tensor(a8!)? dv, float dropout_p, float softmax_scale, bool causal, SymInt window_size_left, SymInt window_size_right, float softcap, Tensor? alibi_slopes, bool deterministic, Tensor? rng_state=None) -> Tensor
(APIServer pid=1)     registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926
(APIServer pid=1)   dispatch key: ADInplaceOrView
(APIServer pid=1)   previous kernel: no debug info
(APIServer pid=1)        new kernel: registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926 (Triggered internally at /opt/pytorch/pytorch/aten/src/ATen/core/dispatch/OperatorEntry.cpp:208.)
(APIServer pid=1)   self.m.impl(
(APIServer pid=1) INFO 03-18 12:03:56 [cache.py:205] Using fp8 data type to store kv cache. It reduces the GPU memory footprint and boosts the performance. Meanwhile, it may cause accuracy drop without a proper scaling factor.
(APIServer pid=1) INFO 03-18 12:03:56 [scheduler.py:230] Chunked prefill is enabled with max_num_batched_tokens=2048.
/usr/local/lib/python3.12/dist-packages/torchvision/io/image.py:14: UserWarning: Failed to load image Python extension: 'Could not load this library: /usr/local/lib/python3.12/dist-packages/torchvision/image.so'If you don't plan on using image functionality from `torchvision.io`, you can ignore this warning. Otherwise, there might be something wrong with your environment. Did you have `libjpeg` or `libpng` installed before building `torchvision` from source?
  warn(
/usr/local/lib/python3.12/dist-packages/torch/library.py:357: UserWarning: Warning only once for all operators,  other operators may also be overridden.
  Overriding a previously registered kernel for the same operator and the same dispatch key
  operator: flash_attn::_flash_attn_backward(Tensor dout, Tensor q, Tensor k, Tensor v, Tensor out, Tensor softmax_lse, Tensor(a6!)? dq, Tensor(a7!)? dk, Tensor(a8!)? dv, float dropout_p, float softmax_scale, bool causal, SymInt window_size_left, SymInt window_size_right, float softcap, Tensor? alibi_slopes, bool deterministic, Tensor? rng_state=None) -> Tensor
    registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926
  dispatch key: ADInplaceOrView
  previous kernel: no debug info
       new kernel: registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926 (Triggered internally at /opt/pytorch/pytorch/aten/src/ATen/core/dispatch/OperatorEntry.cpp:208.)
  self.m.impl(
(EngineCore_DP0 pid=143) INFO 03-18 12:04:00 [core.py:93] Initializing a V1 LLM engine (v0.13.0+faa43dbf.nv26.01) with config: model='Qwen/Qwen3-30B-A3B-FP8', speculative_config=None, tokenizer='Qwen/Qwen3-30B-A3B-FP8', skip_tokenizer_init=False, tokenizer_mode=auto, revision=None, tokenizer_revision=None, trust_remote_code=True, dtype=torch.bfloat16, max_seq_len=32768, download_dir=None, load_format=auto, tensor_parallel_size=1, pipeline_parallel_size=1, data_parallel_size=1, disable_custom_all_reduce=False, quantization=fp8, enforce_eager=False, kv_cache_dtype=fp8, device_config=cuda, structured_outputs_config=StructuredOutputsConfig(backend='auto', disable_fallback=False, disable_any_whitespace=False, disable_additional_properties=False, reasoning_parser='qwen3', reasoning_parser_plugin='', enable_in_reasoning=False), observability_config=ObservabilityConfig(show_hidden_metrics_for_version=None, otlp_traces_endpoint=None, collect_detailed_traces=None, kv_cache_metrics=False, kv_cache_metrics_sample=0.01, cudagraph_metrics=False, enable_layerwise_nvtx_tracing=False), seed=0, served_model_name=Qwen/Qwen3-30B-A3B-FP8, enable_prefix_caching=True, enable_chunked_prefill=True, pooler_config=None, compilation_config={'level': None, 'mode': <CompilationMode.VLLM_COMPILE: 3>, 'debug_dump_path': None, 'cache_dir': '', 'compile_cache_save_format': 'binary', 'backend': 'inductor', 'custom_ops': ['+quant_fp8', 'none', '+quant_fp8'], 'splitting_ops': ['vllm::unified_attention', 'vllm::unified_attention_with_output', 'vllm::unified_mla_attention', 'vllm::unified_mla_attention_with_output', 'vllm::mamba_mixer2', 'vllm::mamba_mixer', 'vllm::short_conv', 'vllm::linear_attention', 'vllm::plamo2_mamba_mixer', 'vllm::gdn_attention_core', 'vllm::kda_attention', 'vllm::sparse_attn_indexer'], 'compile_mm_encoder': False, 'compile_sizes': [], 'compile_ranges_split_points': [2048], 'inductor_compile_config': {'enable_auto_functionalized_v2': False, 'combo_kernels': True, 'benchmark_combo_kernel': True}, 'inductor_passes': {}, 'cudagraph_mode': <CUDAGraphMode.FULL_AND_PIECEWISE: (2, 1)>, 'cudagraph_num_of_warmups': 1, 'cudagraph_capture_sizes': [1, 2, 4, 8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 152, 160, 168, 176, 184, 192, 200, 208, 216, 224, 232, 240, 248, 256, 272, 288, 304, 320, 336, 352, 368, 384, 400, 416, 432, 448, 464, 480, 496, 512], 'cudagraph_copy_inputs': False, 'cudagraph_specialize_lora': True, 'use_inductor_graph_partition': False, 'pass_config': {'fuse_norm_quant': True, 'fuse_act_quant': True, 'fuse_attn_quant': False, 'eliminate_noops': True, 'enable_sp': False, 'fuse_gemm_comms': False, 'fuse_allreduce_rms': False}, 'max_cudagraph_capture_size': 512, 'dynamic_shapes_config': {'type': <DynamicShapesType.BACKED: 'backed'>, 'evaluate_guards': False}, 'local_cache_dir': None}
(EngineCore_DP0 pid=143) INFO 03-18 12:04:00 [parallel_state.py:1203] world_size=1 rank=0 local_rank=0 distributed_init_method=tcp://172.17.0.3:57153 backend=nccl
(EngineCore_DP0 pid=143) INFO 03-18 12:04:00 [parallel_state.py:1411] rank 0 in world size 1 is assigned as DP rank 0, PP rank 0, PCP rank 0, TP rank 0, EP rank 0
(EngineCore_DP0 pid=143) INFO 03-18 12:04:01 [gpu_model_runner.py:3562] Starting to load model Qwen/Qwen3-30B-A3B-FP8...
(EngineCore_DP0 pid=143) INFO 03-18 12:04:11 [cuda.py:351] Using FLASHINFER attention backend out of potential backends: ('FLASHINFER', 'TRITON_ATTN')
(EngineCore_DP0 pid=143) INFO 03-18 12:04:11 [layer.py:372] Enabled separate cuda stream for MoE shared_experts
(EngineCore_DP0 pid=143) WARNING 03-18 12:04:11 [fp8.py:186] DeepGEMM backend requested but not available.
(EngineCore_DP0 pid=143) INFO 03-18 12:04:11 [fp8.py:205] Using Triton backend for FP8 MoE
Loading safetensors checkpoint shards:   0% Completed | 0/7 [00:00<?, ?it/s]
Loading safetensors checkpoint shards:  14% Completed | 1/7 [00:27<02:47, 27.88s/it]
Loading safetensors checkpoint shards:  29% Completed | 2/7 [00:35<01:19, 15.89s/it]
Loading safetensors checkpoint shards:  43% Completed | 3/7 [01:03<01:25, 21.44s/it]
Loading safetensors checkpoint shards:  57% Completed | 4/7 [01:32<01:12, 24.28s/it]
Loading safetensors checkpoint shards:  71% Completed | 5/7 [02:00<00:51, 25.66s/it]
Loading safetensors checkpoint shards:  86% Completed | 6/7 [02:28<00:26, 26.58s/it]
Loading safetensors checkpoint shards: 100% Completed | 7/7 [02:50<00:00, 24.92s/it]
Loading safetensors checkpoint shards: 100% Completed | 7/7 [02:50<00:00, 24.29s/it]
(EngineCore_DP0 pid=143) 
(EngineCore_DP0 pid=143) INFO 03-18 12:07:03 [default_loader.py:308] Loading weights took 170.58 seconds
(EngineCore_DP0 pid=143) WARNING 03-18 12:07:03 [kv_cache.py:90] Checkpoint does not provide a q scaling factor. Setting it to k_scale. This only matters for FP8 Attention backends (flash-attn or flashinfer).
(EngineCore_DP0 pid=143) WARNING 03-18 12:07:03 [kv_cache.py:104] Using KV cache scaling factor 1.0 for fp8_e4m3. If this is unintended, verify that k/v_scale scaling factors are properly set in the checkpoint.
(EngineCore_DP0 pid=143) WARNING 03-18 12:07:03 [kv_cache.py:143] Using uncalibrated q_scale 1.0 and/or prob_scale 1.0 with fp8 attention. This may cause accuracy issues. Please make sure q/prob scaling factors are available in the fp8 checkpoint.
(EngineCore_DP0 pid=143) INFO 03-18 12:07:04 [gpu_model_runner.py:3659] Model loading took 29.0435 GiB memory and 182.555009 seconds
(EngineCore_DP0 pid=143) INFO 03-18 12:07:10 [backends.py:643] Using cache directory: /root/.cache/vllm/torch_compile_cache/ae460ddb27/rank_0_0/backbone for vLLM's torch.compile
(EngineCore_DP0 pid=143) INFO 03-18 12:07:10 [backends.py:703] Dynamo bytecode transform time: 6.08 s
(EngineCore_DP0 pid=143) INFO 03-18 12:07:18 [backends.py:261] Cache the graph of compile range (1, 2048) for later use
(EngineCore_DP0 pid=143) [rank0]:W0318 12:07:19.520000 143 torch/_inductor/utils.py:1703] Not enough SMs to use max_autotune_gemm mode
(EngineCore_DP0 pid=143) WARNING 03-18 12:07:21 [fused_moe.py:888] Using default MoE config. Performance might be sub-optimal! Config file not found at /usr/local/lib/python3.12/dist-packages/vllm/model_executor/layers/fused_moe/configs/E=128,N=768,device_name=NVIDIA_GB10,dtype=fp8_w8a8,block_shape=[128,128].json
(EngineCore_DP0 pid=143) INFO 03-18 12:08:38 [backends.py:278] Compiling a graph for compile range (1, 2048) takes 86.12 s
(EngineCore_DP0 pid=143) INFO 03-18 12:08:38 [monitor.py:34] torch.compile takes 92.20 s in total
(EngineCore_DP0 pid=143) INFO 03-18 12:08:41 [gpu_worker.py:375] Available KV cache memory: 4.04 GiB
(EngineCore_DP0 pid=143) INFO 03-18 12:08:41 [kv_cache_utils.py:1291] GPU KV cache size: 88,176 tokens
(EngineCore_DP0 pid=143) INFO 03-18 12:08:41 [kv_cache_utils.py:1296] Maximum concurrency for 32,768 tokens per request: 2.69x
(EngineCore_DP0 pid=143) 2026-03-18 12:08:41,650 - INFO - autotuner.py:256 - flashinfer.jit: [Autotuner]: Autotuning process starts ...
(EngineCore_DP0 pid=143) INFO 03-18 12:08:41 [kernel_warmup.py:65] Warming up FlashInfer attention.
(EngineCore_DP0 pid=143) 2026-03-18 12:08:41,680 - INFO - autotuner.py:262 - flashinfer.jit: [Autotuner]: Autotuning process ends
Capturing CUDA graphs (mixed prefill-decode, PIECEWISE): 100%|██████████| 51/51 [00:03<00:00, 13.29it/s]
Capturing CUDA graphs (decode, FULL): 100%|██████████| 35/35 [00:01<00:00, 18.98it/s]
(EngineCore_DP0 pid=143) INFO 03-18 12:09:02 [gpu_model_runner.py:4587] Graph capturing finished in 6 secs, took 1.28 GiB
(EngineCore_DP0 pid=143) INFO 03-18 12:09:02 [core.py:259] init engine (profile, create kv cache, warmup model) took 118.60 seconds
(APIServer pid=1) INFO 03-18 12:09:04 [api_server.py:1102] Supported tasks: ['generate']
(APIServer pid=1) WARNING 03-18 12:09:04 [model.py:1487] Default sampling parameters have been overridden by the model's Hugging Face generation config recommended from the model creator. If this is not intended, please relaunch vLLM instance with `--generation-config vllm`.
(APIServer pid=1) INFO 03-18 12:09:04 [serving_responses.py:201] Using default chat sampling params from model: {'temperature': 0.6, 'top_k': 20, 'top_p': 0.95}
(APIServer pid=1) INFO 03-18 12:09:04 [serving_chat.py:137] Using default chat sampling params from model: {'temperature': 0.6, 'top_k': 20, 'top_p': 0.95}
(APIServer pid=1) INFO 03-18 12:09:04 [serving_completion.py:77] Using default completion sampling params from model: {'temperature': 0.6, 'top_k': 20, 'top_p': 0.95}
(APIServer pid=1) INFO 03-18 12:09:05 [serving_chat.py:137] Using default chat sampling params from model: {'temperature': 0.6, 'top_k': 20, 'top_p': 0.95}
(APIServer pid=1) INFO 03-18 12:09:05 [api_server.py:1428] Starting vLLM API server 0 on http://0.0.0.0:8000
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:38] Available routes are:
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /openapi.json, Methods: GET, HEAD
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /docs, Methods: GET, HEAD
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /docs/oauth2-redirect, Methods: GET, HEAD
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /redoc, Methods: GET, HEAD
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /scale_elastic_ep, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /is_scaling_elastic_ep, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /tokenize, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /detokenize, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /inference/v1/generate, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /pause, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /resume, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /is_paused, Methods: GET
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /metrics, Methods: GET
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /health, Methods: GET
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /load, Methods: GET
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /v1/models, Methods: GET
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /version, Methods: GET
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /v1/responses, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /v1/responses/{response_id}, Methods: GET
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /v1/responses/{response_id}/cancel, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /v1/messages, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /v1/chat/completions, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /v1/completions, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /v1/audio/transcriptions, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /v1/audio/translations, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /ping, Methods: GET
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /ping, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /invocations, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /classify, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /v1/embeddings, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /score, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /v1/score, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /rerank, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /v1/rerank, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /v2/rerank, Methods: POST
(APIServer pid=1) INFO 03-18 12:09:05 [launcher.py:46] Route: /pooling, Methods: POST
(APIServer pid=1) INFO:     Started server process [1]
(APIServer pid=1) INFO:     Waiting for application startup.
(APIServer pid=1) INFO:     Application startup complete.
