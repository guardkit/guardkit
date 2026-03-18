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
(APIServer pid=1) INFO 03-18 14:03:56 [api_server.py:1354] vLLM API server version 0.13.0+faa43dbf.nv26.01
(APIServer pid=1) INFO 03-18 14:03:56 [utils.py:253] non-default args: {'model_tag': 'neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic', 'host': '0.0.0.0', 'model': 'neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic', 'max_model_len': 32768, 'gpu_memory_utilization': 0.4, 'kv_cache_dtype': 'fp8', 'enable_prefix_caching': True, 'structured_outputs_config': StructuredOutputsConfig(backend='xgrammar', disable_fallback=False, disable_any_whitespace=False, disable_additional_properties=False, reasoning_parser='', reasoning_parser_plugin='', enable_in_reasoning=False)}
(APIServer pid=1) INFO 03-18 14:03:58 [model.py:514] Resolved architecture: Qwen2ForCausalLM
(APIServer pid=1) INFO 03-18 14:03:58 [model.py:1661] Using max model len 32768
(APIServer pid=1) /usr/local/lib/python3.12/dist-packages/torch/library.py:357: UserWarning: Warning only once for all operators,  other operators may also be overridden.
(APIServer pid=1)   Overriding a previously registered kernel for the same operator and the same dispatch key
(APIServer pid=1)   operator: flash_attn::_flash_attn_backward(Tensor dout, Tensor q, Tensor k, Tensor v, Tensor out, Tensor softmax_lse, Tensor(a6!)? dq, Tensor(a7!)? dk, Tensor(a8!)? dv, float dropout_p, float softmax_scale, bool causal, SymInt window_size_left, SymInt window_size_right, float softcap, Tensor? alibi_slopes, bool deterministic, Tensor? rng_state=None) -> Tensor
(APIServer pid=1)     registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926
(APIServer pid=1)   dispatch key: ADInplaceOrView
(APIServer pid=1)   previous kernel: no debug info
(APIServer pid=1)        new kernel: registered at /usr/local/lib/python3.12/dist-packages/torch/_library/custom_ops.py:926 (Triggered internally at /opt/pytorch/pytorch/aten/src/ATen/core/dispatch/OperatorEntry.cpp:208.)
(APIServer pid=1)   self.m.impl(
(APIServer pid=1) INFO 03-18 14:03:58 [cache.py:205] Using fp8 data type to store kv cache. It reduces the GPU memory footprint and boosts the performance. Meanwhile, it may cause accuracy drop without a proper scaling factor.
(APIServer pid=1) INFO 03-18 14:03:58 [scheduler.py:230] Chunked prefill is enabled with max_num_batched_tokens=2048.
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
(EngineCore_DP0 pid=143) INFO 03-18 14:04:03 [core.py:93] Initializing a V1 LLM engine (v0.13.0+faa43dbf.nv26.01) with config: model='neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic', speculative_config=None, tokenizer='neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic', skip_tokenizer_init=False, tokenizer_mode=auto, revision=None, tokenizer_revision=None, trust_remote_code=False, dtype=torch.bfloat16, max_seq_len=32768, download_dir=None, load_format=auto, tensor_parallel_size=1, pipeline_parallel_size=1, data_parallel_size=1, disable_custom_all_reduce=False, quantization=compressed-tensors, enforce_eager=False, kv_cache_dtype=fp8, device_config=cuda, structured_outputs_config=StructuredOutputsConfig(backend='xgrammar', disable_fallback=False, disable_any_whitespace=False, disable_additional_properties=False, reasoning_parser='', reasoning_parser_plugin='', enable_in_reasoning=False), observability_config=ObservabilityConfig(show_hidden_metrics_for_version=None, otlp_traces_endpoint=None, collect_detailed_traces=None, kv_cache_metrics=False, kv_cache_metrics_sample=0.01, cudagraph_metrics=False, enable_layerwise_nvtx_tracing=False), seed=0, served_model_name=neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic, enable_prefix_caching=True, enable_chunked_prefill=True, pooler_config=None, compilation_config={'level': None, 'mode': <CompilationMode.VLLM_COMPILE: 3>, 'debug_dump_path': None, 'cache_dir': '', 'compile_cache_save_format': 'binary', 'backend': 'inductor', 'custom_ops': ['none'], 'splitting_ops': ['vllm::unified_attention', 'vllm::unified_attention_with_output', 'vllm::unified_mla_attention', 'vllm::unified_mla_attention_with_output', 'vllm::mamba_mixer2', 'vllm::mamba_mixer', 'vllm::short_conv', 'vllm::linear_attention', 'vllm::plamo2_mamba_mixer', 'vllm::gdn_attention_core', 'vllm::kda_attention', 'vllm::sparse_attn_indexer'], 'compile_mm_encoder': False, 'compile_sizes': [], 'compile_ranges_split_points': [2048], 'inductor_compile_config': {'enable_auto_functionalized_v2': False, 'combo_kernels': True, 'benchmark_combo_kernel': True}, 'inductor_passes': {}, 'cudagraph_mode': <CUDAGraphMode.FULL_AND_PIECEWISE: (2, 1)>, 'cudagraph_num_of_warmups': 1, 'cudagraph_capture_sizes': [1, 2, 4, 8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 152, 160, 168, 176, 184, 192, 200, 208, 216, 224, 232, 240, 248, 256, 272, 288, 304, 320, 336, 352, 368, 384, 400, 416, 432, 448, 464, 480, 496, 512], 'cudagraph_copy_inputs': False, 'cudagraph_specialize_lora': True, 'use_inductor_graph_partition': False, 'pass_config': {'fuse_norm_quant': False, 'fuse_act_quant': False, 'fuse_attn_quant': False, 'eliminate_noops': True, 'enable_sp': False, 'fuse_gemm_comms': False, 'fuse_allreduce_rms': False}, 'max_cudagraph_capture_size': 512, 'dynamic_shapes_config': {'type': <DynamicShapesType.BACKED: 'backed'>, 'evaluate_guards': False}, 'local_cache_dir': None}
(EngineCore_DP0 pid=143) INFO 03-18 14:04:03 [parallel_state.py:1203] world_size=1 rank=0 local_rank=0 distributed_init_method=tcp://172.17.0.3:57931 backend=nccl
(EngineCore_DP0 pid=143) INFO 03-18 14:04:03 [parallel_state.py:1411] rank 0 in world size 1 is assigned as DP rank 0, PP rank 0, PCP rank 0, TP rank 0, EP rank 0
(EngineCore_DP0 pid=143) INFO 03-18 14:04:03 [gpu_model_runner.py:3562] Starting to load model neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic...
(EngineCore_DP0 pid=143) INFO 03-18 14:04:13 [cuda.py:351] Using FLASHINFER attention backend out of potential backends: ('FLASHINFER', 'TRITON_ATTN')
Loading safetensors checkpoint shards:   0% Completed | 0/4 [00:00<?, ?it/s]
Loading safetensors checkpoint shards:  25% Completed | 1/4 [00:08<00:25,  8.40s/it]
Loading safetensors checkpoint shards:  50% Completed | 2/4 [00:28<00:30, 15.47s/it]
Loading safetensors checkpoint shards:  75% Completed | 3/4 [00:55<00:20, 20.58s/it]
Loading safetensors checkpoint shards: 100% Completed | 4/4 [01:23<00:00, 23.37s/it]
Loading safetensors checkpoint shards: 100% Completed | 4/4 [01:23<00:00, 20.78s/it]
(EngineCore_DP0 pid=143) 
(EngineCore_DP0 pid=143) INFO 03-18 14:05:39 [default_loader.py:308] Loading weights took 83.69 seconds
(EngineCore_DP0 pid=143) WARNING 03-18 14:05:39 [kv_cache.py:90] Checkpoint does not provide a q scaling factor. Setting it to k_scale. This only matters for FP8 Attention backends (flash-attn or flashinfer).
(EngineCore_DP0 pid=143) WARNING 03-18 14:05:39 [kv_cache.py:104] Using KV cache scaling factor 1.0 for fp8_e4m3. If this is unintended, verify that k/v_scale scaling factors are properly set in the checkpoint.
(EngineCore_DP0 pid=143) WARNING 03-18 14:05:39 [kv_cache.py:143] Using uncalibrated q_scale 1.0 and/or prob_scale 1.0 with fp8 attention. This may cause accuracy issues. Please make sure q/prob scaling factors are available in the fp8 checkpoint.
(EngineCore_DP0 pid=143) INFO 03-18 14:05:40 [gpu_model_runner.py:3659] Model loading took 15.2227 GiB memory and 96.106305 seconds
(EngineCore_DP0 pid=143) INFO 03-18 14:05:42 [decorators.py:432] Directly load AOT compilation from path /root/.cache/vllm/torch_aot_compile/36802542afb4c39fc8192239541b4ebbc816654b61837633c5a894e62c126f85/rank_0_0/model
(EngineCore_DP0 pid=143) INFO 03-18 14:05:42 [backends.py:643] Using cache directory: /root/.cache/vllm/torch_compile_cache/4aae4d336d/rank_0_0/backbone for vLLM's torch.compile
(EngineCore_DP0 pid=143) INFO 03-18 14:05:42 [backends.py:703] Dynamo bytecode transform time: 2.20 s
(EngineCore_DP0 pid=143) INFO 03-18 14:05:52 [backends.py:226] Directly load the compiled graph(s) for compile range (1, 2048) from the cache, took 7.171 s
(EngineCore_DP0 pid=143) INFO 03-18 14:05:52 [monitor.py:34] torch.compile takes 9.37 s in total
(EngineCore_DP0 pid=143) INFO 03-18 14:05:53 [gpu_worker.py:375] Available KV cache memory: 30.46 GiB
(EngineCore_DP0 pid=143) INFO 03-18 14:05:53 [kv_cache_utils.py:1291] GPU KV cache size: 332,672 tokens
(EngineCore_DP0 pid=143) INFO 03-18 14:05:53 [kv_cache_utils.py:1296] Maximum concurrency for 32,768 tokens per request: 10.15x
(EngineCore_DP0 pid=143) 2026-03-18 14:05:54,829 - INFO - autotuner.py:256 - flashinfer.jit: [Autotuner]: Autotuning process starts ...
(EngineCore_DP0 pid=143) INFO 03-18 14:05:54 [kernel_warmup.py:65] Warming up FlashInfer attention.
(EngineCore_DP0 pid=143) 2026-03-18 14:05:54,855 - INFO - autotuner.py:262 - flashinfer.jit: [Autotuner]: Autotuning process ends
Capturing CUDA graphs (mixed prefill-decode, PIECEWISE): 100%|██████████| 51/51 [00:06<00:00,  7.86it/s]
Capturing CUDA graphs (decode, FULL): 100%|██████████| 35/35 [00:04<00:00,  8.49it/s]
(EngineCore_DP0 pid=143) INFO 03-18 14:06:21 [gpu_model_runner.py:4587] Graph capturing finished in 11 secs, took 0.85 GiB
(EngineCore_DP0 pid=143) INFO 03-18 14:06:21 [core.py:259] init engine (profile, create kv cache, warmup model) took 40.98 seconds
(APIServer pid=1) INFO 03-18 14:06:22 [api_server.py:1102] Supported tasks: ['generate']
(APIServer pid=1) WARNING 03-18 14:06:23 [model.py:1487] Default sampling parameters have been overridden by the model's Hugging Face generation config recommended from the model creator. If this is not intended, please relaunch vLLM instance with `--generation-config vllm`.
(APIServer pid=1) INFO 03-18 14:06:23 [serving_responses.py:201] Using default chat sampling params from model: {'repetition_penalty': 1.05, 'temperature': 0.7, 'top_k': 20, 'top_p': 0.8}
(APIServer pid=1) INFO 03-18 14:06:23 [serving_chat.py:137] Using default chat sampling params from model: {'repetition_penalty': 1.05, 'temperature': 0.7, 'top_k': 20, 'top_p': 0.8}
(APIServer pid=1) INFO 03-18 14:06:23 [serving_completion.py:77] Using default completion sampling params from model: {'repetition_penalty': 1.05, 'temperature': 0.7, 'top_k': 20, 'top_p': 0.8}
(APIServer pid=1) INFO 03-18 14:06:23 [serving_chat.py:137] Using default chat sampling params from model: {'repetition_penalty': 1.05, 'temperature': 0.7, 'top_k': 20, 'top_p': 0.8}
(APIServer pid=1) INFO 03-18 14:06:23 [api_server.py:1428] Starting vLLM API server 0 on http://0.0.0.0:8000
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:38] Available routes are:
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /openapi.json, Methods: GET, HEAD
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /docs, Methods: GET, HEAD
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /docs/oauth2-redirect, Methods: GET, HEAD
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /redoc, Methods: GET, HEAD
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /scale_elastic_ep, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /is_scaling_elastic_ep, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /tokenize, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /detokenize, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /inference/v1/generate, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /pause, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /resume, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /is_paused, Methods: GET
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /metrics, Methods: GET
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /health, Methods: GET
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /load, Methods: GET
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /v1/models, Methods: GET
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /version, Methods: GET
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /v1/responses, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /v1/responses/{response_id}, Methods: GET
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /v1/responses/{response_id}/cancel, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /v1/messages, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /v1/chat/completions, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /v1/completions, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /v1/audio/transcriptions, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /v1/audio/translations, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /ping, Methods: GET
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /ping, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /invocations, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /classify, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /v1/embeddings, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /score, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /v1/score, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /rerank, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /v1/rerank, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /v2/rerank, Methods: POST
(APIServer pid=1) INFO 03-18 14:06:23 [launcher.py:46] Route: /pooling, Methods: POST
(APIServer pid=1) INFO:     Started server process [1]
(APIServer pid=1) INFO:     Waiting for application startup.
(APIServer pid=1) INFO:     Application startup complete.
(APIServer pid=1) INFO 03-18 14:09:16 [chat_utils.py:590] Detected the chat template content format to be 'string'. You can set `--chat-template-content-format` to override this.
(APIServer pid=1) INFO 03-18 14:09:24 [loggers.py:248] Engine 000: Avg prompt throughput: 203.6 tokens/s, Avg generation throughput: 6.2 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.6%, Prefix cache hit rate: 0.0%
(APIServer pid=1) INFO 03-18 14:09:34 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.3 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.7%, Prefix cache hit rate: 0.0%
(APIServer pid=1) INFO 03-18 14:09:44 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.3 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.7%, Prefix cache hit rate: 0.0%
(APIServer pid=1) INFO:     172.17.0.1:63871 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:09:54 [loggers.py:248] Engine 000: Avg prompt throughput: 769.0 tokens/s, Avg generation throughput: 6.5 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.3%, Prefix cache hit rate: 0.0%
(APIServer pid=1) INFO 03-18 14:10:04 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.0 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.4%, Prefix cache hit rate: 0.0%
(APIServer pid=1) INFO 03-18 14:10:14 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.0 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.4%, Prefix cache hit rate: 0.0%
(APIServer pid=1) INFO 03-18 14:10:24 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.9 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.4%, Prefix cache hit rate: 0.0%
(APIServer pid=1) INFO:     172.17.0.1:63871 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:10:34 [loggers.py:248] Engine 000: Avg prompt throughput: 688.0 tokens/s, Avg generation throughput: 7.6 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.1%, Prefix cache hit rate: 0.0%
(APIServer pid=1) INFO 03-18 14:10:44 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.0 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.1%, Prefix cache hit rate: 0.0%
(APIServer pid=1) INFO 03-18 14:10:54 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.0 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.1%, Prefix cache hit rate: 0.0%
(APIServer pid=1) INFO 03-18 14:11:04 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.9 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.2%, Prefix cache hit rate: 0.0%
(APIServer pid=1) INFO 03-18 14:11:14 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.0 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.2%, Prefix cache hit rate: 0.0%
(APIServer pid=1) INFO 03-18 14:11:24 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.0 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.2%, Prefix cache hit rate: 0.0%
(APIServer pid=1) INFO 03-18 14:11:34 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.9 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.3%, Prefix cache hit rate: 0.0%
(APIServer pid=1) INFO 03-18 14:11:44 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.9 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.3%, Prefix cache hit rate: 0.0%
(APIServer pid=1) INFO:     172.17.0.1:63871 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64167 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:63871 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64168 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64169 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64170 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:63871 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64168 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64169 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:11:54 [loggers.py:248] Engine 000: Avg prompt throughput: 609.5 tokens/s, Avg generation throughput: 23.8 tokens/s, Running: 1 reqs, Waiting: 1 reqs, GPU KV cache usage: 0.6%, Prefix cache hit rate: 11.3%
(APIServer pid=1) INFO:     172.17.0.1:64170 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:63871 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64169 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64168 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64170 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64167 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64169 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:63871 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64170 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64169 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64168 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64167 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:63871 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:12:04 [loggers.py:248] Engine 000: Avg prompt throughput: 8323.2 tokens/s, Avg generation throughput: 34.6 tokens/s, Running: 0 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.0%, Prefix cache hit rate: 75.1%
(APIServer pid=1) INFO 03-18 14:12:14 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 0.0 tokens/s, Running: 0 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.0%, Prefix cache hit rate: 75.1%
(APIServer pid=1) INFO 03-18 14:14:44 [loggers.py:248] Engine 000: Avg prompt throughput: 156.4 tokens/s, Avg generation throughput: 1.1 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.5%, Prefix cache hit rate: 74.1%
(APIServer pid=1) INFO 03-18 14:14:54 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.4 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.5%, Prefix cache hit rate: 74.1%
(APIServer pid=1) INFO 03-18 14:15:04 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.3 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.5%, Prefix cache hit rate: 74.1%
(APIServer pid=1) INFO 03-18 14:15:14 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.3 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.6%, Prefix cache hit rate: 74.1%
(APIServer pid=1) INFO:     172.17.0.1:64390 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:15:24 [loggers.py:248] Engine 000: Avg prompt throughput: 923.1 tokens/s, Avg generation throughput: 6.9 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.8%, Prefix cache hit rate: 71.8%
(APIServer pid=1) INFO 03-18 14:15:34 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.9 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.8%, Prefix cache hit rate: 71.8%
(APIServer pid=1) INFO 03-18 14:15:44 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.9 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.9%, Prefix cache hit rate: 71.8%
(APIServer pid=1) INFO 03-18 14:15:54 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.9 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.9%, Prefix cache hit rate: 71.8%
(APIServer pid=1) INFO:     172.17.0.1:64390 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:16:04 [loggers.py:248] Engine 000: Avg prompt throughput: 832.7 tokens/s, Avg generation throughput: 8.1 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.5%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:16:14 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.9 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.5%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:16:24 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.9 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.6%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:16:34 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.8 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.6%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:16:44 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.9 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.6%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:16:54 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.8 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.7%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:17:04 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.8 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.7%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:17:14 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.9 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.7%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:17:24 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.8 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.8%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:17:34 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.7 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.8%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:17:44 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.8 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.8%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:17:54 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.8 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.8%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:18:04 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.8 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.9%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:18:14 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.8 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.9%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:18:24 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.7 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.9%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:18:34 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.7 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.0%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:18:44 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.8 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.0%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:18:54 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.8 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.0%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:19:04 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.6 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.0%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO 03-18 14:19:14 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 8.8 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.1%, Prefix cache hit rate: 70.4%
(APIServer pid=1) INFO:     172.17.0.1:64390 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:19:24 [loggers.py:248] Engine 000: Avg prompt throughput: 382.6 tokens/s, Avg generation throughput: 16.1 tokens/s, Running: 5 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.6%, Prefix cache hit rate: 70.1%
(APIServer pid=1) INFO:     172.17.0.1:64749 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64750 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64751 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64390 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64748 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64751 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64749 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64750 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64390 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64748 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64751 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64749 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64390 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64748 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64750 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64751 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:19:34 [loggers.py:248] Engine 000: Avg prompt throughput: 1164.4 tokens/s, Avg generation throughput: 44.8 tokens/s, Running: 4 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.6%, Prefix cache hit rate: 69.2%
(APIServer pid=1) INFO:     172.17.0.1:64749 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64390 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64748 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64750 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64751 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64751 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64748 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64390 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:19:44 [loggers.py:248] Engine 000: Avg prompt throughput: 7061.9 tokens/s, Avg generation throughput: 36.7 tokens/s, Running: 5 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.5%, Prefix cache hit rate: 77.6%
(APIServer pid=1) INFO:     172.17.0.1:64750 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64751 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64748 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64749 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64390 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64751 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64748 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64750 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64749 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64751 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64390 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:19:54 [loggers.py:248] Engine 000: Avg prompt throughput: 4701.1 tokens/s, Avg generation throughput: 24.6 tokens/s, Running: 0 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.0%, Prefix cache hit rate: 81.6%
(APIServer pid=1) INFO 03-18 14:20:04 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 0.0 tokens/s, Running: 0 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.0%, Prefix cache hit rate: 81.6%
(APIServer pid=1) INFO 03-18 14:20:34 [loggers.py:248] Engine 000: Avg prompt throughput: 153.9 tokens/s, Avg generation throughput: 4.5 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.5%, Prefix cache hit rate: 81.1%
(APIServer pid=1) INFO 03-18 14:20:44 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.1 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.5%, Prefix cache hit rate: 81.1%
(APIServer pid=1) INFO 03-18 14:20:54 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.2 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.5%, Prefix cache hit rate: 81.1%
(APIServer pid=1) INFO:     172.17.0.1:64850 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:21:04 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 8.0 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.4%, Prefix cache hit rate: 80.2%
(APIServer pid=1) INFO 03-18 14:21:14 [loggers.py:248] Engine 000: Avg prompt throughput: 1067.4 tokens/s, Avg generation throughput: 8.8 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.2%, Prefix cache hit rate: 80.2%
(APIServer pid=1) INFO 03-18 14:21:24 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.8 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.3%, Prefix cache hit rate: 80.2%
(APIServer pid=1) INFO 03-18 14:21:34 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.6 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.3%, Prefix cache hit rate: 80.2%
(APIServer pid=1) INFO 03-18 14:21:44 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.7 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.3%, Prefix cache hit rate: 80.2%
(APIServer pid=1) INFO:     172.17.0.1:64850 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:21:54 [loggers.py:248] Engine 000: Avg prompt throughput: 971.2 tokens/s, Avg generation throughput: 8.2 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.9%, Prefix cache hit rate: 79.6%
(APIServer pid=1) INFO 03-18 14:22:04 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.7 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.0%, Prefix cache hit rate: 79.6%
(APIServer pid=1) INFO 03-18 14:22:14 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.8 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.0%, Prefix cache hit rate: 79.6%
(APIServer pid=1) INFO 03-18 14:22:24 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.8 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.0%, Prefix cache hit rate: 79.6%
(APIServer pid=1) INFO 03-18 14:22:34 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.7 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.0%, Prefix cache hit rate: 79.6%
(APIServer pid=1) INFO 03-18 14:22:44 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.8 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.1%, Prefix cache hit rate: 79.6%
(APIServer pid=1) INFO 03-18 14:22:54 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.8 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.1%, Prefix cache hit rate: 79.6%
(APIServer pid=1) INFO 03-18 14:23:04 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.7 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.1%, Prefix cache hit rate: 79.6%
(APIServer pid=1) INFO 03-18 14:23:14 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.7 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.2%, Prefix cache hit rate: 79.6%
(APIServer pid=1) INFO 03-18 14:23:24 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.8 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.2%, Prefix cache hit rate: 79.6%
(APIServer pid=1) INFO 03-18 14:23:34 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.7 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.2%, Prefix cache hit rate: 79.6%
(APIServer pid=1) INFO 03-18 14:23:44 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.7 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.2%, Prefix cache hit rate: 79.6%
(APIServer pid=1) INFO 03-18 14:23:54 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.6 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 3.3%, Prefix cache hit rate: 79.6%
(APIServer pid=1) INFO:     172.17.0.1:64850 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64850 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65235 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65237 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65238 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65236 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:24:04 [loggers.py:248] Engine 000: Avg prompt throughput: 790.7 tokens/s, Avg generation throughput: 20.3 tokens/s, Running: 5 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.6%, Prefix cache hit rate: 79.0%
(APIServer pid=1) INFO:     172.17.0.1:64850 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65235 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65238 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65237 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65236 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64850 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65235 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65238 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65236 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65237 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65238 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:24:14 [loggers.py:248] Engine 000: Avg prompt throughput: 5905.8 tokens/s, Avg generation throughput: 38.0 tokens/s, Running: 5 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.8%, Prefix cache hit rate: 81.3%
(APIServer pid=1) INFO:     172.17.0.1:65235 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65236 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65237 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64850 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65238 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65236 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65236 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65237 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65235 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:64850 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65238 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65236 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:24:24 [loggers.py:248] Engine 000: Avg prompt throughput: 8298.1 tokens/s, Avg generation throughput: 39.0 tokens/s, Running: 2 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.8%, Prefix cache hit rate: 84.8%
(APIServer pid=1) INFO:     172.17.0.1:65237 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:65235 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:24:34 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 3.8 tokens/s, Running: 0 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.0%, Prefix cache hit rate: 84.8%
(APIServer pid=1) INFO 03-18 14:24:44 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 0.0 tokens/s, Running: 0 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.0%, Prefix cache hit rate: 84.8%
(APIServer pid=1) INFO 03-18 14:28:44 [loggers.py:248] Engine 000: Avg prompt throughput: 76.0 tokens/s, Avg generation throughput: 5.6 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.2%, Prefix cache hit rate: 84.7%
(APIServer pid=1) INFO 03-18 14:28:54 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.4 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.3%, Prefix cache hit rate: 84.7%
(APIServer pid=1) INFO 03-18 14:29:04 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.3 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.3%, Prefix cache hit rate: 84.7%
(APIServer pid=1) INFO:     172.17.0.1:49222 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:29:14 [loggers.py:248] Engine 000: Avg prompt throughput: 654.8 tokens/s, Avg generation throughput: 6.9 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.0%, Prefix cache hit rate: 83.4%
(APIServer pid=1) INFO 03-18 14:29:24 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.0 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.0%, Prefix cache hit rate: 83.4%
(APIServer pid=1) INFO 03-18 14:29:34 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.0 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 2.0%, Prefix cache hit rate: 83.4%
(APIServer pid=1) INFO:     172.17.0.1:49222 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:29:44 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.3 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.7%, Prefix cache hit rate: 82.4%
(APIServer pid=1) INFO 03-18 14:29:54 [loggers.py:248] Engine 000: Avg prompt throughput: 529.1 tokens/s, Avg generation throughput: 9.0 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 1.6%, Prefix cache hit rate: 82.4%
(APIServer pid=1) INFO 03-18 14:30:04 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.0 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 1.6%, Prefix cache hit rate: 82.4%
(APIServer pid=1) INFO 03-18 14:30:14 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.0 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 1.7%, Prefix cache hit rate: 82.4%
(APIServer pid=1) INFO 03-18 14:30:24 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.0 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 1.7%, Prefix cache hit rate: 82.4%
(APIServer pid=1) INFO 03-18 14:30:34 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.0 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 1.7%, Prefix cache hit rate: 82.4%
(APIServer pid=1) INFO 03-18 14:30:44 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.0 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 1.8%, Prefix cache hit rate: 82.4%
(APIServer pid=1) INFO 03-18 14:30:54 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.9 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 1.8%, Prefix cache hit rate: 82.4%
(APIServer pid=1) INFO 03-18 14:31:04 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.9 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 1.8%, Prefix cache hit rate: 82.4%
(APIServer pid=1) INFO 03-18 14:31:14 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.0 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 1.9%, Prefix cache hit rate: 82.4%
(APIServer pid=1) INFO 03-18 14:31:24 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.9 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 1.9%, Prefix cache hit rate: 82.4%
(APIServer pid=1) INFO 03-18 14:31:34 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 10.0 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 1.9%, Prefix cache hit rate: 82.4%
(APIServer pid=1) INFO 03-18 14:31:44 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.9 tokens/s, Running: 1 reqs, Waiting: 0 reqs, GPU KV cache usage: 1.9%, Prefix cache hit rate: 82.4%
(APIServer pid=1) INFO:     172.17.0.1:49222 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:31:54 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 9.3 tokens/s, Running: 0 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.0%, Prefix cache hit rate: 82.4%
(APIServer pid=1) INFO:     172.17.0.1:49222 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49538 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49539 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49540 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49541 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49222 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49538 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49540 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49541 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49539 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49222 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49538 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:32:04 [loggers.py:248] Engine 000: Avg prompt throughput: 912.4 tokens/s, Avg generation throughput: 32.4 tokens/s, Running: 0 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.0%, Prefix cache hit rate: 82.0%
(APIServer pid=1) INFO:     172.17.0.1:49538 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49222 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49541 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49540 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49539 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49222 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49541 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49538 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49222 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49541 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:32:14 [loggers.py:248] Engine 000: Avg prompt throughput: 6625.1 tokens/s, Avg generation throughput: 42.3 tokens/s, Running: 4 reqs, Waiting: 0 reqs, GPU KV cache usage: 1.6%, Prefix cache hit rate: 83.3%
(APIServer pid=1) INFO:     172.17.0.1:49540 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49222 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49538 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO:     172.17.0.1:49539 - "POST /v1/chat/completions HTTP/1.1" 200 OK
(APIServer pid=1) INFO 03-18 14:32:24 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 3.4 tokens/s, Running: 0 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.0%, Prefix cache hit rate: 83.3%
(APIServer pid=1) INFO 03-18 14:32:34 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 0.0 tokens/s, Running: 0 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.0%, Prefix cache hit rate: 83.3%

