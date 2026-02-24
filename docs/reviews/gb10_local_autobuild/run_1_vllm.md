(APIServer pid=1) INFO 02-23 13:47:02 [qwen3coder_tool_parser.py:83] vLLM Successfully import tool parser Qwen3CoderToolParser !
(APIServer pid=1) INFO:     172.17.0.1:39120 - "POST /v1/messages HTTP/1.1" 200 OK
(APIServer pid=1) INFO 02-23 13:47:03 [loggers.py:248] Engine 000: Avg prompt throughput: 1.9 tokens/s, Avg generation throughput: 1.1 tokens/s, Running: 0 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.0%, Prefix cache hit rate: 0.0%
(APIServer pid=1) INFO 02-23 13:47:13 [loggers.py:248] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 0.0 tokens/s, Running: 0 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.0%, Prefix cache hit rate: 0.0%
(APIServer pid=1) ERROR 02-23 13:48:05 [serving_chat.py:179] Error with model error=ErrorInfo(message='The model `claude-sonnet-4-6` does not exist.', type='NotFoundError', param=None, code=404)
(APIServer pid=1) INFO:     172.17.0.1:34980 - "POST /v1/messages?beta=true HTTP/1.1" 404 Not Found
(APIServer pid=1) ERROR 02-23 13:48:05 [serving_chat.py:179] Error with model error=ErrorInfo(message='The model `claude-sonnet-4-6` does not exist.', type='NotFoundError', param=None, code=404)
(APIServer pid=1) INFO:     172.17.0.1:34980 - "POST /v1/messages?beta=true HTTP/1.1" 404 Not Found

