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
(APIServer pid=1) INFO 03-18 13:32:14 [api_server.py:1354] vLLM API server version 0.13.0+faa43dbf.nv26.01
(APIServer pid=1) INFO 03-18 13:32:14 [utils.py:253] non-default args: {'model_tag': 'neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic', 'host': '0.0.0.0', 'model': 'neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic', 'max_model_len': 32768, 'gpu_memory_utilization': 0.15, 'kv_cache_dtype': 'fp8', 'enable_prefix_caching': True, 'structured_outputs_config': StructuredOutputsConfig(backend='xgrammar', disable_fallback=False, disable_any_whitespace=False, disable_additional_properties=False, reasoning_parser='', reasoning_parser_plugin='', enable_in_reasoning=False)}
(APIServer pid=1) /usr/local/lib/python3.12/dist-packages/torch/library.py:357: UserWarning: Warning only once for all operators,  other operators may also be overridden.
(APIServer pid=1)   Overriding a previously registered kernel for the same operator and the same dispatch key
(APIServer pid=1)   operator: flash_attn::_flash_attn_backward(Tensor dout, Tensor q, Tensor k, Tensor v, Tensor out, Tensor softmax_lse, Tensor(a6!)? dq, Tensor(a7!)? dk, Tensor(a8!)? dv, float dropout_p, float softmax_scale, bool causal, SymInt window_size_left, SymInt window_size_right, float softcap, Tensor? alibi_slopes, bool deterministic, Tensor? rng_state=None) -> Tensor
(APIServer pid=1)     registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926
(APIServer pid=1)   dispatch key: ADInplaceOrView
(APIServer pid=1)   previous kernel: no debug info
(APIServer pid=1)        new kernel: registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926 (Triggered internally at /opt/pytorch/pytorch/aten/src/ATen/core/dispatch/OperatorEntry.cpp:208.)
(APIServer pid=1)   self.m.impl(
(APIServer pid=1) INFO 03-18 13:32:20 [model.py:514] Resolved architecture: Qwen2ForCausalLM
(APIServer pid=1) INFO 03-18 13:32:20 [model.py:1661] Using max model len 32768
(APIServer pid=1) INFO 03-18 13:32:20 [cache.py:205] Using fp8 data type to store kv cache. It reduces the GPU memory footprint and boosts the performance. Meanwhile, it may cause accuracy drop without a proper scaling factor.
(APIServer pid=1) INFO 03-18 13:32:20 [scheduler.py:230] Chunked prefill is enabled with max_num_batched_tokens=2048.
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
(EngineCore_DP0 pid=191) INFO 03-18 13:32:29 [core.py:93] Initializing a V1 LLM engine (v0.13.0+faa43dbf.nv26.01) with config: model='neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic', speculative_config=None, tokenizer='neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic', skip_tokenizer_init=False, tokenizer_mode=auto, revision=None, tokenizer_revision=None, trust_remote_code=False, dtype=torch.bfloat16, max_seq_len=32768, download_dir=None, load_format=auto, tensor_parallel_size=1, pipeline_parallel_size=1, data_parallel_size=1, disable_custom_all_reduce=False, quantization=compressed-tensors, enforce_eager=False, kv_cache_dtype=fp8, device_config=cuda, structured_outputs_config=StructuredOutputsConfig(backend='xgrammar', disable_fallback=False, disable_any_whitespace=False, disable_additional_properties=False, reasoning_parser='', reasoning_parser_plugin='', enable_in_reasoning=False), observability_config=ObservabilityConfig(show_hidden_metrics_for_version=None, otlp_traces_endpoint=None, collect_detailed_traces=None, kv_cache_metrics=False, kv_cache_metrics_sample=0.01, cudagraph_metrics=False, enable_layerwise_nvtx_tracing=False), seed=0, served_model_name=neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic, enable_prefix_caching=True, enable_chunked_prefill=True, pooler_config=None, compilation_config={'level': None, 'mode': <CompilationMode.VLLM_COMPILE: 3>, 'debug_dump_path': None, 'cache_dir': '', 'compile_cache_save_format': 'binary', 'backend': 'inductor', 'custom_ops': ['none'], 'splitting_ops': ['vllm::unified_attention', 'vllm::unified_attention_with_output', 'vllm::unified_mla_attention', 'vllm::unified_mla_attention_with_output', 'vllm::mamba_mixer2', 'vllm::mamba_mixer', 'vllm::short_conv', 'vllm::linear_attention', 'vllm::plamo2_mamba_mixer', 'vllm::gdn_attention_core', 'vllm::kda_attention', 'vllm::sparse_attn_indexer'], 'compile_mm_encoder': False, 'compile_sizes': [], 'compile_ranges_split_points': [2048], 'inductor_compile_config': {'enable_auto_functionalized_v2': False, 'combo_kernels': True, 'benchmark_combo_kernel': True}, 'inductor_passes': {}, 'cudagraph_mode': <CUDAGraphMode.FULL_AND_PIECEWISE: (2, 1)>, 'cudagraph_num_of_warmups': 1, 'cudagraph_capture_sizes': [1, 2, 4, 8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 152, 160, 168, 176, 184, 192, 200, 208, 216, 224, 232, 240, 248, 256, 272, 288, 304, 320, 336, 352, 368, 384, 400, 416, 432, 448, 464, 480, 496, 512], 'cudagraph_copy_inputs': False, 'cudagraph_specialize_lora': True, 'use_inductor_graph_partition': False, 'pass_config': {'fuse_norm_quant': False, 'fuse_act_quant': False, 'fuse_attn_quant': False, 'eliminate_noops': True, 'enable_sp': False, 'fuse_gemm_comms': False, 'fuse_allreduce_rms': False}, 'max_cudagraph_capture_size': 512, 'dynamic_shapes_config': {'type': <DynamicShapesType.BACKED: 'backed'>, 'evaluate_guards': False}, 'local_cache_dir': None}
(EngineCore_DP0 pid=191) INFO 03-18 13:32:30 [parallel_state.py:1203] world_size=1 rank=0 local_rank=0 distributed_init_method=tcp://172.17.0.3:51777 backend=nccl
(EngineCore_DP0 pid=191) INFO 03-18 13:32:30 [parallel_state.py:1411] rank 0 in world size 1 is assigned as DP rank 0, PP rank 0, PCP rank 0, TP rank 0, EP rank 0
(EngineCore_DP0 pid=191) INFO 03-18 13:32:30 [gpu_model_runner.py:3562] Starting to load model neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic...
(EngineCore_DP0 pid=191) INFO 03-18 13:32:40 [cuda.py:351] Using FLASHINFER attention backend out of potential backends: ('FLASHINFER', 'TRITON_ATTN')
(EngineCore_DP0 pid=191) INFO 03-18 13:39:38 [weight_utils.py:487] Time spent downloading weights for neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic: 417.087123 seconds
Loading safetensors checkpoint shards:   0% Completed | 0/4 [00:00<?, ?it/s]
Loading safetensors checkpoint shards:  25% Completed | 1/4 [00:08<00:25,  8.52s/it]
Loading safetensors checkpoint shards:  50% Completed | 2/4 [00:28<00:31, 15.51s/it]
Loading safetensors checkpoint shards:  75% Completed | 3/4 [00:55<00:20, 20.63s/it]
Loading safetensors checkpoint shards: 100% Completed | 4/4 [01:23<00:00, 23.40s/it]
Loading safetensors checkpoint shards: 100% Completed | 4/4 [01:23<00:00, 20.82s/it]
(EngineCore_DP0 pid=191) 
(EngineCore_DP0 pid=191) INFO 03-18 13:41:03 [default_loader.py:308] Loading weights took 83.82 seconds
(EngineCore_DP0 pid=191) WARNING 03-18 13:41:03 [kv_cache.py:90] Checkpoint does not provide a q scaling factor. Setting it to k_scale. This only matters for FP8 Attention backends (flash-attn or flashinfer).
(EngineCore_DP0 pid=191) WARNING 03-18 13:41:03 [kv_cache.py:104] Using KV cache scaling factor 1.0 for fp8_e4m3. If this is unintended, verify that k/v_scale scaling factors are properly set in the checkpoint.
(EngineCore_DP0 pid=191) WARNING 03-18 13:41:03 [kv_cache.py:143] Using uncalibrated q_scale 1.0 and/or prob_scale 1.0 with fp8 attention. This may cause accuracy issues. Please make sure q/prob scaling factors are available in the fp8 checkpoint.
(EngineCore_DP0 pid=191) INFO 03-18 13:41:03 [gpu_model_runner.py:3659] Model loading took 15.2227 GiB memory and 512.925670 seconds
(EngineCore_DP0 pid=191) INFO 03-18 13:41:09 [backends.py:643] Using cache directory: /root/.cache/vllm/torch_compile_cache/4aae4d336d/rank_0_0/backbone for vLLM's torch.compile
(EngineCore_DP0 pid=191) INFO 03-18 13:41:09 [backends.py:703] Dynamo bytecode transform time: 5.73 s
(EngineCore_DP0 pid=191) INFO 03-18 13:41:14 [backends.py:261] Cache the graph of compile range (1, 2048) for later use
(EngineCore_DP0 pid=191) INFO 03-18 13:41:26 [backends.py:278] Compiling a graph for compile range (1, 2048) takes 15.02 s
(EngineCore_DP0 pid=191) INFO 03-18 13:41:26 [monitor.py:34] torch.compile takes 20.75 s in total
(EngineCore_DP0 pid=191) INFO 03-18 13:41:29 [gpu_worker.py:375] Available KV cache memory: -1.30 GiB
(EngineCore_DP0 pid=191) ERROR 03-18 13:41:29 [core.py:866] EngineCore failed to start.
(EngineCore_DP0 pid=191) ERROR 03-18 13:41:29 [core.py:866] Traceback (most recent call last):
(EngineCore_DP0 pid=191) ERROR 03-18 13:41:29 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 857, in run_engine_core
(EngineCore_DP0 pid=191) ERROR 03-18 13:41:29 [core.py:866]     engine_core = EngineCoreProc(*args, **kwargs)
(EngineCore_DP0 pid=191) ERROR 03-18 13:41:29 [core.py:866]                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=191) ERROR 03-18 13:41:29 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 637, in __init__
(EngineCore_DP0 pid=191) ERROR 03-18 13:41:29 [core.py:866]     super().__init__(
(EngineCore_DP0 pid=191) ERROR 03-18 13:41:29 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 109, in __init__
(EngineCore_DP0 pid=191) ERROR 03-18 13:41:29 [core.py:866]     num_gpu_blocks, num_cpu_blocks, kv_cache_config = self._initialize_kv_caches(
(EngineCore_DP0 pid=191) ERROR 03-18 13:41:29 [core.py:866]                                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=191) ERROR 03-18 13:41:29 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 248, in _initialize_kv_caches
(EngineCore_DP0 pid=191) ERROR 03-18 13:41:29 [core.py:866]     kv_cache_configs = get_kv_cache_configs(
(EngineCore_DP0 pid=191) ERROR 03-18 13:41:29 [core.py:866]                        ^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=191) ERROR 03-18 13:41:29 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/core/kv_cache_utils.py", line 1340, in get_kv_cache_configs
(EngineCore_DP0 pid=191) Process EngineCore_DP0:
(EngineCore_DP0 pid=191) Traceback (most recent call last):
(EngineCore_DP0 pid=191)   File "/usr/lib/python3.12/multiprocessing/process.py", line 314, in _bootstrap
(EngineCore_DP0 pid=191)     self.run()
(EngineCore_DP0 pid=191)   File "/usr/lib/python3.12/multiprocessing/process.py", line 108, in run
(EngineCore_DP0 pid=191)     self._target(*self._args, **self._kwargs)
(EngineCore_DP0 pid=191)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 870, in run_engine_core
(EngineCore_DP0 pid=191)     raise e
(EngineCore_DP0 pid=191)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 857, in run_engine_core
(EngineCore_DP0 pid=191)     engine_core = EngineCoreProc(*args, **kwargs)
(EngineCore_DP0 pid=191)                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=191)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 637, in __init__
(EngineCore_DP0 pid=191)     super().__init__(
(EngineCore_DP0 pid=191)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 109, in __init__
(EngineCore_DP0 pid=191)     num_gpu_blocks, num_cpu_blocks, kv_cache_config = self._initialize_kv_caches(
(EngineCore_DP0 pid=191)                                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=191)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 248, in _initialize_kv_caches
(EngineCore_DP0 pid=191)     kv_cache_configs = get_kv_cache_configs(
(EngineCore_DP0 pid=191)                        ^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=191)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/core/kv_cache_utils.py", line 1340, in get_kv_cache_configs
(EngineCore_DP0 pid=191)     check_enough_kv_cache_memory(
(EngineCore_DP0 pid=191)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/core/kv_cache_utils.py", line 687, in check_enough_kv_cache_memory
(EngineCore_DP0 pid=191)     raise ValueError(
(EngineCore_DP0 pid=191) ValueError: No available memory for the cache blocks. Try increasing `gpu_memory_utilization` when initializing the engine. See https://docs.vllm.ai/en/latest/configuration/conserving_memory/ for more details.
(EngineCore_DP0 pid=191) ERROR 03-18 13:41:29 [core.py:866]     check_enough_kv_cache_memory(
(EngineCore_DP0 pid=191) ERROR 03-18 13:41:29 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/core/kv_cache_utils.py", line 687, in check_enough_kv_cache_memory
(EngineCore_DP0 pid=191) ERROR 03-18 13:41:29 [core.py:866]     raise ValueError(
(EngineCore_DP0 pid=191) ERROR 03-18 13:41:29 [core.py:866] ValueError: No available memory for the cache blocks. Try increasing `gpu_memory_utilization` when initializing the engine. See https://docs.vllm.ai/en/latest/configuration/conserving_memory/ for more details.
[rank0]:[W318 13:41:30.265537082 ProcessGroupNCCL.cpp:1565] Warning: WARNING: destroy_process_group() was not called before program exit, which can leak resources. For more info, please see https://pytorch.org/docs/stable/distributed.html#shutdown (function operator())
(APIServer pid=1) Traceback (most recent call last):
(APIServer pid=1)   File "/usr/local/bin/vllm", line 7, in <module>
(APIServer pid=1)     sys.exit(main())
(APIServer pid=1)              ^^^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/vllm/entrypoints/cli/main.py", line 73, in main
(APIServer pid=1)     args.dispatch_function(args)
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/vllm/entrypoints/cli/serve.py", line 60, in cmd
(APIServer pid=1)     uvloop.run(run_server(args))
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/uvloop/__init__.py", line 96, in run
(APIServer pid=1)     return __asyncio.run(
(APIServer pid=1)            ^^^^^^^^^^^^^^
(APIServer pid=1)   File "/usr/lib/python3.12/asyncio/runners.py", line 194, in run
(APIServer pid=1)     return runner.run(main)
(APIServer pid=1)            ^^^^^^^^^^^^^^^^
(APIServer pid=1)   File "/usr/lib/python3.12/asyncio/runners.py", line 118, in run
(APIServer pid=1)     return self._loop.run_until_complete(task)
(APIServer pid=1)            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(APIServer pid=1)   File "uvloop/loop.pyx", line 1518, in uvloop.loop.Loop.run_until_complete
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/uvloop/__init__.py", line 48, in wrapper
(APIServer pid=1)     return await main
(APIServer pid=1)            ^^^^^^^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/vllm/entrypoints/openai/api_server.py", line 1401, in run_server
(APIServer pid=1)     await run_server_worker(listen_address, sock, args, **uvicorn_kwargs)
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/vllm/entrypoints/openai/api_server.py", line 1420, in run_server_worker
(APIServer pid=1)     async with build_async_engine_client(
(APIServer pid=1)   File "/usr/lib/python3.12/contextlib.py", line 210, in __aenter__
(APIServer pid=1)     return await anext(self.gen)
(APIServer pid=1)            ^^^^^^^^^^^^^^^^^^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/vllm/entrypoints/openai/api_server.py", line 173, in build_async_engine_client
(APIServer pid=1)     async with build_async_engine_client_from_engine_args(
(APIServer pid=1)   File "/usr/lib/python3.12/contextlib.py", line 210, in __aenter__
(APIServer pid=1)     return await anext(self.gen)
(APIServer pid=1)            ^^^^^^^^^^^^^^^^^^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/vllm/entrypoints/openai/api_server.py", line 215, in build_async_engine_client_from_engine_args
(APIServer pid=1)     async_llm = AsyncLLM.from_vllm_config(
(APIServer pid=1)                 ^^^^^^^^^^^^^^^^^^^^^^^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/async_llm.py", line 215, in from_vllm_config
(APIServer pid=1)     return cls(
(APIServer pid=1)            ^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/async_llm.py", line 134, in __init__
(APIServer pid=1)     self.engine_core = EngineCoreClient.make_async_mp_client(
(APIServer pid=1)                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core_client.py", line 121, in make_async_mp_client
(APIServer pid=1)     return AsyncMPClient(*client_args)
(APIServer pid=1)            ^^^^^^^^^^^^^^^^^^^^^^^^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core_client.py", line 820, in __init__
(APIServer pid=1)     super().__init__(
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core_client.py", line 477, in __init__
(APIServer pid=1)     with launch_core_engines(vllm_config, executor_class, log_stats) as (
(APIServer pid=1)   File "/usr/lib/python3.12/contextlib.py", line 144, in __exit__
(APIServer pid=1)     next(self.gen)
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/utils.py", line 903, in launch_core_engines
(APIServer pid=1)     wait_for_engine_startup(
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/utils.py", line 960, in wait_for_engine_startup
(APIServer pid=1)     raise RuntimeError(
(APIServer pid=1) RuntimeError: Engine core initialization failed. See root cause above. Failed core proc(s): {}
richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/guardkit/scripts$ 
