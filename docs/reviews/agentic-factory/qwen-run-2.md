richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/guardkit/scripts$ docker logs -f vllm-agentic-factory
(APIServer pid=1) INFO 03-26 10:43:48 [utils.py:299] 
(APIServer pid=1) INFO 03-26 10:43:48 [utils.py:299]        █     █     █▄   ▄█
(APIServer pid=1) INFO 03-26 10:43:48 [utils.py:299]  ▄▄ ▄█ █     █     █ ▀▄▀ █  version 0.18.1rc1.dev147+g290809456
(APIServer pid=1) INFO 03-26 10:43:48 [utils.py:299]   █▄█▀ █     █     █     █  model   Qwen/Qwen3.5-35B-A3B-FP8
(APIServer pid=1) INFO 03-26 10:43:48 [utils.py:299]    ▀▀  ▀▀▀▀▀ ▀▀▀▀▀ ▀     ▀
(APIServer pid=1) INFO 03-26 10:43:48 [utils.py:299] 
(APIServer pid=1) INFO 03-26 10:43:48 [utils.py:233] non-default args: {'model_tag': 'Qwen/Qwen3.5-35B-A3B-FP8', 'enable_auto_tool_choice': True, 'tool_call_parser': 'qwen3_coder', 'host': '0.0.0.0', 'model': 'Qwen/Qwen3.5-35B-A3B-FP8', 'trust_remote_code': True, 'max_model_len': 262144, 'reasoning_parser': 'qwen3', 'gpu_memory_utilization': 0.8, 'enable_prefix_caching': True}
(APIServer pid=1) The argument `trust_remote_code` is to be used with Auto classes. It has no effect here and is ignored.
(APIServer pid=1) INFO 03-26 10:43:49 [model.py:541] Resolved architecture: Qwen3_5MoeForConditionalGeneration
(APIServer pid=1) INFO 03-26 10:43:49 [model.py:1653] Using max model len 262144
(APIServer pid=1) WARNING 03-26 10:43:50 [config.py:388] Mamba cache mode is set to 'align' for Qwen3_5MoeForConditionalGeneration by default when prefix caching is enabled
(APIServer pid=1) INFO 03-26 10:43:50 [config.py:408] Warning: Prefix caching in Mamba cache 'align' mode is currently enabled. Its support for Mamba layers is experimental. Please report any issues you may observe.
(APIServer pid=1) /usr/local/lib/python3.12/dist-packages/torch/cuda/__init__.py:435: UserWarning: 
(APIServer pid=1)     Found GPU0 NVIDIA GB10 which is of cuda capability 12.1.
(APIServer pid=1)     Minimum and Maximum cuda capability supported by this version of PyTorch is
(APIServer pid=1)     (8.0) - (12.0)
(APIServer pid=1)     
(APIServer pid=1)   queued_call()
(APIServer pid=1) INFO 03-26 10:43:50 [config.py:228] Setting attention block size to 1056 tokens to ensure that attention page size is >= mamba page size.
(APIServer pid=1) INFO 03-26 10:43:50 [config.py:259] Padding mamba page size by 0.76% to ensure that mamba page size and attention page size are exactly equal.
(APIServer pid=1) INFO 03-26 10:43:50 [vllm.py:769] Asynchronous scheduling is enabled.
(APIServer pid=1) INFO 03-26 10:43:50 [compilation.py:290] Enabled custom fusions: norm_quant, act_quant
(EngineCore pid=62) INFO 03-26 10:44:04 [core.py:105] Initializing a V1 LLM engine (v0.18.1rc1.dev147+g290809456) with config: model='Qwen/Qwen3.5-35B-A3B-FP8', speculative_config=None, tokenizer='Qwen/Qwen3.5-35B-A3B-FP8', skip_tokenizer_init=False, tokenizer_mode=auto, revision=None, tokenizer_revision=None, trust_remote_code=True, dtype=torch.bfloat16, max_seq_len=262144, download_dir=None, load_format=auto, tensor_parallel_size=1, pipeline_parallel_size=1, data_parallel_size=1, decode_context_parallel_size=1, dcp_comm_backend=ag_rs, disable_custom_all_reduce=False, quantization=fp8, enforce_eager=False, enable_return_routed_experts=False, kv_cache_dtype=auto, device_config=cuda, structured_outputs_config=StructuredOutputsConfig(backend='auto', disable_any_whitespace=False, disable_additional_properties=False, reasoning_parser='qwen3', reasoning_parser_plugin='', enable_in_reasoning=False), observability_config=ObservabilityConfig(show_hidden_metrics_for_version=None, otlp_traces_endpoint=None, collect_detailed_traces=None, kv_cache_metrics=False, kv_cache_metrics_sample=0.01, cudagraph_metrics=False, enable_layerwise_nvtx_tracing=False, enable_mfu_metrics=False, enable_mm_processor_stats=False, enable_logging_iteration_details=False), seed=0, served_model_name=Qwen/Qwen3.5-35B-A3B-FP8, enable_prefix_caching=True, enable_chunked_prefill=True, pooler_config=None, compilation_config={'mode': <CompilationMode.VLLM_COMPILE: 3>, 'debug_dump_path': None, 'cache_dir': '', 'compile_cache_save_format': 'binary', 'backend': 'inductor', 'custom_ops': ['+quant_fp8', 'none', '+quant_fp8'], 'splitting_ops': ['vllm::unified_attention', 'vllm::unified_attention_with_output', 'vllm::unified_mla_attention', 'vllm::unified_mla_attention_with_output', 'vllm::mamba_mixer2', 'vllm::mamba_mixer', 'vllm::short_conv', 'vllm::linear_attention', 'vllm::plamo2_mamba_mixer', 'vllm::gdn_attention_core', 'vllm::olmo_hybrid_gdn_full_forward', 'vllm::kda_attention', 'vllm::sparse_attn_indexer', 'vllm::rocm_aiter_sparse_attn_indexer', 'vllm::unified_kv_cache_update', 'vllm::unified_mla_kv_cache_update'], 'compile_mm_encoder': False, 'cudagraph_mm_encoder': False, 'encoder_cudagraph_token_budgets': [], 'encoder_cudagraph_max_images_per_batch': 0, 'compile_sizes': [], 'compile_ranges_endpoints': [2048], 'inductor_compile_config': {'enable_auto_functionalized_v2': False, 'size_asserts': False, 'alignment_asserts': False, 'scalar_asserts': False, 'combo_kernels': True, 'benchmark_combo_kernel': True}, 'inductor_passes': {}, 'cudagraph_mode': <CUDAGraphMode.FULL_AND_PIECEWISE: (2, 1)>, 'cudagraph_num_of_warmups': 1, 'cudagraph_capture_sizes': [1, 2, 4, 8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 152, 160, 168, 176, 184, 192, 200, 208, 216, 224, 232, 240, 248, 256, 272, 288, 304, 320, 336, 352, 368, 384, 400, 416, 432, 448, 464, 480, 496, 512], 'cudagraph_copy_inputs': False, 'cudagraph_specialize_lora': True, 'use_inductor_graph_partition': False, 'pass_config': {'fuse_norm_quant': True, 'fuse_act_quant': True, 'fuse_attn_quant': False, 'enable_sp': False, 'fuse_gemm_comms': False, 'fuse_allreduce_rms': False}, 'max_cudagraph_capture_size': 512, 'dynamic_shapes_config': {'type': <DynamicShapesType.BACKED: 'backed'>, 'evaluate_guards': False, 'assume_32_bit_indexing': False}, 'local_cache_dir': None, 'fast_moe_cold_start': True, 'static_all_moe_layers': []}
(EngineCore pid=62) /usr/local/lib/python3.12/dist-packages/torch/cuda/__init__.py:435: UserWarning: 
(EngineCore pid=62)     Found GPU0 NVIDIA GB10 which is of cuda capability 12.1.
(EngineCore pid=62)     Minimum and Maximum cuda capability supported by this version of PyTorch is
(EngineCore pid=62)     (8.0) - (12.0)
(EngineCore pid=62)     
(EngineCore pid=62)   queued_call()
(EngineCore pid=62) INFO 03-26 10:44:06 [parallel_state.py:1400] world_size=1 rank=0 local_rank=0 distributed_init_method=tcp://172.17.0.2:57101 backend=nccl
(EngineCore pid=62) INFO 03-26 10:44:06 [parallel_state.py:1716] rank 0 in world size 1 is assigned as DP rank 0, PP rank 0, PCP rank 0, TP rank 0, EP rank 0, EPLB rank N/A
(EngineCore pid=62) INFO 03-26 10:44:14 [gpu_model_runner.py:4723] Starting to load model Qwen/Qwen3.5-35B-A3B-FP8...
(EngineCore pid=62) INFO 03-26 10:44:14 [cuda.py:390] Using backend AttentionBackendEnum.FLASH_ATTN for vit attention
(EngineCore pid=62) INFO 03-26 10:44:14 [mm_encoder_attention.py:230] Using AttentionBackendEnum.FLASH_ATTN for MMEncoderAttention.
(EngineCore pid=62) INFO 03-26 10:44:14 [__init__.py:261] Selected CutlassFP8ScaledMMLinearKernel for Fp8LinearMethod
(EngineCore pid=62) INFO 03-26 10:44:14 [qwen3_next.py:198] Using Triton/FLA GDN prefill kernel
(EngineCore pid=62) INFO 03-26 10:44:15 [fp8.py:396] Using TRITON Fp8 MoE backend out of potential backends: ['AITER', 'FLASHINFER_TRTLLM', 'FLASHINFER_CUTLASS', 'DEEPGEMM', 'TRITON', 'MARLIN', 'BATCHED_DEEPGEMM', 'BATCHED_TRITON', 'XPU'].
(EngineCore pid=62) INFO 03-26 10:44:15 [cuda.py:334] Using FLASH_ATTN attention backend out of potential backends: ['FLASH_ATTN', 'FLASHINFER', 'TRITON_ATTN', 'FLEX_ATTENTION'].
(EngineCore pid=62) INFO 03-26 10:44:15 [flash_attn.py:596] Using FlashAttention version 2
(EngineCore pid=62) INFO 03-26 11:02:26 [weight_utils.py:581] Time spent downloading weights for Qwen/Qwen3.5-35B-A3B-FP8: 1089.140590 seconds
Loading safetensors checkpoint shards:   0% Completed | 0/14 [00:00<?, ?it/s]
Loading safetensors checkpoint shards:   7% Completed | 1/14 [00:04<00:56,  4.38s/it]
Loading safetensors checkpoint shards:  14% Completed | 2/14 [00:08<00:51,  4.32s/it]
Loading safetensors checkpoint shards:  21% Completed | 3/14 [00:12<00:44,  4.02s/it]
Loading safetensors checkpoint shards:  29% Completed | 4/14 [00:15<00:38,  3.81s/it]
Loading safetensors checkpoint shards:  36% Completed | 5/14 [00:19<00:33,  3.75s/it]
Loading safetensors checkpoint shards:  43% Completed | 6/14 [00:23<00:29,  3.71s/it]
Loading safetensors checkpoint shards:  50% Completed | 7/14 [00:26<00:25,  3.64s/it]
Loading safetensors checkpoint shards:  57% Completed | 8/14 [00:30<00:21,  3.61s/it]
Loading safetensors checkpoint shards:  64% Completed | 9/14 [00:51<00:45,  9.14s/it]
Loading safetensors checkpoint shards:  71% Completed | 10/14 [00:54<00:29,  7.40s/it]
Loading safetensors checkpoint shards:  79% Completed | 11/14 [00:58<00:18,  6.22s/it]
Loading safetensors checkpoint shards:  86% Completed | 12/14 [01:02<00:10,  5.44s/it]
Loading safetensors checkpoint shards:  93% Completed | 13/14 [01:19<00:09,  9.06s/it]
Loading safetensors checkpoint shards: 100% Completed | 14/14 [01:22<00:00,  7.27s/it]
Loading safetensors checkpoint shards: 100% Completed | 14/14 [01:22<00:00,  5.90s/it]
(EngineCore pid=62) 
(EngineCore pid=62) INFO 03-26 11:03:49 [default_loader.py:384] Loading weights took 82.71 seconds
(EngineCore pid=62) INFO 03-26 11:03:49 [fp8.py:560] Using MoEPrepareAndFinalizeNoDPEPModular
(EngineCore pid=62) INFO 03-26 11:03:49 [gpu_model_runner.py:4808] Model loading took 34.22 GiB memory and 1175.062959 seconds
(EngineCore pid=62) INFO 03-26 11:03:49 [gpu_model_runner.py:5744] Encoder cache will be initialized with a budget of 16384 tokens, and profiled with 1 image items of the maximum feature size.
(EngineCore pid=62) INFO 03-26 11:04:04 [backends.py:1051] Using cache directory: /root/.cache/vllm/torch_compile_cache/a8c79b8c5c/rank_0_0/backbone for vLLM's torch.compile
(EngineCore pid=62) INFO 03-26 11:04:04 [backends.py:1111] Dynamo bytecode transform time: 7.03 s
(EngineCore pid=62) [rank0]:W0326 11:04:11.434000 62 torch/_inductor/utils.py:1679] Not enough SMs to use max_autotune_gemm mode
(EngineCore pid=62) INFO 03-26 11:04:13 [backends.py:372] Cache the graph of compile range (1, 2048) for later use
(EngineCore pid=62) INFO 03-26 11:04:38 [backends.py:390] Compiling a graph for compile range (1, 2048) takes 33.22 s
(EngineCore pid=62) INFO 03-26 11:04:39 [decorators.py:640] saved AOT compiled function to /root/.cache/vllm/torch_compile_cache/torch_aot_compile/ca897b2010df8baf9e1f346d45c242c5297ca4a2e1d25d8e1c08c1329b0c447e/rank_0_0/model
(EngineCore pid=62) INFO 03-26 11:04:39 [monitor.py:48] torch.compile took 42.67 s in total
(EngineCore pid=62) /usr/local/lib/python3.12/dist-packages/vllm/model_executor/layers/fla/ops/utils.py:113: UserWarning: Input tensor shape suggests potential format mismatch: seq_len (16) < num_heads (32). This may indicate the inputs were passed in head-first format [B, H, T, ...] when head_first=False was specified. Please verify your input tensor format matches the expected shape [B, T, H, ...].
(EngineCore pid=62)   return fn(*contiguous_args, **contiguous_kwargs)
(EngineCore pid=62) WARNING 03-26 11:05:29 [fused_moe.py:1090] Using default MoE config. Performance might be sub-optimal! Config file not found at /usr/local/lib/python3.12/dist-packages/vllm/model_executor/layers/fused_moe/configs/E=256,N=512,device_name=NVIDIA_GB10,dtype=fp8_w8a8,block_shape=[128,128].json
(EngineCore pid=62) /usr/local/lib/python3.12/dist-packages/vllm/model_executor/layers/fla/ops/utils.py:113: UserWarning: Input tensor shape suggests potential format mismatch: seq_len (16) < num_heads (32). This may indicate the inputs were passed in head-first format [B, H, T, ...] when head_first=False was specified. Please verify your input tensor format matches the expected shape [B, T, H, ...].
(EngineCore pid=62)   return fn(*contiguous_args, **contiguous_kwargs)
(EngineCore pid=62) INFO 03-26 11:05:32 [monitor.py:76] Initial profiling/warmup run took 52.59 s
(EngineCore pid=62) INFO 03-26 11:05:36 [kv_cache_utils.py:829] Overriding num_gpu_blocks=0 with num_gpu_blocks_override=512
(EngineCore pid=62) INFO 03-26 11:05:37 [gpu_model_runner.py:5867] Profiling CUDA graph memory: PIECEWISE=51 (largest=512), FULL=35 (largest=256)
(EngineCore pid=62) INFO 03-26 11:06:09 [gpu_model_runner.py:5946] Estimated CUDA graph memory: 1.65 GiB total
(EngineCore pid=62) INFO 03-26 11:06:09 [gpu_worker.py:436] Available KV cache memory: 55.72 GiB
(EngineCore pid=62) INFO 03-26 11:06:09 [gpu_worker.py:470] In v0.19, CUDA graph memory profiling will be enabled by default (VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=1), which more accurately accounts for CUDA graph memory during KV cache allocation. To try it now, set VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=1 and increase --gpu-memory-utilization from 0.8000 to 0.8136 to maintain the same effective KV cache size.
(EngineCore pid=62) INFO 03-26 11:06:09 [kv_cache_utils.py:1319] GPU KV cache size: 729,696 tokens
(EngineCore pid=62) INFO 03-26 11:06:09 [kv_cache_utils.py:1324] Maximum concurrency for 262,144 tokens per request: 10.85x
(EngineCore pid=62) 2026-03-26 11:06:23,543 - INFO - autotuner.py:262 - flashinfer.jit: [Autotuner]: Autotuning process starts ...
(EngineCore pid=62) 2026-03-26 11:06:24,103 - INFO - autotuner.py:268 - flashinfer.jit: [Autotuner]: Autotuning process ends
Capturing CUDA graphs (mixed prefill-decode, PIECEWISE): 100%|██████████| 51/51 [00:07<00:00,  6.86it/s]
Capturing CUDA graphs (decode, FULL): 100%|██████████| 35/35 [00:03<00:00, 10.30it/s]
(EngineCore pid=62) INFO 03-26 11:06:38 [gpu_model_runner.py:6035] Graph capturing finished in 14 secs, took 0.04 GiB
(EngineCore pid=62) INFO 03-26 11:06:38 [gpu_worker.py:597] CUDA graph pool memory: 0.04 GiB (actual), 1.65 GiB (estimated), difference: 1.61 GiB (4316.2%).
(EngineCore pid=62) INFO 03-26 11:06:38 [core.py:283] init engine (profile, create kv cache, warmup model) took 168.54 seconds
(EngineCore pid=62) INFO 03-26 11:06:38 [vllm.py:769] Asynchronous scheduling is enabled.
(EngineCore pid=62) INFO 03-26 11:06:38 [compilation.py:290] Enabled custom fusions: norm_quant, act_quant
(APIServer pid=1) INFO 03-26 11:06:40 [api_server.py:590] Supported tasks: ['generate']
(APIServer pid=1) INFO 03-26 11:06:41 [parser_manager.py:202] "auto" tool choice has been enabled.
(APIServer pid=1) WARNING 03-26 11:06:41 [model.py:1412] Default vLLM sampling parameters have been overridden by the model's `generation_config.json`: `{'top_k': 20, 'top_p': 0.95}`. If this is not intended, please relaunch vLLM instance with `--generation-config vllm`.
(APIServer pid=1) INFO 03-26 11:06:47 [hf.py:314] Detected the chat template content format to be 'string'. You can set `--chat-template-content-format` to override this.
(APIServer pid=1) INFO 03-26 11:06:53 [base.py:217] Multi-modal warmup completed in 6.791s
(APIServer pid=1) INFO 03-26 11:06:54 [api_server.py:594] Starting vLLM server on http://0.0.0.0:8000
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:37] Available routes are:
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /openapi.json, Methods: GET, HEAD
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /docs, Methods: GET, HEAD
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /docs/oauth2-redirect, Methods: GET, HEAD
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /redoc, Methods: GET, HEAD
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /tokenize, Methods: POST
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /detokenize, Methods: POST
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /load, Methods: GET
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /version, Methods: GET
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /health, Methods: GET
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /metrics, Methods: GET
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /v1/models, Methods: GET
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /ping, Methods: GET
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /ping, Methods: POST
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /invocations, Methods: POST
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /v1/chat/completions, Methods: POST
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /v1/chat/completions/batch, Methods: POST
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /v1/responses, Methods: POST
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /v1/responses/{response_id}, Methods: GET
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /v1/responses/{response_id}/cancel, Methods: POST
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /v1/completions, Methods: POST
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /v1/messages, Methods: POST
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /v1/messages/count_tokens, Methods: POST
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /inference/v1/generate, Methods: POST
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /scale_elastic_ep, Methods: POST
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /is_scaling_elastic_ep, Methods: POST
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /v1/chat/completions/render, Methods: POST
(APIServer pid=1) INFO 03-26 11:06:54 [launcher.py:46] Route: /v1/completions/render, Methods: POST
(APIServer pid=1) INFO:     Started server process [1]
(APIServer pid=1) INFO:     Waiting for application startup.
(APIServer pid=1) INFO:     Application startup complete.