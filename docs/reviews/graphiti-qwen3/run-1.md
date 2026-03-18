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
(APIServer pid=1) INFO 03-18 11:13:17 [api_server.py:1354] vLLM API server version 0.13.0+faa43dbf.nv26.01
(APIServer pid=1) INFO 03-18 11:13:17 [utils.py:253] non-default args: {'model_tag': 'Qwen/Qwen3-30B-A3B-FP8', 'host': '0.0.0.0', 'model': 'Qwen/Qwen3-30B-A3B-FP8', 'trust_remote_code': True, 'max_model_len': 32768, 'load_format': 'fastsafetensors', 'reasoning_parser': 'qwen3', 'gpu_memory_utilization': 0.3, 'kv_cache_dtype': 'fp8', 'enable_prefix_caching': True}
(APIServer pid=1) The argument `trust_remote_code` is to be used with Auto classes. It has no effect here and is ignored.
(APIServer pid=1) /usr/local/lib/python3.12/dist-packages/torch/library.py:357: UserWarning: Warning only once for all operators,  other operators may also be overridden.
(APIServer pid=1)   Overriding a previously registered kernel for the same operator and the same dispatch key
(APIServer pid=1)   operator: flash_attn::_flash_attn_backward(Tensor dout, Tensor q, Tensor k, Tensor v, Tensor out, Tensor softmax_lse, Tensor(a6!)? dq, Tensor(a7!)? dk, Tensor(a8!)? dv, float dropout_p, float softmax_scale, bool causal, SymInt window_size_left, SymInt window_size_right, float softcap, Tensor? alibi_slopes, bool deterministic, Tensor? rng_state=None) -> Tensor
(APIServer pid=1)     registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926
(APIServer pid=1)   dispatch key: ADInplaceOrView
(APIServer pid=1)   previous kernel: no debug info
(APIServer pid=1)        new kernel: registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926 (Triggered internally at /opt/pytorch/pytorch/aten/src/ATen/core/dispatch/OperatorEntry.cpp:208.)
(APIServer pid=1)   self.m.impl(
(APIServer pid=1) INFO 03-18 11:13:22 [model.py:514] Resolved architecture: Qwen3MoeForCausalLM
(APIServer pid=1) INFO 03-18 11:13:22 [model.py:1661] Using max model len 32768
(APIServer pid=1) INFO 03-18 11:13:22 [cache.py:205] Using fp8 data type to store kv cache. It reduces the GPU memory footprint and boosts the performance. Meanwhile, it may cause accuracy drop without a proper scaling factor.
(APIServer pid=1) INFO 03-18 11:13:22 [scheduler.py:230] Chunked prefill is enabled with max_num_batched_tokens=2048.
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
(EngineCore_DP0 pid=192) INFO 03-18 11:13:28 [core.py:93] Initializing a V1 LLM engine (v0.13.0+faa43dbf.nv26.01) with config: model='Qwen/Qwen3-30B-A3B-FP8', speculative_config=None, tokenizer='Qwen/Qwen3-30B-A3B-FP8', skip_tokenizer_init=False, tokenizer_mode=auto, revision=None, tokenizer_revision=None, trust_remote_code=True, dtype=torch.bfloat16, max_seq_len=32768, download_dir=None, load_format=fastsafetensors, tensor_parallel_size=1, pipeline_parallel_size=1, data_parallel_size=1, disable_custom_all_reduce=False, quantization=fp8, enforce_eager=False, kv_cache_dtype=fp8, device_config=cuda, structured_outputs_config=StructuredOutputsConfig(backend='auto', disable_fallback=False, disable_any_whitespace=False, disable_additional_properties=False, reasoning_parser='qwen3', reasoning_parser_plugin='', enable_in_reasoning=False), observability_config=ObservabilityConfig(show_hidden_metrics_for_version=None, otlp_traces_endpoint=None, collect_detailed_traces=None, kv_cache_metrics=False, kv_cache_metrics_sample=0.01, cudagraph_metrics=False, enable_layerwise_nvtx_tracing=False), seed=0, served_model_name=Qwen/Qwen3-30B-A3B-FP8, enable_prefix_caching=True, enable_chunked_prefill=True, pooler_config=None, compilation_config={'level': None, 'mode': <CompilationMode.VLLM_COMPILE: 3>, 'debug_dump_path': None, 'cache_dir': '', 'compile_cache_save_format': 'binary', 'backend': 'inductor', 'custom_ops': ['+quant_fp8', 'none', '+quant_fp8'], 'splitting_ops': ['vllm::unified_attention', 'vllm::unified_attention_with_output', 'vllm::unified_mla_attention', 'vllm::unified_mla_attention_with_output', 'vllm::mamba_mixer2', 'vllm::mamba_mixer', 'vllm::short_conv', 'vllm::linear_attention', 'vllm::plamo2_mamba_mixer', 'vllm::gdn_attention_core', 'vllm::kda_attention', 'vllm::sparse_attn_indexer'], 'compile_mm_encoder': False, 'compile_sizes': [], 'compile_ranges_split_points': [2048], 'inductor_compile_config': {'enable_auto_functionalized_v2': False, 'combo_kernels': True, 'benchmark_combo_kernel': True}, 'inductor_passes': {}, 'cudagraph_mode': <CUDAGraphMode.FULL_AND_PIECEWISE: (2, 1)>, 'cudagraph_num_of_warmups': 1, 'cudagraph_capture_sizes': [1, 2, 4, 8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 152, 160, 168, 176, 184, 192, 200, 208, 216, 224, 232, 240, 248, 256, 272, 288, 304, 320, 336, 352, 368, 384, 400, 416, 432, 448, 464, 480, 496, 512], 'cudagraph_copy_inputs': False, 'cudagraph_specialize_lora': True, 'use_inductor_graph_partition': False, 'pass_config': {'fuse_norm_quant': True, 'fuse_act_quant': True, 'fuse_attn_quant': False, 'eliminate_noops': True, 'enable_sp': False, 'fuse_gemm_comms': False, 'fuse_allreduce_rms': False}, 'max_cudagraph_capture_size': 512, 'dynamic_shapes_config': {'type': <DynamicShapesType.BACKED: 'backed'>, 'evaluate_guards': False}, 'local_cache_dir': None}
(EngineCore_DP0 pid=192) INFO 03-18 11:13:28 [parallel_state.py:1203] world_size=1 rank=0 local_rank=0 distributed_init_method=tcp://172.17.0.3:45045 backend=nccl
(EngineCore_DP0 pid=192) INFO 03-18 11:13:28 [parallel_state.py:1411] rank 0 in world size 1 is assigned as DP rank 0, PP rank 0, PCP rank 0, TP rank 0, EP rank 0
(EngineCore_DP0 pid=192) INFO 03-18 11:13:28 [gpu_model_runner.py:3562] Starting to load model Qwen/Qwen3-30B-A3B-FP8...
(EngineCore_DP0 pid=192) INFO 03-18 11:13:38 [cuda.py:351] Using FLASHINFER attention backend out of potential backends: ('FLASHINFER', 'TRITON_ATTN')
(EngineCore_DP0 pid=192) INFO 03-18 11:13:38 [layer.py:372] Enabled separate cuda stream for MoE shared_experts
(EngineCore_DP0 pid=192) WARNING 03-18 11:13:38 [fp8.py:186] DeepGEMM backend requested but not available.
(EngineCore_DP0 pid=192) INFO 03-18 11:13:38 [fp8.py:205] Using Triton backend for FP8 MoE
(EngineCore_DP0 pid=192) INFO 03-18 11:27:26 [weight_utils.py:487] Time spent downloading weights for Qwen/Qwen3-30B-A3B-FP8: 826.331217 seconds
Loading safetensors using Fastsafetensor loader:   0% Completed | 0/7 [00:00<?, ?it/s]
Loading safetensors using Fastsafetensor loader:   0% Completed | 0/7 [00:00<?, ?it/s]
(EngineCore_DP0 pid=192) 
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866] EngineCore failed to start.
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866] Traceback (most recent call last):
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/utils/import_utils.py", line 319, in __getattr__
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     importlib.import_module(name)
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/lib/python3.12/importlib/__init__.py", line 90, in import_module
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     return _bootstrap._gcd_import(name[level:], package, level)
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "<frozen importlib._bootstrap>", line 1324, in _find_and_load_unlocked
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866] ModuleNotFoundError: No module named 'fastsafetensors'
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866] 
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866] The above exception was the direct cause of the following exception:
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866] 
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866] Traceback (most recent call last):
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 857, in run_engine_core
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     engine_core = EngineCoreProc(*args, **kwargs)
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 637, in __init__
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     super().__init__(
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 102, in __init__
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     self.model_executor = executor_class(vllm_config)
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/executor/abstract.py", line 101, in __init__
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     self._init_executor()
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/executor/uniproc_executor.py", line 48, in _init_executor
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     self.driver_worker.load_model()
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/gpu_worker.py", line 289, in load_model
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     self.model_runner.load_model(eep_scale_up=eep_scale_up)
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/gpu_model_runner.py", line 3581, in load_model
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     self.model = model_loader.load_model(
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]                  ^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/base_loader.py", line 55, in load_model
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     self.load_weights(model, model_config)
(EngineCore_DP0 pid=192) Process EngineCore_DP0:
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/default_loader.py", line 305, in load_weights
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     loaded_weights = model.load_weights(self.get_all_weights(model_config, model))
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/qwen3_moe.py", line 748, in load_weights
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     return loader.load_weights(weights)
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/online_quantization.py", line 173, in patched_model_load_weights
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     return original_load_weights(auto_weight_loader, weights, mapper=mapper)
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/utils.py", line 335, in load_weights
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     autoloaded_weights = set(self._load_module("", self.module, weights))
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/utils.py", line 279, in _load_module
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     for child_prefix, child_weights in self._groupby_prefix(weights):
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/utils.py", line 163, in _groupby_prefix
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     for prefix, group in itertools.groupby(weights_by_parts, key=lambda x: x[0][0]):
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/utils.py", line 158, in <genexpr>
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     weights_by_parts = (
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]                        ^
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/utils.py", line 331, in <genexpr>
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     weights = (
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]               ^
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/default_loader.py", line 277, in get_all_weights
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     yield from self._get_weights_iterator(primary_weights)
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/default_loader.py", line 263, in <genexpr>
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     return ((source.prefix + name, tensor) for (name, tensor) in weights_iterator)
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/weight_utils.py", line 791, in fastsafetensors_weights_iterator
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     loader = _init_loader(pg, device, f_list, nogds=nogds)
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/weight_utils.py", line 760, in _init_loader
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     loader = SafeTensorsFileLoader(pg, device, nogds=nogds)
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/utils/import_utils.py", line 190, in __call__
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     return self.__getattr__("__call__")
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/utils/import_utils.py", line 346, in __getattr__
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     getattr(self.__module, f"{self.__attr_path}.{key}")
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]   File "/usr/local/lib/python3.12/dist-packages/vllm/utils/import_utils.py", line 324, in __getattr__
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866]     raise ImportError(msg) from exc
(EngineCore_DP0 pid=192) ERROR 03-18 11:27:27 [core.py:866] ImportError: Please install vllm[fastsafetensors] for fastsafetensors support
(EngineCore_DP0 pid=192) Traceback (most recent call last):
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/utils/import_utils.py", line 319, in __getattr__
(EngineCore_DP0 pid=192)     importlib.import_module(name)
(EngineCore_DP0 pid=192)   File "/usr/lib/python3.12/importlib/__init__.py", line 90, in import_module
(EngineCore_DP0 pid=192)     return _bootstrap._gcd_import(name[level:], package, level)
(EngineCore_DP0 pid=192)            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192)   File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
(EngineCore_DP0 pid=192)   File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
(EngineCore_DP0 pid=192)   File "<frozen importlib._bootstrap>", line 1324, in _find_and_load_unlocked
(EngineCore_DP0 pid=192) ModuleNotFoundError: No module named 'fastsafetensors'
(EngineCore_DP0 pid=192) 
(EngineCore_DP0 pid=192) The above exception was the direct cause of the following exception:
(EngineCore_DP0 pid=192) 
(EngineCore_DP0 pid=192) Traceback (most recent call last):
(EngineCore_DP0 pid=192)   File "/usr/lib/python3.12/multiprocessing/process.py", line 314, in _bootstrap
(EngineCore_DP0 pid=192)     self.run()
(EngineCore_DP0 pid=192)   File "/usr/lib/python3.12/multiprocessing/process.py", line 108, in run
(EngineCore_DP0 pid=192)     self._target(*self._args, **self._kwargs)
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 870, in run_engine_core
(EngineCore_DP0 pid=192)     raise e
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 857, in run_engine_core
(EngineCore_DP0 pid=192)     engine_core = EngineCoreProc(*args, **kwargs)
(EngineCore_DP0 pid=192)                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 637, in __init__
(EngineCore_DP0 pid=192)     super().__init__(
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/engine/core.py", line 102, in __init__
(EngineCore_DP0 pid=192)     self.model_executor = executor_class(vllm_config)
(EngineCore_DP0 pid=192)                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/executor/abstract.py", line 101, in __init__
(EngineCore_DP0 pid=192)     self._init_executor()
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/executor/uniproc_executor.py", line 48, in _init_executor
(EngineCore_DP0 pid=192)     self.driver_worker.load_model()
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/gpu_worker.py", line 289, in load_model
(EngineCore_DP0 pid=192)     self.model_runner.load_model(eep_scale_up=eep_scale_up)
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/gpu_model_runner.py", line 3581, in load_model
(EngineCore_DP0 pid=192)     self.model = model_loader.load_model(
(EngineCore_DP0 pid=192)                  ^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/base_loader.py", line 55, in load_model
(EngineCore_DP0 pid=192)     self.load_weights(model, model_config)
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/default_loader.py", line 305, in load_weights
(EngineCore_DP0 pid=192)     loaded_weights = model.load_weights(self.get_all_weights(model_config, model))
(EngineCore_DP0 pid=192)                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/qwen3_moe.py", line 748, in load_weights
(EngineCore_DP0 pid=192)     return loader.load_weights(weights)
(EngineCore_DP0 pid=192)            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/online_quantization.py", line 173, in patched_model_load_weights
(EngineCore_DP0 pid=192)     return original_load_weights(auto_weight_loader, weights, mapper=mapper)
(EngineCore_DP0 pid=192)            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/utils.py", line 335, in load_weights
(EngineCore_DP0 pid=192)     autoloaded_weights = set(self._load_module("", self.module, weights))
(EngineCore_DP0 pid=192)                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/utils.py", line 279, in _load_module
(EngineCore_DP0 pid=192)     for child_prefix, child_weights in self._groupby_prefix(weights):
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/utils.py", line 163, in _groupby_prefix
(EngineCore_DP0 pid=192)     for prefix, group in itertools.groupby(weights_by_parts, key=lambda x: x[0][0]):
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/utils.py", line 158, in <genexpr>
(EngineCore_DP0 pid=192)     weights_by_parts = (
(EngineCore_DP0 pid=192)                        ^
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/utils.py", line 331, in <genexpr>
(EngineCore_DP0 pid=192)     weights = (
(EngineCore_DP0 pid=192)               ^
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/default_loader.py", line 277, in get_all_weights
(EngineCore_DP0 pid=192)     yield from self._get_weights_iterator(primary_weights)
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/default_loader.py", line 263, in <genexpr>
(EngineCore_DP0 pid=192)     return ((source.prefix + name, tensor) for (name, tensor) in weights_iterator)
(EngineCore_DP0 pid=192)            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/weight_utils.py", line 791, in fastsafetensors_weights_iterator
(EngineCore_DP0 pid=192)     loader = _init_loader(pg, device, f_list, nogds=nogds)
(EngineCore_DP0 pid=192)              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/weight_utils.py", line 760, in _init_loader
(EngineCore_DP0 pid=192)     loader = SafeTensorsFileLoader(pg, device, nogds=nogds)
(EngineCore_DP0 pid=192)              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/utils/import_utils.py", line 190, in __call__
(EngineCore_DP0 pid=192)     return self.__getattr__("__call__")
(EngineCore_DP0 pid=192)            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/utils/import_utils.py", line 346, in __getattr__
(EngineCore_DP0 pid=192)     getattr(self.__module, f"{self.__attr_path}.{key}")
(EngineCore_DP0 pid=192)   File "/usr/local/lib/python3.12/dist-packages/vllm/utils/import_utils.py", line 324, in __getattr__
(EngineCore_DP0 pid=192)     raise ImportError(msg) from exc
(EngineCore_DP0 pid=192) ImportError: Please install vllm[fastsafetensors] for fastsafetensors support
[rank0]:[W318 11:27:27.752715061 ProcessGroupNCCL.cpp:1565] Warning: WARNING: destroy_process_group() was not called before program exit, which can leak resources. For more info, please see https://pytorch.org/docs/stable/distributed.html#shutdown (function operator())
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
