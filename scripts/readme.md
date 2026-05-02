what was the outcome? how do we start the mcp?                                        
                                                 
● Outcome                                                                               
                                               
  graphiti-mcp is now healthy and serving on http://promaxgb10-41b1:8004/mcp against    
  llama-swap (qwen-graphiti LLM + nomic-embed embeddings on :9000) and FalkorDB on the
  NAS (whitestocks:6379). The original symptom — Up 2 days (unhealthy) — was three      
  coupled issues: a stale HEALTHCHECK baked into the vendored Dockerfile (probing the
  wrong port), wrong model identifiers in the YAML (vLLM names where llama-swap expects
  its own aliases), and dead vllm-*.sh references in graphiti-stack-up.sh left over from
   the llama-swap migration. All fixed and verified live; runbook at
  docs/runbooks/RUNBOOK-INFRA-ORCHESTRATION.md.

  How to start the MCP

  Normal day-to-day (top-level, brings up everything in scope):                         
   
  cd ~/Projects/appmilla_github/guardkit                                                
  ./scripts/infra-up.sh                                           
  ./scripts/infra-status.sh   # confirm
                                                                                        
  Just the graphiti tier (skip the orchestrator):                                       
                                                                                        
  ./scripts/graphiti-stack-up.sh                                                        
                                                                  
  After a DGX-OS reboot (llama-swap may not be revived yet):                            
   
  sudo systemctl start llama-swap-keepalive.service   # one-shot revive                 
  ./scripts/infra-up.sh                                                                 
   
  To stop:                                                                              
                                                                  
  ./scripts/infra-down.sh        # leaves llama-swap running (shared with 
  autobuild/jarvis)                                                                     
  ./scripts/graphiti-stack-down.sh   # graphiti tier only
                                                                                        
  Healthy state shows: docker inspect graphiti-mcp --format '{{.State.Health.Status}}' =
   healthy, and a POST to http://promaxgb10-41b1:8004/mcp with an MCP initialize returns
   HTTP 200.                                          