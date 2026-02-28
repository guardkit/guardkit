richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/guardkit$ ./scripts/vllm-embed.sh
Model: nomic-embed-text-v1.5 (137M, ~274MB, 8192 context)

========================================
  VLLM Embedding Server — GB10
========================================
  Model:    nomic-ai/nomic-embed-text-v1.5
  Port:     8001
  GPU util: 0.15
========================================

267e5bc48ec41cce22d33dec2941108db8b466014feec06f7c04c52fb70d39e3
Container started: vllm-embedding

Waiting for model to load...
  Logs:   docker logs -f vllm-embedding
  Health: curl http://localhost:8001/health
  Models: curl http://localhost:8001/v1/models

Test embeddings:
  curl http://localhost:8001/v1/embeddings \
    -H 'Content-Type: application/json' \
    -d '{"model": "nomic-embed-text-v1.5", "input": "Hello world"}'
richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/guardkit$ docker logs -f vllm-embedding

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
(APIServer pid=1) INFO 02-28 16:12:03 [api_server.py:1354] vLLM API server version 0.13.0+faa43dbf.nv26.01
(APIServer pid=1) INFO 02-28 16:12:03 [utils.py:253] non-default args: {'model_tag': 'nomic-ai/nomic-embed-text-v1.5', 'host': '0.0.0.0', 'port': 8001, 'model': 'nomic-ai/nomic-embed-text-v1.5', 'runner': 'pooling', 'trust_remote_code': True, 'gpu_memory_utilization': 0.15}
(APIServer pid=1) The argument `trust_remote_code` is to be used with Auto classes. It has no effect here and is ignored.
(APIServer pid=1) WARNING 02-28 16:12:05 [utils.py:91] NomicBertConfig contains a deprecated attribute name 'rotary_emb_base'. Please use the preferred attribute name 'rope_theta' instead.
(APIServer pid=1) WARNING 02-28 16:12:05 [utils.py:91] NomicBertConfig contains a deprecated attribute name 'rotary_emb_fraction'. Please use the preferred attribute name 'partial_rotary_factor' instead.
(APIServer pid=1) INFO 02-28 16:12:05 [config.py:864] Found sentence-transformers tokenize configuration.
(APIServer pid=1) /usr/local/lib/python3.12/dist-packages/torch/library.py:357: UserWarning: Warning only once for all operators,  other operators may also be overridden.
(APIServer pid=1)   Overriding a previously registered kernel for the same operator and the same dispatch key
(APIServer pid=1)   operator: flash_attn::_flash_attn_backward(Tensor dout, Tensor q, Tensor k, Tensor v, Tensor out, Tensor softmax_lse, Tensor(a6!)? dq, Tensor(a7!)? dk, Tensor(a8!)? dv, float dropout_p, float softmax_scale, bool causal, SymInt window_size_left, SymInt window_size_right, float softcap, Tensor? alibi_slopes, bool deterministic, Tensor? rng_state=None) -> Tensor
(APIServer pid=1)     registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926
(APIServer pid=1)   dispatch key: ADInplaceOrView
(APIServer pid=1)   previous kernel: no debug info
(APIServer pid=1)        new kernel: registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926 (Triggered internally at /opt/pytorch/pytorch/aten/src/ATen/core/dispatch/OperatorEntry.cpp:208.)
(APIServer pid=1)   self.m.impl(
(APIServer pid=1) INFO 02-28 16:12:08 [model.py:827] Resolved `--convert auto` to `--convert embed`. Pass the value explicitly to silence this message.
(APIServer pid=1) INFO 02-28 16:12:08 [model.py:514] Resolved architecture: NomicBertModel
(APIServer pid=1) INFO 02-28 16:12:08 [config.py:752] Found sentence-transformers modules configuration.
(APIServer pid=1) INFO 02-28 16:12:08 [config.py:783] Found pooling configuration.
(APIServer pid=1) INFO 02-28 16:12:08 [model.py:2002] Downcasting torch.float32 to torch.float16.
(APIServer pid=1) INFO 02-28 16:12:08 [model.py:1661] Using max model len 8192
(APIServer pid=1) INFO 02-28 16:12:08 [model.py:1661] Using max model len 2048
(APIServer pid=1) WARNING 02-28 16:12:08 [config.py:146] Nomic context extension is disabled. Changing max_model_len from 8192 to 2048. To enable context extension, see: https://github.com/vllm-project/vllm/tree/main/examples/offline_inference/context_extension.html
(APIServer pid=1) WARNING 02-28 16:12:08 [vllm.py:701] Pooling models do not support full cudagraphs. Overriding cudagraph_mode to PIECEWISE.
/usr/local/lib/python3.12/dist-packages/torchvision/io/image.py:14: UserWarning: Failed to load image Python extension: 'Could not load this library: /usr/local/lib/python3.12/dist-packages/torchvision/image.so'If you don't plan on using image functionality from `torchvision.io`, you can ignore this warning. Otherwise, there might be something wrong with your environment. Did you have `libjpeg` or `libpng` installed before building `torchvision` from source?
  warn(
(EngineCore_DP0 pid=167) INFO 02-28 16:12:12 [core.py:93] Initializing a V1 LLM engine (v0.13.0+faa43dbf.nv26.01) with config: model='nomic-ai/nomic-embed-text-v1.5', speculative_config=None, tokenizer='nomic-ai/nomic-embed-text-v1.5', skip_tokenizer_init=False, tokenizer_mode=auto, revision=None, tokenizer_revision=None, trust_remote_code=True, dtype=torch.float16, max_seq_len=2048, download_dir=None, load_format=auto, tensor_parallel_size=1, pipeline_parallel_size=1, data_parallel_size=1, disable_custom_all_reduce=False, quantization=None, enforce_eager=False, kv_cache_dtype=auto, device_config=cuda, structured_outputs_config=StructuredOutputsConfig(backend='auto', disable_fallback=False, disable_any_whitespace=False, disable_additional_properties=False, reasoning_parser='', reasoning_parser_plugin='', enable_in_reasoning=False), observability_config=ObservabilityConfig(show_hidden_metrics_for_version=None, otlp_traces_endpoint=None, collect_detailed_traces=None, kv_cache_metrics=False, kv_cache_metrics_sample=0.01, cudagraph_metrics=False, enable_layerwise_nvtx_tracing=False), seed=0, served_model_name=nomic-ai/nomic-embed-text-v1.5, enable_prefix_caching=False, enable_chunked_prefill=False, pooler_config=PoolerConfig(pooling_type='MEAN', normalize=False, dimensions=None, enable_chunked_processing=None, max_embed_len=None, softmax=None, activation=None, use_activation=None, logit_bias=None, step_tag_id=None, returned_token_ids=None), compilation_config={'level': None, 'mode': <CompilationMode.VLLM_COMPILE: 3>, 'debug_dump_path': None, 'cache_dir': '', 'compile_cache_save_format': 'binary', 'backend': 'inductor', 'custom_ops': ['none'], 'splitting_ops': ['vllm::unified_attention', 'vllm::unified_attention_with_output', 'vllm::unified_mla_attention', 'vllm::unified_mla_attention_with_output', 'vllm::mamba_mixer2', 'vllm::mamba_mixer', 'vllm::short_conv', 'vllm::linear_attention', 'vllm::plamo2_mamba_mixer', 'vllm::gdn_attention_core', 'vllm::kda_attention', 'vllm::sparse_attn_indexer'], 'compile_mm_encoder': False, 'compile_sizes': [], 'compile_ranges_split_points': [8192], 'inductor_compile_config': {'enable_auto_functionalized_v2': False, 'combo_kernels': True, 'benchmark_combo_kernel': True}, 'inductor_passes': {}, 'cudagraph_mode': <CUDAGraphMode.PIECEWISE: 1>, 'cudagraph_num_of_warmups': 1, 'cudagraph_capture_sizes': [1, 2, 4, 8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 152, 160, 168, 176, 184, 192, 200, 208, 216, 224, 232, 240, 248, 256, 272, 288, 304, 320, 336, 352, 368, 384, 400, 416, 432, 448, 464, 480, 496, 512], 'cudagraph_copy_inputs': False, 'cudagraph_specialize_lora': True, 'use_inductor_graph_partition': False, 'pass_config': {'fuse_norm_quant': False, 'fuse_act_quant': False, 'fuse_attn_quant': False, 'eliminate_noops': True, 'enable_sp': False, 'fuse_gemm_comms': False, 'fuse_allreduce_rms': False}, 'max_cudagraph_capture_size': 512, 'dynamic_shapes_config': {'type': <DynamicShapesType.BACKED: 'backed'>, 'evaluate_guards': False}, 'local_cache_dir': None}
(EngineCore_DP0 pid=167) /usr/local/lib/python3.12/dist-packages/torch/library.py:357: UserWarning: Warning only once for all operators,  other operators may also be overridden.
(EngineCore_DP0 pid=167)   Overriding a previously registered kernel for the same operator and the same dispatch key
(EngineCore_DP0 pid=167)   operator: flash_attn::_flash_attn_backward(Tensor dout, Tensor q, Tensor k, Tensor v, Tensor out, Tensor softmax_lse, Tensor(a6!)? dq, Tensor(a7!)? dk, Tensor(a8!)? dv, float dropout_p, float softmax_scale, bool causal, SymInt window_size_left, SymInt window_size_right, float softcap, Tensor? alibi_slopes, bool deterministic, Tensor? rng_state=None) -> Tensor
(EngineCore_DP0 pid=167)     registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926
(EngineCore_DP0 pid=167)   dispatch key: ADInplaceOrView
(EngineCore_DP0 pid=167)   previous kernel: no debug info
(EngineCore_DP0 pid=167)        new kernel: registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926 (Triggered internally at /opt/pytorch/pytorch/aten/src/ATen/core/dispatch/OperatorEntry.cpp:208.)
(EngineCore_DP0 pid=167)   self.m.impl(
(EngineCore_DP0 pid=167) INFO 02-28 16:12:13 [parallel_state.py:1203] world_size=1 rank=0 local_rank=0 distributed_init_method=tcp://172.17.0.3:38849 backend=nccl
(EngineCore_DP0 pid=167) INFO 02-28 16:12:13 [parallel_state.py:1411] rank 0 in world size 1 is assigned as DP rank 0, PP rank 0, PCP rank 0, TP rank 0, EP rank 0
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866] EngineCore failed to start.
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866] Traceback (most recent call last):
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 857, in run_engine_core
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866]     engine_core = EngineCoreProc(*args, **kwargs)
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866]                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 637, in __init__
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866]     super().__init__(
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 102, in __init__
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866]     self.model_executor = executor_class(vllm_config)
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866]                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/executor/abstract.py", line 101, in __init__
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866]     self._init_executor()
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/executor/uniproc_executor.py", line 47, in _init_executor
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866]     self.driver_worker.init_device()
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/worker_base.py", line 326, in init_device
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866]     self.worker.init_device()  # type: ignore
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866]     ^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/gpu_worker.py", line 247, in init_device
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866]     raise ValueError(
(EngineCore_DP0 pid=167) ERROR 02-28 16:12:13 [core.py:866] ValueError: Free memory on device (4.04/119.63 GiB) on startup is less than desired GPU memory utilization (0.15, 17.94 GiB). Decrease GPU memory utilization or reduce GPU memory used by other processes.
(EngineCore_DP0 pid=167) Process EngineCore_DP0:
(EngineCore_DP0 pid=167) Traceback (most recent call last):
(EngineCore_DP0 pid=167)   File "/usr/lib/python3.12/multiprocessing/process.py", line 314, in _bootstrap
(EngineCore_DP0 pid=167)     self.run()
(EngineCore_DP0 pid=167)   File "/usr/lib/python3.12/multiprocessing/process.py", line 108, in run
(EngineCore_DP0 pid=167)     self._target(*self._args, **self._kwargs)
(EngineCore_DP0 pid=167)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 870, in run_engine_core
(EngineCore_DP0 pid=167)     raise e
(EngineCore_DP0 pid=167)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 857, in run_engine_core
(EngineCore_DP0 pid=167)     engine_core = EngineCoreProc(*args, **kwargs)
(EngineCore_DP0 pid=167)                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=167)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 637, in __init__
(EngineCore_DP0 pid=167)     super().__init__(
(EngineCore_DP0 pid=167)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 102, in __init__
(EngineCore_DP0 pid=167)     self.model_executor = executor_class(vllm_config)
(EngineCore_DP0 pid=167)                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=167)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/executor/abstract.py", line 101, in __init__
(EngineCore_DP0 pid=167)     self._init_executor()
(EngineCore_DP0 pid=167)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/executor/uniproc_executor.py", line 47, in _init_executor
(EngineCore_DP0 pid=167)     self.driver_worker.init_device()
(EngineCore_DP0 pid=167)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/worker_base.py", line 326, in init_device
(EngineCore_DP0 pid=167)     self.worker.init_device()  # type: ignore
(EngineCore_DP0 pid=167)     ^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=167)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/gpu_worker.py", line 247, in init_device
(EngineCore_DP0 pid=167)     raise ValueError(
(EngineCore_DP0 pid=167) ValueError: Free memory on device (4.04/119.63 GiB) on startup is less than desired GPU memory utilization (0.15, 17.94 GiB). Decrease GPU memory utilization or reduce GPU memory used by other processes.
[rank0]:[W228 16:12:13.860801916 ProcessGroupNCCL.cpp:1565] Warning: WARNING: destroy_process_group() was not called before program exit, which can leak resources. For more info, please see https://pytorch.org/docs/stable/distributed.html#shutdown (function operator())
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