# pattern-advisor - Extended Reference

This file contains detailed documentation for the `pattern-advisor` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/pattern-advisor-ext.md
```


## Pattern Recommendation Process

### Step 1: Extract Problem Context

Analyze the task requirements and implementation plan to understand:

**Functional Requirements**:
- What is the system supposed to do?
- What triggers the behavior? (event-driven, state-driven)
- What are the key interactions?

**Non-Functional Requirements (Constraints)**:
- Performance: latency, throughput
- Scalability: concurrent users, data volume
- Availability: uptime requirements
- Security: authentication, authorization, encryption
- Reliability: fault tolerance, resilience

**Technical Context**:
- Technology stack (Python, TypeScript, .NET, etc.)
- External dependencies (APIs, databases, message queues)
- Deployment environment (cloud, on-premise, hybrid)

**Example**:
```
EARS Requirement: "When payment is submitted, the system SHALL validate funds within 200ms"

EXTRACTED CONTEXT:
- Trigger: payment submission (event-driven)
- Action: validate funds
- Constraint: < 200ms response time (performance)
- External dependency: payment gateway (implied)

INFERRED CONSTRAINTS:
- High availability (payment is critical)
- Fault tolerance (external system may fail)
- Low latency (200ms is tight)
```

### Step 2: Query Design Patterns MCP

Use the appropriate MCP tool based on your query needs:

#### find_patterns (Semantic Search - Primary Tool)

Use for **problem-focused queries**:

```
Problem: "I need a pattern for handling external API failures gracefully with timeout constraints"

MCP Query:
{
  "problem_description": "Handle external API failures gracefully with timeout constraints under 200ms",
  "context": "Payment validation service calling external payment gateway",
  "preferences": {
    "language": "{stack}",
    "complexity": "low-to-medium"  // Prefer simpler patterns for MVP
  }
}
```

**Why this tool?**
- Uses vector embeddings for semantic matching
- Finds patterns by *problem solved*, not just keywords
- Returns ranked results with **confidence scores**
- Understands natural language descriptions

**Query Structure**:
```json
{
  "category": "Resilience | Performance | Security | Data Access | Architectural | Behavioral | Structural | Creational",
  "tags": ["retry", "circuit-breaker", "timeout"],
  "non_functional_requirements": ["response_time < 200ms", "fault-tolerant"],
  "stack": ["C#", ".NET 8"],
  "limit": 5  // IMPORTANT: Don't fetch too many (token budget)
}
```

**Token Budget Management**:
- Initial query: Limit to **5-7 patterns**
- Pattern details: Fetch **only top 3-4 candidates**
- Total tokens per session: ~15,000 max (leave room for implementation plan)

#### search_patterns (Keyword/Metadata Filtering)

Use for **category/tag-based queries**:

```
Scenario: "I know I need a resilience pattern, but not sure which one"

MCP Query:
{
  "query": "resilience fault-tolerance",
  "category": "Resilience",
  "tags": ["retry", "circuit-breaker", "timeout", "bulkhead"],
  "limit": 10
}
```

**Why this tool?**
- Fast filtering by metadata
- Good for exploratory searches
- Returns counts and summaries
- Less token-heavy than `find_patterns`

#### get_pattern_details (Deep Dive)

Use **after narrowing down candidates**:

```
Scenario: "Circuit Breaker looks promising, but I need implementation details for .NET 8"

MCP Query:
{
  "pattern_name": "Circuit Breaker",
  "stack": ["C#", ".NET 8"],
  "include_code_examples": true,
  "include_trade_offs": true
}
```

**Returns**:
- Full description
- UML diagrams (where applicable)
- Code examples (stack-specific)
- Trade-offs (when to use, when NOT to use)
- Related patterns
- Library recommendations (e.g., Polly for .NET, resilience4j for Java)

**Token Warning**:
- Each pattern detail response: ~1,500-3,000 tokens
- Fetch only **3-5 pattern details per session**
- Use `search_patterns` first to narrow candidates

#### count_patterns (Coverage Check)

Use for **reporting or broad searches**:

```
Scenario: "How many security patterns are available for Node.js?"

MCP Query:
{
  "category": "Security",
  "stack": ["Node.js"]
}

Returns:
{
  "count": 23
}
```

### Step 3: Rank and Filter Patterns

**Ranking Criteria**:
1. **Constraint Match (40%)**: Does it meet non-functional requirements?
   - Example: Circuit Breaker + Timeout for <200ms constraint
2. **Requirement Fit (30%)**: Does it solve the functional problem?
   - Example: Saga pattern for distributed transactions
3. **Stack Compatibility (20%)**: Is there a proven implementation?
   - Example: Polly for .NET resilience patterns
4. **Quality Score (10%)**: Pattern maturity, community adoption
   - Example: Repository pattern (mature) vs. experimental patterns

**Filter Out**:
- Patterns with low confidence (<0.60)
- Patterns requiring unavailable infrastructure
- Patterns beyond team's expertise (unless approved)
- Overly complex patterns for simple problems (YAGNI)

**Example Ranking**:
```
Task: Payment validation with < 200ms SLA, external API dependency

Found Patterns:
1. Circuit Breaker (confidence: 0.92) ✅
   - Constraint Match: 95% (prevents cascading failures, fast-fail)
   - Requirement Fit: 90% (handles external API failures)
   - Stack Compatibility: 100% (Polly for .NET)
   - Quality Score: 95% (industry standard)
   → RECOMMENDED (Primary)

2. Retry Pattern (confidence: 0.88) ✅
   - Constraint Match: 80% (retry adds latency, but configurable)
   - Requirement Fit: 85% (transient failure handling)
   - Stack Compatibility: 100% (Polly)
   - Quality Score: 90%
   → RECOMMENDED (Secondary, use with Circuit Breaker)

3. Timeout Pattern (confidence: 0.85) ✅
   - Constraint Match: 100% (enforces 200ms limit)
   - Requirement Fit: 70% (doesn't handle failure, just bounds it)
   - Stack Compatibility: 100% (built-in .NET)
   - Quality Score: 85%
   → RECOMMENDED (Primary, combine with Circuit Breaker)

4. Saga Pattern (confidence: 0.45) ❌
   - Constraint Match: 20% (adds complexity, increases latency)
   - Requirement Fit: 30% (overkill for single API call)
   - Stack Compatibility: 60% (requires orchestration framework)
   - Quality Score: 80%
   → NOT RECOMMENDED (YAGNI violation)
```

### Step 4: Validate Pattern Relationships

**Check for**:
- **Complementary patterns**: Work well together (Circuit Breaker + Retry + Timeout)
- **Conflicting patterns**: Contradict each other (Saga + 2PC for same transaction)
- **Dependencies**: One pattern requires another (CQRS requires separate read/write models)

**Example Validation**:
```
Recommended Patterns:
- Circuit Breaker
- Retry (with exponential backoff)
- Timeout (200ms)

VALIDATION:
✅ Complementary: Yes (standard resilience triad)
❌ Conflicts: None
⚠️ Order matters:
   1. Timeout (innermost - bounds each attempt)
   2. Retry (middle - retries failed attempts)
   3. Circuit Breaker (outermost - prevents retry storms)

IMPLEMENTATION NOTE:
Use Polly's Policy Wrap to compose in correct order:
Policy.Wrap(circuitBreaker, retry, timeout)
```

### Step 5: Generate Recommendations

**Output Format**:

---


## 🎯 Design Pattern Recommendations for TASK-042

**Context**: Payment validation service with < 200ms SLA, external gateway dependency

---

### Primary Patterns (Strongly Recommended)

#### 1. Circuit Breaker Pattern (Confidence: 0.92)

**Why this pattern?**
- **Problem**: External payment gateway may fail or become unresponsive, causing cascading failures
- **Solution**: Circuit breaker detects failures and "opens" to prevent further calls, allowing system to degrade gracefully
- **Benefit**: Protects your service from waiting on failed downstream dependencies

**Stack-Specific Implementation (.NET 8 + Polly)**:
```csharp
var circuitBreakerPolicy = Policy
    .Handle<HttpRequestException>()
    .CircuitBreakerAsync(
        exceptionsAllowedBeforeBreaking: 3,
        durationOfBreak: TimeSpan.FromSeconds(30)
    );

var result = await circuitBreakerPolicy.ExecuteAsync(async () =>
{
    return await _paymentGatewayClient.ValidateFundsAsync(request);
});
```

**Trade-offs**:
- ✅ Prevents cascading failures
- ✅ Fast-fail when circuit is open (saves latency)
- ❌ Requires monitoring/alerting (how do you know circuit opened?)
- ❌ Temporary service disruption when circuit opens

**Related Patterns**:
- Combine with **Retry** (for transient failures before circuit opens)
- Combine with **Timeout** (to bound wait time per attempt)
- Combine with **Fallback** (provide default behavior when circuit is open)

**Configuration Guidance**:
- `exceptionsAllowedBeforeBreaking`: 3-5 (balance sensitivity vs. false positives)
- `durationOfBreak`: 30-60 seconds (allow downstream time to recover)
- Monitor: Circuit state, failure rate, break duration

---

#### 2. Timeout Pattern (Confidence: 0.85)

**Why this pattern?**
- **Problem**: 200ms SLA requires bounding wait time on external calls
- **Solution**: Enforce maximum wait time, fail fast if exceeded
- **Benefit**: Prevents slow external services from violating your SLA

**Stack-Specific Implementation (.NET 8)**:
```csharp
var timeoutPolicy = Policy
    .TimeoutAsync(TimeSpan.FromMilliseconds(180), TimeoutStrategy.Pessimistic);

// Wrap with circuit breaker
var combinedPolicy = Policy.WrapAsync(circuitBreakerPolicy, timeoutPolicy);

var result = await combinedPolicy.ExecuteAsync(async () =>
{
    return await _paymentGatewayClient.ValidateFundsAsync(request);
});
```

**Trade-offs**:
- ✅ Guarantees SLA compliance (fails fast rather than exceeding SLA)
- ✅ Simple to implement
- ❌ May cancel successful-but-slow requests
- ❌ Requires careful timeout tuning (too short = false failures)

**Configuration Guidance**:
- Timeout: 180ms (leaves 20ms buffer for processing)
- Strategy: `Pessimistic` (cancels operation aggressively)
- Monitor: Timeout occurrences (indicates gateway performance issues)

---

### Secondary Patterns (Consider If Applicable)

#### 3. Retry Pattern with Exponential Backoff (Confidence: 0.88)

**Why this pattern?**
- **Problem**: Transient failures (network blips, temporary gateway overload) shouldn't fail the request
- **Solution**: Retry failed requests with increasing delays
- **Benefit**: Improves success rate for transient failures

**Stack-Specific Implementation (.NET 8 + Polly)**:
```csharp
var retryPolicy = Policy
    .Handle<HttpRequestException>()
    .WaitAndRetryAsync(
        retryCount: 2,
        sleepDurationProvider: attempt => TimeSpan.FromMilliseconds(50 * Math.Pow(2, attempt)),
        onRetry: (exception, timeSpan, retryCount, context) =>
        {
            _logger.LogWarning($"Retry {retryCount} after {timeSpan.TotalMilliseconds}ms");
        }
    );

// Compose: Circuit Breaker → Retry → Timeout
var policy = Policy.WrapAsync(circuitBreakerPolicy, retryPolicy, timeoutPolicy);
```

**Trade-offs**:
- ✅ Improves reliability for transient failures
- ✅ Exponential backoff prevents thundering herd
- ❌ Adds latency (each retry takes time)
- ❌ Must fit within 200ms SLA (limit retry count)

**Configuration Guidance**:
- Retry count: 2 max (to stay within SLA)
- Initial delay: 50ms
- Backoff: Exponential (50ms, 100ms)
- Total max time: ~150ms (leaves room for initial attempt)

**CAUTION**:
- Only retry **idempotent operations** (safe to execute multiple times)
- Validate that payment gateway supports idempotency (check docs)

---

### Pattern Validation Summary

**Complementary Patterns**:
- Circuit Breaker + Retry + Timeout = **Resilience Triad** (industry standard)
- Order matters: Wrap as `Policy.Wrap(circuitBreaker, retry, timeout)`

**Conflicting Patterns**: None

**Dependencies**:
- All three patterns require **Polly** NuGet package
- Circuit breaker requires **monitoring/alerting** (use Application Insights, Datadog, etc.)

**Complexity Assessment**:
- Low-Medium (Polly simplifies implementation)
- Team should be familiar with async/await patterns
- Configuration requires performance testing (tune timeouts, retry counts)

---


## Pattern Query Examples

### Example 1: Performance Constraint
```
TASK: "Reduce dashboard load time from 3s to 500ms"

MCP Query:
{
  "category": "Performance",
  "non_functional_requirements": ["response_time < 500ms"],
  "context": "Dashboard aggregates data from 5 microservices",
  "stack": ["C#", ".NET 8", "Redis"],
  "limit": 5
}

Expected Patterns:
- Caching (read-through, write-behind)
- Lazy Loading
- Parallel Execution
- BFF (Backend for Frontend)
- API Gateway (aggregation)
```

### Example 2: Scalability Requirement
```
TASK: "Support 10,000 concurrent users"

MCP Query:
{
  "category": "Scalability",
  "non_functional_requirements": ["concurrent_users >= 10000"],
  "context": "E-commerce product catalog",
  "stack": ["Node.js", "PostgreSQL", "Redis"],
  "limit": 5
}

Expected Patterns:
- CQRS (separate read/write models)
- Event Sourcing (if high write volume)
- Sharding (database partitioning)
- Load Balancing
- Caching (CDN for static content)
```

### Example 3: Security Requirement
```
TASK: "Implement multi-tenant data isolation"

MCP Query:
{
  "category": "Security",
  "tags": ["multi-tenancy", "data-isolation"],
  "context": "SaaS application with sensitive customer data",
  "stack": ["Python", "Django", "PostgreSQL"],
  "limit": 5
}

Expected Patterns:
- Tenant Isolation (database per tenant, schema per tenant, row-level security)
- Claims-Based Authorization
- Role-Based Access Control (RBAC)
- Data Encryption (at rest, in transit)
```


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat pattern-advisor-ext.md
```

Or in Claude Code:
```
Please read pattern-advisor-ext.md for detailed examples.
```
