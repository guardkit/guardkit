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
(APIServer pid=1) INFO 03-18 13:29:09 [api_server.py:1354] vLLM API server version 0.13.0+faa43dbf.nv26.01
(APIServer pid=1) INFO 03-18 13:29:09 [utils.py:253] non-default args: {'model_tag': 'Qwen/Qwen2.5-14B-Instruct-FP8', 'host': '0.0.0.0', 'model': 'Qwen/Qwen2.5-14B-Instruct-FP8', 'max_model_len': 32768, 'gpu_memory_utilization': 0.15, 'kv_cache_dtype': 'fp8', 'enable_prefix_caching': True, 'structured_outputs_config': StructuredOutputsConfig(backend='xgrammar', disable_fallback=False, disable_any_whitespace=False, disable_additional_properties=False, reasoning_parser='', reasoning_parser_plugin='', enable_in_reasoning=False)}
(APIServer pid=1) Traceback (most recent call last):
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/huggingface_hub/utils/_http.py", line 402, in hf_raise_for_status
(APIServer pid=1)     response.raise_for_status()
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/requests/models.py", line 1026, in raise_for_status
(APIServer pid=1)     raise HTTPError(http_error_msg, response=self)
(APIServer pid=1) requests.exceptions.HTTPError: 401 Client Error: Unauthorized for url: https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-FP8/resolve/main/config.json
(APIServer pid=1) 
(APIServer pid=1) The above exception was the direct cause of the following exception:
(APIServer pid=1) 
(APIServer pid=1) Traceback (most recent call last):
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/transformers/utils/hub.py", line 479, in cached_files
(APIServer pid=1)     hf_hub_download(
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/huggingface_hub/utils/_validators.py", line 114, in _inner_fn
(APIServer pid=1)     return fn(*args, **kwargs)
(APIServer pid=1)            ^^^^^^^^^^^^^^^^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/huggingface_hub/file_download.py", line 1007, in hf_hub_download
(APIServer pid=1)     return _hf_hub_download_to_cache_dir(
(APIServer pid=1)            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/huggingface_hub/file_download.py", line 1114, in _hf_hub_download_to_cache_dir
(APIServer pid=1)     _raise_on_head_call_error(head_call_error, force_download, local_files_only)
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/huggingface_hub/file_download.py", line 1655, in _raise_on_head_call_error
(APIServer pid=1)     raise head_call_error
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/huggingface_hub/file_download.py", line 1543, in _get_metadata_or_catch_error
(APIServer pid=1)     metadata = get_hf_file_metadata(
(APIServer pid=1)                ^^^^^^^^^^^^^^^^^^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/huggingface_hub/utils/_validators.py", line 114, in _inner_fn
(APIServer pid=1)     return fn(*args, **kwargs)
(APIServer pid=1)            ^^^^^^^^^^^^^^^^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/huggingface_hub/file_download.py", line 1460, in get_hf_file_metadata
(APIServer pid=1)     r = _request_wrapper(
(APIServer pid=1)         ^^^^^^^^^^^^^^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/huggingface_hub/file_download.py", line 283, in _request_wrapper
(APIServer pid=1)     response = _request_wrapper(
(APIServer pid=1)                ^^^^^^^^^^^^^^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/huggingface_hub/file_download.py", line 307, in _request_wrapper
(APIServer pid=1)     hf_raise_for_status(response)
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/huggingface_hub/utils/_http.py", line 452, in hf_raise_for_status
(APIServer pid=1)     raise _format(RepositoryNotFoundError, message, response) from e
(APIServer pid=1) huggingface_hub.errors.RepositoryNotFoundError: 401 Client Error. (Request ID: Root=1-69baa8a6-7bae638e1ddf13c72009d643;6f53fe31-d0e7-4e86-b8a4-ef40cb1f3a55)
(APIServer pid=1) 
(APIServer pid=1) Repository Not Found for url: https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-FP8/resolve/main/config.json.
(APIServer pid=1) Please make sure you specified the correct `repo_id` and `repo_type`.
(APIServer pid=1) If you are trying to access a private or gated repo, make sure you are authenticated. For more details, see https://huggingface.co/docs/huggingface_hub/authentication
(APIServer pid=1) Invalid username or password.
(APIServer pid=1) 
(APIServer pid=1) The above exception was the direct cause of the following exception:
(APIServer pid=1) 
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
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/vllm/entrypoints/openai/api_server.py", line 200, in build_async_engine_client_from_engine_args
(APIServer pid=1)     vllm_config = engine_args.create_engine_config(usage_context=usage_context)
(APIServer pid=1)                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/vllm/engine/arg_utils.py", line 1323, in create_engine_config
(APIServer pid=1)     maybe_override_with_speculators(
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/vllm/transformers_utils/config.py", line 508, in maybe_override_with_speculators
(APIServer pid=1)     config_dict, _ = PretrainedConfig.get_config_dict(
(APIServer pid=1)                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/transformers/configuration_utils.py", line 662, in get_config_dict
(APIServer pid=1)     config_dict, kwargs = cls._get_config_dict(pretrained_model_name_or_path, **kwargs)
(APIServer pid=1)                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/transformers/configuration_utils.py", line 721, in _get_config_dict
(APIServer pid=1)     resolved_config_file = cached_file(
(APIServer pid=1)                            ^^^^^^^^^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/transformers/utils/hub.py", line 322, in cached_file
(APIServer pid=1)     file = cached_files(path_or_repo_id=path_or_repo_id, filenames=[filename], **kwargs)
(APIServer pid=1)            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(APIServer pid=1)   File "/usr/local/lib/python3.12/dist-packages/transformers/utils/hub.py", line 511, in cached_files
(APIServer pid=1)     raise OSError(
(APIServer pid=1) OSError: Qwen/Qwen2.5-14B-Instruct-FP8 is not a local folder and is not a valid model identifier listed on 'https://huggingface.co/models'
(APIServer pid=1) If this is a private repository, make sure to pass a token having permission to this repo either by logging in with `hf auth login` or by passing `token=<your_token>`
richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/guardkit/scripts$ 
