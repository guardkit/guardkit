richardwoollcott@promaxgb10-41b1:~$ docker logs -f vllm-embedding

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
(APIServer pid=1) INFO 02-28 16:40:45 [api_server.py:1354] vLLM API server version 0.13.0+faa43dbf.nv26.01
(APIServer pid=1) INFO 02-28 16:40:45 [utils.py:253] non-default args: {'model_tag': 'nomic-ai/nomic-embed-text-v1.5', 'host': '0.0.0.0', 'port': 8001, 'model': 'nomic-ai/nomic-embed-text-v1.5', 'runner': 'pooling', 'trust_remote_code': True, 'gpu_memory_utilization': 0.15}
(APIServer pid=1) The argument `trust_remote_code` is to be used with Auto classes. It has no effect here and is ignored.
(APIServer pid=1) WARNING 02-28 16:40:46 [utils.py:91] NomicBertConfig contains a deprecated attribute name 'rotary_emb_base'. Please use the preferred attribute name 'rope_theta' instead.
(APIServer pid=1) WARNING 02-28 16:40:46 [utils.py:91] NomicBertConfig contains a deprecated attribute name 'rotary_emb_fraction'. Please use the preferred attribute name 'partial_rotary_factor' instead.
(APIServer pid=1) INFO 02-28 16:40:46 [config.py:864] Found sentence-transformers tokenize configuration.
(APIServer pid=1) /usr/local/lib/python3.12/dist-packages/torch/library.py:357: UserWarning: Warning only once for all operators,  other operators may also be overridden.
(APIServer pid=1)   Overriding a previously registered kernel for the same operator and the same dispatch key
(APIServer pid=1)   operator: flash_attn::_flash_attn_backward(Tensor dout, Tensor q, Tensor k, Tensor v, Tensor out, Tensor softmax_lse, Tensor(a6!)? dq, Tensor(a7!)? dk, Tensor(a8!)? dv, float dropout_p, float softmax_scale, bool causal, SymInt window_size_left, SymInt window_size_right, float softcap, Tensor? alibi_slopes, bool deterministic, Tensor? rng_state=None) -> Tensor
(APIServer pid=1)     registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926
(APIServer pid=1)   dispatch key: ADInplaceOrView
(APIServer pid=1)   previous kernel: no debug info
(APIServer pid=1)        new kernel: registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926 (Triggered internally at /opt/pytorch/pytorch/aten/src/ATen/core/dispatch/OperatorEntry.cpp:208.)
(APIServer pid=1)   self.m.impl(
(APIServer pid=1) INFO 02-28 16:40:50 [model.py:827] Resolved `--convert auto` to `--convert embed`. Pass the value explicitly to silence this message.
(APIServer pid=1) INFO 02-28 16:40:50 [model.py:514] Resolved architecture: NomicBertModel
(APIServer pid=1) INFO 02-28 16:40:50 [config.py:752] Found sentence-transformers modules configuration.
(APIServer pid=1) INFO 02-28 16:40:50 [config.py:783] Found pooling configuration.
(APIServer pid=1) INFO 02-28 16:40:50 [model.py:2002] Downcasting torch.float32 to torch.float16.
(APIServer pid=1) INFO 02-28 16:40:50 [model.py:1661] Using max model len 8192
(APIServer pid=1) INFO 02-28 16:40:50 [model.py:1661] Using max model len 2048
(APIServer pid=1) WARNING 02-28 16:40:50 [config.py:146] Nomic context extension is disabled. Changing max_model_len from 8192 to 2048. To enable context extension, see: https://github.com/vllm-project/vllm/tree/main/examples/offline_inference/context_extension.html
(APIServer pid=1) WARNING 02-28 16:40:50 [vllm.py:701] Pooling models do not support full cudagraphs. Overriding cudagraph_mode to PIECEWISE.
/usr/local/lib/python3.12/dist-packages/torchvision/io/image.py:14: UserWarning: Failed to load image Python extension: 'Could not load this library: /usr/local/lib/python3.12/dist-packages/torchvision/image.so'If you don't plan on using image functionality from `torchvision.io`, you can ignore this warning. Otherwise, there might be something wrong with your environment. Did you have `libjpeg` or `libpng` installed before building `torchvision` from source?
  warn(
(EngineCore_DP0 pid=167) INFO 02-28 16:40:54 [core.py:93] Initializing a V1 LLM engine (v0.13.0+faa43dbf.nv26.01) with config: model='nomic-ai/nomic-embed-text-v1.5', speculative_config=None, tokenizer='nomic-ai/nomic-embed-text-v1.5', skip_tokenizer_init=False, tokenizer_mode=auto, revision=None, tokenizer_revision=None, trust_remote_code=True, dtype=torch.float16, max_seq_len=2048, download_dir=None, load_format=auto, tensor_parallel_size=1, pipeline_parallel_size=1, data_parallel_size=1, disable_custom_all_reduce=False, quantization=None, enforce_eager=False, kv_cache_dtype=auto, device_config=cuda, structured_outputs_config=StructuredOutputsConfig(backend='auto', disable_fallback=False, disable_any_whitespace=False, disable_additional_properties=False, reasoning_parser='', reasoning_parser_plugin='', enable_in_reasoning=False), observability_config=ObservabilityConfig(show_hidden_metrics_for_version=None, otlp_traces_endpoint=None, collect_detailed_traces=None, kv_cache_metrics=False, kv_cache_metrics_sample=0.01, cudagraph_metrics=False, enable_layerwise_nvtx_tracing=False), seed=0, served_model_name=nomic-ai/nomic-embed-text-v1.5, enable_prefix_caching=False, enable_chunked_prefill=False, pooler_config=PoolerConfig(pooling_type='MEAN', normalize=False, dimensions=None, enable_chunked_processing=None, max_embed_len=None, softmax=None, activation=None, use_activation=None, logit_bias=None, step_tag_id=None, returned_token_ids=None), compilation_config={'level': None, 'mode': <CompilationMode.VLLM_COMPILE: 3>, 'debug_dump_path': None, 'cache_dir': '', 'compile_cache_save_format': 'binary', 'backend': 'inductor', 'custom_ops': ['none'], 'splitting_ops': ['vllm::unified_attention', 'vllm::unified_attention_with_output', 'vllm::unified_mla_attention', 'vllm::unified_mla_attention_with_output', 'vllm::mamba_mixer2', 'vllm::mamba_mixer', 'vllm::short_conv', 'vllm::linear_attention', 'vllm::plamo2_mamba_mixer', 'vllm::gdn_attention_core', 'vllm::kda_attention', 'vllm::sparse_attn_indexer'], 'compile_mm_encoder': False, 'compile_sizes': [], 'compile_ranges_split_points': [8192], 'inductor_compile_config': {'enable_auto_functionalized_v2': False, 'combo_kernels': True, 'benchmark_combo_kernel': True}, 'inductor_passes': {}, 'cudagraph_mode': <CUDAGraphMode.PIECEWISE: 1>, 'cudagraph_num_of_warmups': 1, 'cudagraph_capture_sizes': [1, 2, 4, 8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 152, 160, 168, 176, 184, 192, 200, 208, 216, 224, 232, 240, 248, 256, 272, 288, 304, 320, 336, 352, 368, 384, 400, 416, 432, 448, 464, 480, 496, 512], 'cudagraph_copy_inputs': False, 'cudagraph_specialize_lora': True, 'use_inductor_graph_partition': False, 'pass_config': {'fuse_norm_quant': False, 'fuse_act_quant': False, 'fuse_attn_quant': False, 'eliminate_noops': True, 'enable_sp': False, 'fuse_gemm_comms': False, 'fuse_allreduce_rms': False}, 'max_cudagraph_capture_size': 512, 'dynamic_shapes_config': {'type': <DynamicShapesType.BACKED: 'backed'>, 'evaluate_guards': False}, 'local_cache_dir': None}
(EngineCore_DP0 pid=167) /usr/local/lib/python3.12/dist-packages/torch/library.py:357: UserWarning: Warning only once for all operators,  other operators may also be overridden.
(EngineCore_DP0 pid=167)   Overriding a previously registered kernel for the same operator and the same dispatch key
(EngineCore_DP0 pid=167)   operator: flash_attn::_flash_attn_backward(Tensor dout, Tensor q, Tensor k, Tensor v, Tensor out, Tensor softmax_lse, Tensor(a6!)? dq, Tensor(a7!)? dk, Tensor(a8!)? dv, float dropout_p, float softmax_scale, bool causal, SymInt window_size_left, SymInt window_size_right, float softcap, Tensor? alibi_slopes, bool deterministic, Tensor? rng_state=None) -> Tensor
(EngineCore_DP0 pid=167)     registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926
(EngineCore_DP0 pid=167)   dispatch key: ADInplaceOrView
(EngineCore_DP0 pid=167)   previous kernel: no debug info
(EngineCore_DP0 pid=167)        new kernel: registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926 (Triggered internally at /opt/pytorch/pytorch/aten/src/ATen/core/dispatch/OperatorEntry.cpp:208.)
(EngineCore_DP0 pid=167)   self.m.impl(
(EngineCore_DP0 pid=167) INFO 02-28 16:40:54 [parallel_state.py:1203] world_size=1 rank=0 local_rank=0 distributed_init_method=tcp://172.17.0.2:35867 backend=nccl
(EngineCore_DP0 pid=167) INFO 02-28 16:40:54 [parallel_state.py:1411] rank 0 in world size 1 is assigned as DP rank 0, PP rank 0, PCP rank 0, TP rank 0, EP rank 0
(EngineCore_DP0 pid=167) INFO 02-28 16:40:55 [gpu_model_runner.py:3562] Starting to load model nomic-ai/nomic-embed-text-v1.5...
(EngineCore_DP0 pid=167) INFO 02-28 16:41:05 [cuda.py:351] Using FLASH_ATTN attention backend out of potential backends: ('FLASH_ATTN', 'FLEX_ATTENTION')
(EngineCore_DP0 pid=167) INFO 02-28 16:41:06 [weight_utils.py:527] No model.safetensors.index.json found in remote.
Loading safetensors checkpoint shards:   0% Completed | 0/1 [00:00<?, ?it/s]
Loading safetensors checkpoint shards: 100% Completed | 1/1 [00:00<00:00,  5.48it/s]
Loading safetensors checkpoint shards: 100% Completed | 1/1 [00:00<00:00,  5.48it/s]
(EngineCore_DP0 pid=167) 
(EngineCore_DP0 pid=167) INFO 02-28 16:41:06 [default_loader.py:308] Loading weights took 0.20 seconds
(EngineCore_DP0 pid=167) INFO 02-28 16:41:06 [gpu_model_runner.py:3659] Model loading took 0.2551 GiB memory and 11.141736 seconds
(EngineCore_DP0 pid=167) 2026-02-28 16:41:06,689 - INFO - autotuner.py:256 - flashinfer.jit: [Autotuner]: Autotuning process starts ...
(EngineCore_DP0 pid=167) INFO 02-28 16:41:08 [backends.py:643] Using cache directory: /root/.cache/vllm/torch_compile_cache/d66b5d3476/rank_0_0/backbone for vLLM's torch.compile
(EngineCore_DP0 pid=167) INFO 02-28 16:41:08 [backends.py:703] Dynamo bytecode transform time: 1.99 s
(EngineCore_DP0 pid=167) [rank0]:W0228 16:41:09.602000 167 torch/_inductor/utils.py:1703] Not enough SMs to use max_autotune_gemm mode
(EngineCore_DP0 pid=167) INFO 02-28 16:41:11 [backends.py:261] Cache the graph of compile range (1, 8192) for later use
(EngineCore_DP0 pid=167) INFO 02-28 16:41:14 [backends.py:278] Compiling a graph for compile range (1, 8192) takes 5.06 s
(EngineCore_DP0 pid=167) INFO 02-28 16:41:14 [monitor.py:34] torch.compile takes 7.05 s in total
(EngineCore_DP0 pid=167) 2026-02-28 16:41:14,326 - INFO - autotuner.py:262 - flashinfer.jit: [Autotuner]: Autotuning process ends
Capturing CUDA graphs (mixed prefill-decode, PIECEWISE): 100%|██████████| 51/51 [00:00<00:00, 160.00it/s]
(EngineCore_DP0 pid=167) INFO 02-28 16:41:15 [gpu_model_runner.py:4587] Graph capturing finished in 1 secs, took 0.01 GiB
(EngineCore_DP0 pid=167) INFO 02-28 16:41:15 [core.py:259] init engine (profile, create kv cache, warmup model) took 8.35 seconds
(EngineCore_DP0 pid=167) INFO 02-28 16:41:15 [config.py:864] Found sentence-transformers tokenize configuration.
(APIServer pid=1) INFO 02-28 16:41:15 [api_server.py:1102] Supported tasks: ['token_embed', 'embed']
(APIServer pid=1) INFO 02-28 16:41:15 [api_server.py:1428] Starting vLLM API server 0 on http://0.0.0.0:8001
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:38] Available routes are:
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /openapi.json, Methods: GET, HEAD
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /docs, Methods: GET, HEAD
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /docs/oauth2-redirect, Methods: GET, HEAD
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /redoc, Methods: GET, HEAD
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /scale_elastic_ep, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /is_scaling_elastic_ep, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /tokenize, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /detokenize, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /inference/v1/generate, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /pause, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /resume, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /is_paused, Methods: GET
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /metrics, Methods: GET
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /health, Methods: GET
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /load, Methods: GET
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /v1/models, Methods: GET
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /version, Methods: GET
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /v1/responses, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /v1/responses/{response_id}, Methods: GET
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /v1/responses/{response_id}/cancel, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /v1/messages, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /v1/chat/completions, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /v1/completions, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /v1/audio/transcriptions, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /v1/audio/translations, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /ping, Methods: GET
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /ping, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /invocations, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /classify, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /v1/embeddings, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /score, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /v1/score, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /rerank, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /v1/rerank, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /v2/rerank, Methods: POST
(APIServer pid=1) INFO 02-28 16:41:15 [launcher.py:46] Route: /pooling, Methods: POST
(APIServer pid=1) INFO:     Started server process [1]
(APIServer pid=1) INFO:     Waiting for application startup.
(APIServer pid=1) INFO:     Application startup complete.
(APIServer pid=1) INFO:     172.17.0.1:41774 - "GET /health HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:41778 - "GET /models HTTP/1.1" 404 Not Found
(APIServer pid=1) INFO:     172.17.0.1:53074 - "POST /v1/embeddings HTTP/1.1" 404 Not Found

