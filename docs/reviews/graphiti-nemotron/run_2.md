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
(APIServer pid=1) INFO 03-18 06:54:54 [api_server.py:1354] vLLM API server version 0.13.0+faa43dbf.nv26.01
(APIServer pid=1) INFO 03-18 06:54:54 [utils.py:253] non-default args: {'model_tag': 'nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8', 'host': '0.0.0.0', 'model': 'nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8', 'trust_remote_code': True, 'max_model_len': 8192, 'gpu_memory_utilization': 0.15, 'kv_cache_dtype': 'fp8'}
(APIServer pid=1) The argument `trust_remote_code` is to be used with Auto classes. It has no effect here and is ignored.
(APIServer pid=1) /usr/local/lib/python3.12/dist-packages/torch/library.py:357: UserWarning: Warning only once for all operators,  other operators may also be overridden.
(APIServer pid=1)   Overriding a previously registered kernel for the same operator and the same dispatch key
(APIServer pid=1)   operator: flash_attn::_flash_attn_backward(Tensor dout, Tensor q, Tensor k, Tensor v, Tensor out, Tensor softmax_lse, Tensor(a6!)? dq, Tensor(a7!)? dk, Tensor(a8!)? dv, float dropout_p, float softmax_scale, bool causal, SymInt window_size_left, SymInt window_size_right, float softcap, Tensor? alibi_slopes, bool deterministic, Tensor? rng_state=None) -> Tensor
(APIServer pid=1)     registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926
(APIServer pid=1)   dispatch key: ADInplaceOrView
(APIServer pid=1)   previous kernel: no debug info
(APIServer pid=1)        new kernel: registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926 (Triggered internally at /opt/pytorch/pytorch/aten/src/ATen/core/dispatch/OperatorEntry.cpp:208.)
(APIServer pid=1)   self.m.impl(
(APIServer pid=1) INFO 03-18 06:54:59 [model.py:514] Resolved architecture: NemotronHForCausalLM
(APIServer pid=1) INFO 03-18 06:54:59 [model.py:1661] Using max model len 8192
(APIServer pid=1) INFO 03-18 06:54:59 [cache.py:205] Using fp8 data type to store kv cache. It reduces the GPU memory footprint and boosts the performance. Meanwhile, it may cause accuracy drop without a proper scaling factor.
(APIServer pid=1) INFO 03-18 06:54:59 [scheduler.py:230] Chunked prefill is enabled with max_num_batched_tokens=2048.
(APIServer pid=1) INFO 03-18 06:54:59 [config.py:506] Updating mamba_ssm_cache_dtype to 'float16' for NemotronH model
(APIServer pid=1) INFO 03-18 06:54:59 [config.py:312] Disabling cascade attention since it is not supported for hybrid models.
(APIServer pid=1) INFO 03-18 06:54:59 [config.py:439] Setting attention block size to 992 tokens to ensure that attention page size is >= mamba page size.
(APIServer pid=1) INFO 03-18 06:54:59 [config.py:463] Padding mamba page size by 0.35% to ensure that mamba page size and attention page size are exactly equal.
(APIServer pid=1) WARNING 03-18 06:54:59 [modelopt.py:313] Detected ModelOpt fp8 checkpoint. Please note that the format is experimental and could change.
(APIServer pid=1) The following generation flags are not valid and may be ignored: ['top_p']. Set `TRANSFORMERS_VERBOSITY=info` for more details.
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
(EngineCore_DP0 pid=165) INFO 03-18 06:55:03 [core.py:93] Initializing a V1 LLM engine (v0.13.0+faa43dbf.nv26.01) with config: model='nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8', speculative_config=None, tokenizer='nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8', skip_tokenizer_init=False, tokenizer_mode=auto, revision=None, tokenizer_revision=None, trust_remote_code=True, dtype=torch.bfloat16, max_seq_len=8192, download_dir=None, load_format=auto, tensor_parallel_size=1, pipeline_parallel_size=1, data_parallel_size=1, disable_custom_all_reduce=False, quantization=modelopt, enforce_eager=False, kv_cache_dtype=fp8, device_config=cuda, structured_outputs_config=StructuredOutputsConfig(backend='auto', disable_fallback=False, disable_any_whitespace=False, disable_additional_properties=False, reasoning_parser='', reasoning_parser_plugin='', enable_in_reasoning=False), observability_config=ObservabilityConfig(show_hidden_metrics_for_version=None, otlp_traces_endpoint=None, collect_detailed_traces=None, kv_cache_metrics=False, kv_cache_metrics_sample=0.01, cudagraph_metrics=False, enable_layerwise_nvtx_tracing=False), seed=0, served_model_name=nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8, enable_prefix_caching=False, enable_chunked_prefill=True, pooler_config=None, compilation_config={'level': None, 'mode': <CompilationMode.VLLM_COMPILE: 3>, 'debug_dump_path': None, 'cache_dir': '', 'compile_cache_save_format': 'binary', 'backend': 'inductor', 'custom_ops': ['none'], 'splitting_ops': ['vllm::unified_attention', 'vllm::unified_attention_with_output', 'vllm::unified_mla_attention', 'vllm::unified_mla_attention_with_output', 'vllm::mamba_mixer2', 'vllm::mamba_mixer', 'vllm::short_conv', 'vllm::linear_attention', 'vllm::plamo2_mamba_mixer', 'vllm::gdn_attention_core', 'vllm::kda_attention', 'vllm::sparse_attn_indexer'], 'compile_mm_encoder': False, 'compile_sizes': [], 'compile_ranges_split_points': [2048], 'inductor_compile_config': {'enable_auto_functionalized_v2': False, 'combo_kernels': True, 'benchmark_combo_kernel': True}, 'inductor_passes': {}, 'cudagraph_mode': <CUDAGraphMode.FULL_AND_PIECEWISE: (2, 1)>, 'cudagraph_num_of_warmups': 1, 'cudagraph_capture_sizes': [1, 2, 4, 8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 152, 160, 168, 176, 184, 192, 200, 208, 216, 224, 232, 240, 248, 256, 272, 288, 304, 320, 336, 352, 368, 384, 400, 416, 432, 448, 464, 480, 496, 512], 'cudagraph_copy_inputs': False, 'cudagraph_specialize_lora': True, 'use_inductor_graph_partition': False, 'pass_config': {'fuse_norm_quant': False, 'fuse_act_quant': False, 'fuse_attn_quant': False, 'eliminate_noops': True, 'enable_sp': False, 'fuse_gemm_comms': False, 'fuse_allreduce_rms': False}, 'max_cudagraph_capture_size': 512, 'dynamic_shapes_config': {'type': <DynamicShapesType.BACKED: 'backed'>, 'evaluate_guards': False}, 'local_cache_dir': None}
(EngineCore_DP0 pid=165) INFO 03-18 06:55:04 [parallel_state.py:1203] world_size=1 rank=0 local_rank=0 distributed_init_method=tcp://172.17.0.3:35599 backend=nccl
(EngineCore_DP0 pid=165) INFO 03-18 06:55:04 [parallel_state.py:1411] rank 0 in world size 1 is assigned as DP rank 0, PP rank 0, PCP rank 0, TP rank 0, EP rank 0
(EngineCore_DP0 pid=165) INFO 03-18 06:55:04 [gpu_model_runner.py:3562] Starting to load model nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8...
(EngineCore_DP0 pid=165) INFO 03-18 06:55:15 [cuda.py:351] Using FLASHINFER attention backend out of potential backends: ('FLASHINFER', 'TRITON_ATTN')
Loading safetensors checkpoint shards:   0% Completed | 0/2 [00:00<?, ?it/s]
Loading safetensors checkpoint shards:  50% Completed | 1/2 [00:08<00:08,  8.96s/it]
Loading safetensors checkpoint shards: 100% Completed | 2/2 [00:32<00:00, 17.38s/it]
Loading safetensors checkpoint shards: 100% Completed | 2/2 [00:32<00:00, 16.11s/it]
(EngineCore_DP0 pid=165) 
(EngineCore_DP0 pid=165) INFO 03-18 06:55:49 [default_loader.py:308] Loading weights took 32.77 seconds
(EngineCore_DP0 pid=165) INFO 03-18 06:55:50 [gpu_model_runner.py:3659] Model loading took 4.9054 GiB memory and 44.986674 seconds
(EngineCore_DP0 pid=165) INFO 03-18 06:55:51 [backends.py:643] Using cache directory: /root/.cache/vllm/torch_compile_cache/564663590f/rank_0_0/backbone for vLLM's torch.compile
(EngineCore_DP0 pid=165) INFO 03-18 06:55:51 [backends.py:703] Dynamo bytecode transform time: 1.81 s
(EngineCore_DP0 pid=165) INFO 03-18 06:55:53 [backends.py:261] Cache the graph of compile range (1, 2048) for later use
(EngineCore_DP0 pid=165) [rank0]:W0318 06:57:13.573000 165 torch/_inductor/utils.py:1703] Not enough SMs to use max_autotune_gemm mode
(EngineCore_DP0 pid=165) INFO 03-18 06:57:23 [backends.py:278] Compiling a graph for compile range (1, 2048) takes 90.39 s
(EngineCore_DP0 pid=165) INFO 03-18 06:57:23 [monitor.py:34] torch.compile takes 92.20 s in total
(EngineCore_DP0 pid=165) INFO 03-18 06:57:25 [gpu_worker.py:375] Available KV cache memory: 11.15 GiB
(EngineCore_DP0 pid=165) WARNING 03-18 06:57:25 [kv_cache_utils.py:1033] Add 3 padding layers, may waste at most 14.29% KV cache memory
(EngineCore_DP0 pid=165) INFO 03-18 06:57:25 [kv_cache_utils.py:1291] GPU KV cache size: 208,320 tokens
(EngineCore_DP0 pid=165) INFO 03-18 06:57:25 [kv_cache_utils.py:1296] Maximum concurrency for 8,192 tokens per request: 98.20x
(EngineCore_DP0 pid=165) 2026-03-18 06:57:26,008 - INFO - autotuner.py:256 - flashinfer.jit: [Autotuner]: Autotuning process starts ...
(EngineCore_DP0 pid=165) 2026-03-18 06:57:33,420 - INFO - autotuner.py:262 - flashinfer.jit: [Autotuner]: Autotuning process ends
Capturing CUDA graphs (mixed prefill-decode, PIECEWISE): 100%|██████████| 51/51 [00:04<00:00, 10.66it/s]
Capturing CUDA graphs (decode, FULL): 100%|██████████| 35/35 [00:18<00:00,  1.90it/s]
(EngineCore_DP0 pid=165) INFO 03-18 06:57:57 [gpu_model_runner.py:4587] Graph capturing finished in 24 secs, took 1.00 GiB
(EngineCore_DP0 pid=165) INFO 03-18 06:57:57 [core.py:259] init engine (profile, create kv cache, warmup model) took 127.33 seconds
(APIServer pid=1) INFO 03-18 06:57:58 [api_server.py:1102] Supported tasks: ['generate']
(APIServer pid=1) WARNING 03-18 06:57:58 [model.py:1487] Default sampling parameters have been overridden by the model's Hugging Face generation config recommended from the model creator. If this is not intended, please relaunch vLLM instance with `--generation-config vllm`.
(APIServer pid=1) INFO 03-18 06:57:58 [serving_responses.py:201] Using default chat sampling params from model: {'top_p': 0.95}
(APIServer pid=1) INFO 03-18 06:57:59 [serving_chat.py:137] Using default chat sampling params from model: {'top_p': 0.95}
(APIServer pid=1) INFO 03-18 06:57:59 [serving_completion.py:77] Using default completion sampling params from model: {'top_p': 0.95}
(APIServer pid=1) INFO 03-18 06:57:59 [serving_chat.py:137] Using default chat sampling params from model: {'top_p': 0.95}
(APIServer pid=1) INFO 03-18 06:57:59 [api_server.py:1428] Starting vLLM API server 0 on http://0.0.0.0:8000
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:38] Available routes are:
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /openapi.json, Methods: GET, HEAD
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /docs, Methods: GET, HEAD
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /docs/oauth2-redirect, Methods: GET, HEAD
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /redoc, Methods: GET, HEAD
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /scale_elastic_ep, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /is_scaling_elastic_ep, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /tokenize, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /detokenize, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /inference/v1/generate, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /pause, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /resume, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /is_paused, Methods: GET
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /metrics, Methods: GET
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /health, Methods: GET
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /load, Methods: GET
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /v1/models, Methods: GET
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /version, Methods: GET
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /v1/responses, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /v1/responses/{response_id}, Methods: GET
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /v1/responses/{response_id}/cancel, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /v1/messages, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /v1/chat/completions, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /v1/completions, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /v1/audio/transcriptions, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /v1/audio/translations, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /ping, Methods: GET
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /ping, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /invocations, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /classify, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /v1/embeddings, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /score, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /v1/score, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /rerank, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /v1/rerank, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /v2/rerank, Methods: POST
(APIServer pid=1) INFO 03-18 06:57:59 [launcher.py:46] Route: /pooling, Methods: POST
(APIServer pid=1) INFO:     Started server process [1]
(APIServer pid=1) INFO:     Waiting for application startup.
(APIServer pid=1) INFO:     Application startup complete.

