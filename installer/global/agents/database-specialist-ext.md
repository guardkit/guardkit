# database-specialist - Extended Reference

This file contains detailed documentation for the `database-specialist` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/database-specialist-ext.md
```


## Implementation Patterns

### PostgreSQL Advanced Schema Design
```sql
-- Multi-tenant database with Row Level Security
CREATE SCHEMA IF NOT EXISTS app;

-- Tenant table
CREATE TABLE app.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    subdomain VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(50) NOT NULL DEFAULT 'free',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true
);

-- Users table with tenant association
CREATE TABLE app.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES app.tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(100),
    password_hash VARCHAR(255) NOT NULL,
    profile JSONB DEFAULT '{}',
    roles TEXT[] DEFAULT ARRAY['user'],
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, email),
    UNIQUE(tenant_id, username)
);

-- Products table with soft delete and versioning
CREATE TABLE app.products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES app.tenants(id) ON DELETE CASCADE,
    sku VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    cost DECIMAL(10,2) CHECK (cost >= 0),
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    version INTEGER NOT NULL DEFAULT 1,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES app.users(id),
    updated_by UUID REFERENCES app.users(id),
    UNIQUE(tenant_id, sku, version)
);

-- Audit log table
CREATE TABLE app.audit_logs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID,
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
) PARTITION BY RANGE (created_at);

-- Create monthly partitions for audit logs
CREATE TABLE app.audit_logs_2024_01 PARTITION OF app.audit_logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE app.audit_logs_2024_02 PARTITION OF app.audit_logs
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Indexes for performance
CREATE INDEX idx_users_tenant_email ON app.users(tenant_id, email);
CREATE INDEX idx_users_tenant_created ON app.users(tenant_id, created_at DESC);
CREATE INDEX idx_products_tenant_sku ON app.products(tenant_id, sku) WHERE NOT is_deleted;
CREATE INDEX idx_products_tenant_tags ON app.products USING GIN(tags) WHERE NOT is_deleted;
CREATE INDEX idx_products_metadata ON app.products USING GIN(metadata);
CREATE INDEX idx_audit_logs_tenant_created ON app.audit_logs(tenant_id, created_at DESC);
CREATE INDEX idx_audit_logs_table_record ON app.audit_logs(table_name, record_id);

-- Full-text search
ALTER TABLE app.products ADD COLUMN search_vector tsvector;

UPDATE app.products SET search_vector = 
    setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(array_to_string(tags, ' '), '')), 'C');

CREATE INDEX idx_products_search ON app.products USING GIN(search_vector);

-- Trigger to update search vector
CREATE OR REPLACE FUNCTION app.update_search_vector() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', coalesce(NEW.name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(array_to_string(NEW.tags, ' '), '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_products_search_vector 
    BEFORE INSERT OR UPDATE ON app.products
    FOR EACH ROW EXECUTE FUNCTION app.update_search_vector();

-- Row Level Security
ALTER TABLE app.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.products ENABLE ROW LEVEL SECURITY;

-- Policy for tenant isolation
CREATE POLICY tenant_isolation_policy ON app.users
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_policy ON app.products
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Updated timestamp trigger
CREATE OR REPLACE FUNCTION app.update_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON app.users
    FOR EACH ROW EXECUTE FUNCTION app.update_updated_at();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON app.products
    FOR EACH ROW EXECUTE FUNCTION app.update_updated_at();

-- Audit trigger
CREATE OR REPLACE FUNCTION app.audit_trigger() RETURNS trigger AS $$
DECLARE
    audit_row app.audit_logs;
    changed_fields JSONB = '{}';
BEGIN
    audit_row.table_name = TG_TABLE_NAME;
    audit_row.user_id = current_setting('app.current_user', true)::uuid;
    audit_row.tenant_id = current_setting('app.current_tenant', true)::uuid;
    audit_row.action = TG_OP;
    
    IF TG_OP = 'DELETE' THEN
        audit_row.record_id = OLD.id;
        audit_row.old_values = to_jsonb(OLD);
    ELSIF TG_OP = 'UPDATE' THEN
        audit_row.record_id = NEW.id;
        audit_row.old_values = to_jsonb(OLD);
        audit_row.new_values = to_jsonb(NEW);
        
        -- Track only changed fields
        SELECT jsonb_object_agg(key, value) INTO changed_fields
        FROM jsonb_each(to_jsonb(NEW))
        WHERE to_jsonb(NEW) -> key IS DISTINCT FROM to_jsonb(OLD) -> key;
        
        audit_row.new_values = changed_fields;
    ELSIF TG_OP = 'INSERT' THEN
        audit_row.record_id = NEW.id;
        audit_row.new_values = to_jsonb(NEW);
    END IF;
    
    INSERT INTO app.audit_logs VALUES (audit_row.*);
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_users AFTER INSERT OR UPDATE OR DELETE ON app.users
    FOR EACH ROW EXECUTE FUNCTION app.audit_trigger();

CREATE TRIGGER audit_products AFTER INSERT OR UPDATE OR DELETE ON app.products
    FOR EACH ROW EXECUTE FUNCTION app.audit_trigger();
```

### Query Optimization Patterns
```sql
-- Optimized pagination with cursor
CREATE OR REPLACE FUNCTION app.get_products_paginated(
    p_tenant_id UUID,
    p_cursor TIMESTAMPTZ DEFAULT NULL,
    p_limit INTEGER DEFAULT 20
) RETURNS TABLE (
    id UUID,
    name VARCHAR,
    price DECIMAL,
    created_at TIMESTAMPTZ,
    total_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    WITH filtered_products AS (
        SELECT 
            p.id,
            p.name,
            p.price,
            p.created_at,
            COUNT(*) OVER() as total_count
        FROM app.products p
        WHERE p.tenant_id = p_tenant_id
            AND NOT p.is_deleted
            AND (p_cursor IS NULL OR p.created_at < p_cursor)
        ORDER BY p.created_at DESC
        LIMIT p_limit
    )
    SELECT * FROM filtered_products;
END;
$$ LANGUAGE plpgsql;

-- Materialized view for analytics
CREATE MATERIALIZED VIEW app.product_analytics AS
SELECT 
    tenant_id,
    DATE_TRUNC('day', created_at) as date,
    COUNT(*) as products_created,
    AVG(price) as avg_price,
    SUM(quantity) as total_inventory,
    SUM(price * quantity) as inventory_value
FROM app.products
WHERE NOT is_deleted
GROUP BY tenant_id, DATE_TRUNC('day', created_at);

CREATE UNIQUE INDEX ON app.product_analytics(tenant_id, date);

-- Refresh materialized view
CREATE OR REPLACE FUNCTION app.refresh_analytics() RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY app.product_analytics;
END;
$$ LANGUAGE plpgsql;

-- Common Table Expression for complex queries
WITH RECURSIVE category_tree AS (
    -- Anchor: top-level categories
    SELECT 
        id,
        name,
        parent_id,
        1 as level,
        ARRAY[id] as path,
        name as full_path
    FROM categories
    WHERE parent_id IS NULL
    
    UNION ALL
    
    -- Recursive: child categories
    SELECT 
        c.id,
        c.name,
        c.parent_id,
        ct.level + 1,
        ct.path || c.id,
        ct.full_path || ' > ' || c.name
    FROM categories c
    INNER JOIN category_tree ct ON c.parent_id = ct.id
    WHERE ct.level < 5  -- Prevent infinite recursion
)
SELECT * FROM category_tree ORDER BY path;
```

### MongoDB Schema Design
```javascript
// MongoDB schema design for e-commerce
// Product collection with embedded and referenced data
const productSchema = {
  _id: ObjectId(),
  tenantId: ObjectId(),
  sku: "PROD-001",
  name: "Product Name",
  slug: "product-name",
  description: "Product description",
  
  // Embedded for performance
  pricing: {
    currency: "USD",
    basePrice: 99.99,
    salePrice: 79.99,
    cost: 45.00,
    taxRate: 0.08,
    discounts: [
      {
        type: "percentage",
        value: 20,
        validFrom: ISODate("2024-01-01"),
        validTo: ISODate("2024-12-31"),
        code: "SAVE20"
      }
    ]
  },
  
  // Denormalized for query performance
  category: {
    _id: ObjectId(),
    name: "Electronics",
    path: ["Electronics", "Computers", "Laptops"],
    slug: "electronics/computers/laptops"
  },
  
  // Array of embedded documents
  variants: [
    {
      _id: ObjectId(),
      sku: "PROD-001-RED-M",
      attributes: {
        color: "Red",
        size: "Medium"
      },
      inventory: {
        quantity: 50,
        reserved: 5,
        available: 45
      },
      pricing: {
        basePrice: 99.99,
        salePrice: 79.99
      }
    }
  ],
  
  // Reference to separate collection for large data
  reviews: {
    count: 125,
    average: 4.5,
    distribution: {
      5: 75,
      4: 30,
      3: 15,
      2: 3,
      1: 2
    },
    // Store only recent reviews
    recent: [
      {
        userId: ObjectId(),
        userName: "John Doe",
        rating: 5,
        comment: "Great product!",
        createdAt: ISODate()
      }
    ]
  },
  
  // Metadata and search
  tags: ["electronics", "laptop", "gaming"],
  searchKeywords: ["laptop", "computer", "gaming", "portable"],
  
  // Timestamps and versioning
  version: 1,
  createdAt: ISODate(),
  updatedAt: ISODate(),
  createdBy: ObjectId(),
  updatedBy: ObjectId(),
  
  // Soft delete
  isDeleted: false,
  deletedAt: null
};

// Indexes for optimal performance
db.products.createIndex({ tenantId: 1, sku: 1 }, { unique: true });
db.products.createIndex({ tenantId: 1, slug: 1 }, { unique: true });
db.products.createIndex({ tenantId: 1, "category._id": 1 });
db.products.createIndex({ tenantId: 1, tags: 1 });
db.products.createIndex({ 
  name: "text", 
  description: "text", 
  searchKeywords: "text" 
}, {
  weights: {
    name: 10,
    searchKeywords: 5,
    description: 1
  }
});
db.products.createIndex({ tenantId: 1, createdAt: -1 });
db.products.createIndex({ tenantId: 1, "pricing.salePrice": 1 });

// Aggregation pipeline for analytics
db.products.aggregate([
  // Match tenant and active products
  {
    $match: {
      tenantId: ObjectId("..."),
      isDeleted: false
    }
  },
  
  // Unwind variants for inventory calculation
  {
    $unwind: "$variants"
  },
  
  // Group by category
  {
    $group: {
      _id: "$category._id",
      categoryName: { $first: "$category.name" },
      productCount: { $sum: 1 },
      totalInventory: { $sum: "$variants.inventory.quantity" },
      avgPrice: { $avg: "$pricing.basePrice" },
      minPrice: { $min: "$pricing.basePrice" },
      maxPrice: { $max: "$pricing.basePrice" }
    }
  },
  
  // Sort by product count
  {
    $sort: { productCount: -1 }
  },
  
  // Add computed fields
  {
    $addFields: {
      priceRange: {
        $concat: [
          "$", { $toString: "$minPrice" },
          " - $", { $toString: "$maxPrice" }
        ]
      }
    }
  }
]);

// Change streams for real-time updates
const changeStream = db.products.watch(
  [
    {
      $match: {
        $and: [
          { "fullDocument.tenantId": tenantId },
          { operationType: { $in: ["insert", "update", "delete"] } }
        ]
      }
    }
  ],
  { fullDocument: "updateLookup" }
);

changeStream.on("change", (change) => {
  console.log("Product changed:", change);
  // Handle real-time updates
});
```

### Redis Caching Strategies
```python

# redis_cache.py
import redis
import json
import hashlib
from typing import Any, Optional, List, Dict
from datetime import timedelta
import pickle

class RedisCache:
    """Advanced Redis caching with multiple strategies"""
    
    def __init__(self, host='localhost', port=6379, db=0):
        self.redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=False,  # Handle bytes for complex objects
            connection_pool=redis.ConnectionPool(
                max_connections=50,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 1,  # TCP_KEEPINTVL
                    3: 5,  # TCP_KEEPCNT
                }
            )
        )
        self.pipeline = self.redis.pipeline()
    
    # Cache patterns
    def cache_aside(self, key: str, fetch_func, ttl: int = 3600) -> Any:
        """Cache-aside pattern (lazy loading)"""
        # Try to get from cache
        cached = self.redis.get(key)
        if cached:
            return pickle.loads(cached)
        
        # Fetch from source
        data = fetch_func()
        
        # Store in cache
        self.redis.setex(key, ttl, pickle.dumps(data))
        return data
    
    def write_through(self, key: str, data: Any, persist_func, ttl: int = 3600):
        """Write-through pattern"""
        # Write to cache
        self.redis.setex(key, ttl, pickle.dumps(data))
        
        # Write to persistent storage
        persist_func(data)
    
    def write_behind(self, key: str, data: Any, ttl: int = 3600):
        """Write-behind pattern (write-back)"""
        # Write to cache immediately
        self.redis.setex(key, ttl, pickle.dumps(data))
        
        # Queue for async write to persistent storage
        self.redis.lpush('write_queue', json.dumps({
            'key': key,
            'data': data,
            'timestamp': time.time()
        }))
    
    # Advanced caching strategies
    def cache_with_refresh(self, key: str, fetch_func, ttl: int = 3600, 
                          refresh_ttl: int = 3000) -> Any:
        """Proactive cache refresh before expiration"""
        cached = self.redis.get(key)
        remaining_ttl = self.redis.ttl(key)
        
        if cached:
            # Refresh if close to expiration
            if remaining_ttl < (ttl - refresh_ttl):
                # Async refresh in background
                self.redis.lpush('refresh_queue', json.dumps({
                    'key': key,
                    'fetch_func': fetch_func.__name__
                }))
            return pickle.loads(cached)
        
        # Initial fetch
        data = fetch_func()
        self.redis.setex(key, ttl, pickle.dumps(data))
        return data
    
    def distributed_lock(self, lock_name: str, timeout: int = 10) -> bool:
        """Distributed locking with Redis"""
        identifier = str(uuid.uuid4())
        lock_key = f"lock:{lock_name}"
        
        # Try to acquire lock
        if self.redis.set(lock_key, identifier, nx=True, ex=timeout):
            return identifier
        return None
    
    def release_lock(self, lock_name: str, identifier: str) -> bool:
        """Release distributed lock"""
        lock_key = f"lock:{lock_name}"
        
        # Lua script for atomic check and delete
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        return self.redis.eval(lua_script, 1, lock_key, identifier)
    
    # Query result caching
    def cache_query_result(self, query: str, params: Dict, result: Any, 
                          ttl: int = 300):
        """Cache database query results"""
        # Generate cache key from query and params
        cache_key = self._generate_query_key(query, params)
        
        # Store with metadata
        cache_data = {
            'result': result,
            'query': query,
            'params': params,
            'cached_at': time.time()
        }
        
        self.redis.setex(cache_key, ttl, pickle.dumps(cache_data))
    
    def get_cached_query(self, query: str, params: Dict) -> Optional[Any]:
        """Retrieve cached query result"""
        cache_key = self._generate_query_key(query, params)
        cached = self.redis.get(cache_key)
        
        if cached:
            data = pickle.loads(cached)
            return data['result']
        return None
    
    def _generate_query_key(self, query: str, params: Dict) -> str:
        """Generate deterministic cache key from query"""
        query_hash = hashlib.sha256(
            f"{query}:{json.dumps(params, sort_keys=True)}".encode()
        ).hexdigest()
        return f"query:{query_hash}"
    
    # Session management
    def store_session(self, session_id: str, data: Dict, ttl: int = 1800):
        """Store user session data"""
        key = f"session:{session_id}"
        self.redis.hset(key, mapping=data)
        self.redis.expire(key, ttl)
    
    def get_session(self, session_id: str) -> Dict:
        """Retrieve session data"""
        key = f"session:{session_id}"
        return self.redis.hgetall(key)
    
    def extend_session(self, session_id: str, ttl: int = 1800):
        """Extend session TTL"""
        key = f"session:{session_id}"
        self.redis.expire(key, ttl)
    
    # Rate limiting
    def check_rate_limit(self, identifier: str, limit: int = 100, 
                         window: int = 3600) -> bool:
        """Token bucket rate limiting"""
        key = f"rate_limit:{identifier}"
        
        try:
            current = self.redis.incr(key)
            if current == 1:
                self.redis.expire(key, window)
            
            return current <= limit
        except redis.RedisError:
            return True  # Fail open
    
    # Cache invalidation
    def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern"""
        cursor = 0
        while True:
            cursor, keys = self.redis.scan(cursor, match=pattern, count=100)
            if keys:
                self.redis.delete(*keys)
            if cursor == 0:
                break
    
    def invalidate_tags(self, tags: List[str]):
        """Tag-based cache invalidation"""
        for tag in tags:
            members = self.redis.smembers(f"tag:{tag}")
            if members:
                self.redis.delete(*members)
                self.redis.delete(f"tag:{tag}")
    
    def tag_cache_entry(self, key: str, tags: List[str]):
        """Tag a cache entry for group invalidation"""
        for tag in tags:
            self.redis.sadd(f"tag:{tag}", key)
```

### Database Migration Strategy
```python

# migrations/migration_runner.py
import os
import hashlib
from datetime import datetime
from typing import List, Dict, Any
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

class DatabaseMigration:
    """Database migration system with rollback support"""
    
    def __init__(self, connection_string: str):
        self.conn = psycopg2.connect(connection_string)
        self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        self.cursor = self.conn.cursor()
        self._ensure_migration_table()
    
    def _ensure_migration_table(self):
        """Create migration tracking table"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                checksum VARCHAR(64) NOT NULL,
                executed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms INTEGER,
                rolled_back BOOLEAN DEFAULT FALSE,
                rolled_back_at TIMESTAMPTZ
            )
        """)
    
    def run_migrations(self, migrations_dir: str):
        """Run all pending migrations"""
        migrations = self._get_migration_files(migrations_dir)
        
        for migration_file in migrations:
            version = self._extract_version(migration_file)
            
            if not self._is_migration_applied(version):
                self._apply_migration(migration_file, version)
    
    def _apply_migration(self, file_path: str, version: str):
        """Apply a single migration"""
        print(f"Applying migration {version}...")
        
        with open(file_path, 'r') as f:
            sql = f.read()
        
        checksum = hashlib.sha256(sql.encode()).hexdigest()
        start_time = datetime.now()
        
        try:
            # Split migration into up and down parts
            parts = sql.split('-- DOWN')
            up_sql = parts[0].replace('-- UP', '').strip()
            
            # Execute migration
            self.cursor.execute(up_sql)
            
            # Record migration
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            self.cursor.execute("""
                INSERT INTO schema_migrations (version, name, checksum, execution_time_ms)
                VALUES (%s, %s, %s, %s)
            """, (version, os.path.basename(file_path), checksum, execution_time))
            
            print(f"Migration {version} applied successfully in {execution_time}ms")
            
        except Exception as e:
            print(f"Error applying migration {version}: {e}")
            raise
    
    def rollback_migration(self, version: str):
        """Rollback a specific migration"""
        print(f"Rolling back migration {version}...")
        
        # Get migration file
        migration_file = self._find_migration_file(version)
        
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        # Extract down migration
        if '-- DOWN' in sql:
            down_sql = sql.split('-- DOWN')[1].strip()
            
            try:
                self.cursor.execute(down_sql)
                
                # Mark as rolled back
                self.cursor.execute("""
                    UPDATE schema_migrations 
                    SET rolled_back = TRUE, rolled_back_at = CURRENT_TIMESTAMP
                    WHERE version = %s
                """, (version,))
                
                print(f"Migration {version} rolled back successfully")
                
            except Exception as e:
                print(f"Error rolling back migration {version}: {e}")
                raise
        else:
            print(f"No rollback defined for migration {version}")
    
    def _is_migration_applied(self, version: str) -> bool:
        """Check if migration has been applied"""
        self.cursor.execute("""
            SELECT 1 FROM schema_migrations 
            WHERE version = %s AND NOT rolled_back
        """, (version,))
        return self.cursor.fetchone() is not None
    
    def _get_migration_files(self, directory: str) -> List[str]:
        """Get sorted list of migration files"""
        files = []
        for filename in os.listdir(directory):
            if filename.endswith('.sql'):
                files.append(os.path.join(directory, filename))
        return sorted(files)
    
    def _extract_version(self, file_path: str) -> str:
        """Extract version from filename"""
        filename = os.path.basename(file_path)
        return filename.split('_')[0]

# Example migration file: 001_create_users_table.sql
"""
-- UP
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);

-- DOWN
DROP TABLE IF EXISTS users;
"""
```

### Database Design
1. Normalize to 3NF, then denormalize for performance
2. Use appropriate data types
3. Implement proper constraints
4. Design for scalability from the start
5. Consider multi-tenancy requirements
6. Plan for data archival

### Performance Optimization
1. Profile queries before optimizing
2. Use appropriate indexes
3. Avoid N+1 queries
4. Implement connection pooling
5. Use read replicas for scaling
6. Cache frequently accessed data

### Data Integrity
1. Use transactions appropriately
2. Implement foreign key constraints
3. Use check constraints for validation
4. Maintain audit trails
5. Implement soft deletes when needed
6. Regular consistency checks

### Backup & Recovery
1. Automated regular backups
2. Test restore procedures
3. Point-in-time recovery capability
4. Geographic redundancy
5. Document recovery procedures
6. Monitor backup health


## Related Agents

### Integration with software-architect

**Purpose**: Align database schema design with system architecture patterns.

**Handoff Pattern**:
```yaml
flow:
  - actor: software-architect
    action: designs_system_architecture
    output:
      - architectural_patterns: [microservices, event-driven, CQRS]
      - scalability_requirements: {read_heavy: true, write_qps: 5000}

  - actor: database-specialist
    action: designs_database_schema
    input: architectural_patterns, scalability_requirements
    output:
      - schema_design: {tables: [...], indexes: [...]}
      - database_selection: PostgreSQL + Redis
      - partitioning_strategy: horizontal_sharding

  - actor: software-architect
    action: validates_alignment
    checks:
      - schema supports bounded contexts
      - read replicas align with scaling needs
```

**Example Handoff Payload**:
```json
{
  "from_agent": "software-architect",
  "to_agent": "database-specialist",
  "task": "design_database_schema",
  "context": {
    "architecture_pattern": "microservices",
    "services": [
      {
        "name": "user-service",
        "data_ownership": ["users", "profiles"],
        "access_patterns": {"read_heavy": true, "write_qps": 200}
      }
    ]
  }
}
```

### Integration with devops-specialist

**Purpose**: Coordinate database infrastructure provisioning, backups, and disaster recovery.

**Handoff Pattern**:
```yaml
flow:
  - actor: database-specialist
    action: defines_infrastructure_requirements
    output:
      - database_version: PostgreSQL 15
      - instance_specs: {cpu: 8, memory: 32GB}
      - replication_topology: primary + 2 read replicas
      - backup_requirements: {rpo: 1h, rto: 30min}

  - actor: devops-specialist
    action: provisions_infrastructure
    output:
      - terraform_configs: {...}
      - monitoring_setup: Prometheus + Grafana
      - backup_automation: daily_full + hourly_incremental
```

**Example Handoff Payload**:
```json
{
  "from_agent": "database-specialist",
  "to_agent": "devops-specialist",
  "task": "provision_database_infrastructure",
  "requirements": {
    "database_engine": "PostgreSQL",
    "version": "15.4",
    "topology": {
      "primary": {"instance_type": "db.r6g.2xlarge"},
      "read_replicas": {"count": 2, "regions": ["us-east-1", "us-west-2"]}
    },
    "backup_policy": {
      "automated_backups": {"retention_days": 30},
      "point_in_time_recovery": {"enabled": true}
    }
  }
}
```

### Integration with security-specialist

**Purpose**: Implement database-level security controls, encryption, and access policies.

**Handoff Pattern**:
```yaml
flow:
  - actor: security-specialist
    action: defines_security_requirements
    output:
      - data_classification: {pii: [email, phone], sensitive: [payment_info]}
      - encryption_requirements: {at_rest: AES-256, in_transit: TLS_1.3}
      - access_control_model: role_based + row_level_security

  - actor: database-specialist
    action: implements_security_controls
    output:
      - encryption_enabled: true
      - rls_policies: {...}
      - audit_logging: {enabled: true}
```

### Integration with debugging-specialist

**Purpose**: Diagnose database performance issues, query bottlenecks, and connection problems.

**Handoff Pattern**:
```yaml
flow:
  - actor: debugging-specialist
    action: detects_performance_issue
    output:
      - symptom: API_endpoint_timeout
      - affected_endpoint: GET /api/users/{id}/orders

  - actor: database-specialist
    action: analyzes_database_performance
    output:
      - slow_queries_identified: [...]
      - missing_indexes: [users.email, orders.user_id]
      - connection_pool_exhaustion: false
```

**Example Handoff Payload**:
```json
{
  "from_agent": "debugging-specialist",
  "to_agent": "database-specialist",
  "task": "diagnose_query_performance",
  "issue_context": {
    "symptom": "API endpoint timeouts",
    "metrics": {"p95_latency_ms": 2300, "error_rate": 0.15},
    "suspected_queries": [
      "SELECT * FROM users WHERE id = $1",
      "SELECT * FROM orders WHERE user_id = $1"
    ]
  },
  "diagnostics_needed": [
    "EXPLAIN ANALYZE for suspected queries",
    "slow query log analysis",
    "connection pool metrics"
  ]
}
```

---


## ORM Integration Patterns

### SQLAlchemy (Python)

**Model Definition Best Practices**

✅ **DO: Use type hints and relationship lazy loading**
```python
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime
from typing import List

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Lazy loading prevents N+1 queries
    orders: Mapped[List["Order"]] = relationship(back_populates="user", lazy="select")
```

❌ **DON'T: Use eager loading by default or skip indexes**
```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)  # Missing type hints
    email = Column(String(255))  # Missing unique constraint and index

    # Eager loading causes unnecessary JOINs
    orders = relationship("Order", lazy="joined")  # ❌ Always fetches orders
```

**Async Query Patterns**

✅ **DO: Use async session with proper connection management**
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/db",
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
)

async def get_user_with_orders(user_id: int) -> User:
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        stmt = select(User).options(
            selectinload(User.orders)  # Avoids N+1 queries
        ).where(User.id == user_id)

        result = await session.execute(stmt)
        return result.scalar_one_or_none()
```

### Prisma (TypeScript)

**Schema Definition Best Practices**

✅ **DO: Use proper relations and indexes**
```prisma
model User {
  id        Int      @id @default(autoincrement())
  email     String   @unique @db.VarChar(255)
  createdAt DateTime @default(now()) @map("created_at")

  orders    Order[]

  @@index([email])  // Explicit index
  @@index([createdAt])
  @@map("users")
}

model Order {
  id        Int      @id @default(autoincrement())
  userId    Int      @map("user_id")
  total     Decimal  @db.Decimal(10, 2)  // Proper decimal for currency
  status    OrderStatus @default(PENDING)

  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@index([userId, createdAt])  // Composite index
  @@map("orders")
}
```

**Type-Safe Query Patterns**

✅ **DO: Use type-safe queries with proper error handling**
```typescript
// Transaction with proper error handling
async function createOrderWithItems(
  userId: number,
  orderData: { total: number; items: Array<{ productId: number; quantity: number }> }
) {
  return await prisma.$transaction(async (tx) => {
    const order = await tx.order.create({
      data: { userId, total: orderData.total, status: 'PENDING' },
    })

    await tx.orderItem.createMany({
      data: orderData.items.map(item => ({
        orderId: order.id,
        productId: item.productId,
        quantity: item.quantity,
      })),
    })

    return order
  })
}
```

### Entity Framework Core (.NET)

**DbContext Configuration**

✅ **DO: Use Fluent API for complex configurations**
```csharp
protected override void OnModelCreating(ModelBuilder modelBuilder)
{
    modelBuilder.Entity<User>(entity =>
    {
        entity.ToTable("users");
        entity.HasKey(e => e.Id);

        entity.Property(e => e.Email)
            .IsRequired()
            .HasMaxLength(255);

        entity.HasIndex(e => e.Email)
            .IsUnique()
            .HasDatabaseName("idx_users_email");

        entity.HasMany(e => e.Orders)
            .WithOne(e => e.User)
            .HasForeignKey(e => e.UserId)
            .OnDelete(DeleteBehavior.Cascade);
    });
}
```

**Efficient Query Patterns**

✅ **DO: Use AsNoTracking for read-only queries**
```csharp
public async Task<User> GetUserWithOrdersAsync(int userId)
{
    return await _context.Users
        .AsNoTracking()  // Disable change tracking for read-only
        .Include(u => u.Orders.OrderByDescending(o => o.CreatedAt).Take(50))
        .FirstOrDefaultAsync(u => u.Id == userId);
}

public async Task<List<UserSummary>> GetUserSummariesAsync()
{
    return await _context.Users
        .AsNoTracking()
        .Select(u => new UserSummary  // Project only needed fields
        {
            Id = u.Id,
            Email = u.Email,
            OrderCount = u.Orders.Count(),
            TotalSpent = u.Orders.Sum(o => o.Total)
        })
        .ToListAsync();
}
```

### TypeORM (TypeScript)

**Entity Definition**

✅ **DO: Use decorators with proper types and indexes**
```typescript
@Entity('users')
@Index(['email'], { unique: true })
@Index(['createdAt'])
export class User {
  @PrimaryGeneratedColumn()
  id: number

  @Column({ type: 'varchar', length: 255 })
  email: string

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date

  @OneToMany(() => Order, (order) => order.user, { cascade: false })
  orders: Order[]
}
```

**Transaction Patterns**

✅ **DO: Use query runner with proper error handling**
```typescript
async function createOrderWithItems(userId: number, total: number, items: any[]): Promise<Order> {
  const queryRunner = dataSource.createQueryRunner()
  await queryRunner.connect()
  await queryRunner.startTransaction()

  try {
    const order = await queryRunner.manager.save(Order, { userId, total, status: 'PENDING' })

    const orderItems = items.map(item =>
      queryRunner.manager.create(OrderItem, { orderId: order.id, ...item })
    )
    await queryRunner.manager.save(orderItems)

    await queryRunner.commitTransaction()
    return order
  } catch (error) {
    await queryRunner.rollbackTransaction()
    throw error
  } finally {
    await queryRunner.release()  // Always release connection
  }
}
```

---


## Database Debugging Patterns

### Slow Query Analysis

**PostgreSQL EXPLAIN ANALYZE**

```sql
-- Analyze query execution plan with actual runtime statistics
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT u.id, u.email, COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.created_at > '2024-01-01'
GROUP BY u.id, u.email
ORDER BY order_count DESC
LIMIT 100;

-- Key indicators to analyze:
-- 1. High 'read' in Buffers → Data not in cache, needs index
-- 2. Seq Scan on large table → Missing index
-- 3. High actual time vs estimated cost → Statistics outdated
```

**Query Profiling**

```sql
-- View current slow queries
SELECT
  pid,
  now() - query_start as duration,
  state,
  query
FROM pg_stat_activity
WHERE state != 'idle'
  AND now() - query_start > interval '5 seconds'
ORDER BY duration DESC;

-- Analyze query statistics (requires pg_stat_statements)
SELECT
  query,
  calls,
  total_exec_time / 1000 as total_time_seconds,
  mean_exec_time / 1000 as mean_time_seconds,
  rows
FROM pg_stat_statements
WHERE mean_exec_time > 1000  -- >1s average
ORDER BY total_exec_time DESC
LIMIT 20;
```

### Connection Pool Issues

**Diagnosing Pool Exhaustion**

```sql
-- Check current connections
SELECT
  count(*) as total_connections,
  count(*) FILTER (WHERE state = 'active') as active,
  count(*) FILTER (WHERE state = 'idle') as idle,
  count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
FROM pg_stat_activity
WHERE datname = current_database();

-- Identify long-running connections
SELECT
  pid,
  usename,
  application_name,
  state,
  now() - state_change as state_duration,
  query
FROM pg_stat_activity
WHERE datname = current_database()
  AND state = 'idle in transaction'
  AND now() - state_change > interval '5 minutes';

-- Kill problematic connections
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle in transaction'
  AND now() - state_change > interval '10 minutes';
```

### Deadlock Detection

**Monitor Lock Waits**

```sql
-- View blocked queries
SELECT
  blocked_locks.pid AS blocked_pid,
  blocked_activity.query AS blocked_query,
  blocking_locks.pid AS blocking_pid,
  blocking_activity.query AS blocking_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
  ON blocking_locks.locktype = blocked_locks.locktype
  AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

**Deadlock Prevention**

✅ **DO: Order operations consistently to prevent circular waits**
```sql
BEGIN;
  -- Lock in consistent order: users first, then orders
  SELECT * FROM users WHERE id = 1 FOR UPDATE;
  SELECT * FROM orders WHERE id = 2 FOR UPDATE;

  UPDATE users SET last_order_date = NOW() WHERE id = 1;
  UPDATE orders SET status = 'COMPLETED' WHERE id = 2;
COMMIT;
```

❌ **DON'T: Create circular wait conditions**
```sql
-- Transaction 1: UPDATE users WHERE id = 1; UPDATE orders WHERE id = 2;
-- Transaction 2: UPDATE orders WHERE id = 2; UPDATE users WHERE id = 1;
-- Result: Circular wait → deadlock
```

### Replication Lag Monitoring

```sql
-- Check replication lag on replica
SELECT
  now() - pg_last_xact_replay_timestamp() AS replication_lag,
  pg_is_in_recovery() AS is_replica;

-- On primary: View replica status
SELECT
  client_addr,
  application_name,
  state,
  pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS lag_bytes,
  replay_lag
FROM pg_stat_replication;

-- Alert on high lag (>5 seconds)
SELECT application_name, client_addr, replay_lag
FROM pg_stat_replication
WHERE replay_lag > interval '5 seconds';
```

**Application-Level Lag Handling**

```typescript
class DatabaseRouter {
  private lagThresholdMs: number = 1000  // 1 second

  async query(sql: string, params: any[], options: { consistencyRequired?: boolean } = {}) {
    if (options.consistencyRequired) {
      return this.primaryPool.query(sql, params)  // Always use primary
    }

    const healthyReplica = await this.getHealthyReplica()
    if (healthyReplica) {
      return healthyReplica.query(sql, params)
    }

    // Fallback to primary if all replicas lagging
    return this.primaryPool.query(sql, params)
  }
}

## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat database-specialist-ext.md
```

Or in Claude Code:
```
Please read database-specialist-ext.md for detailed examples.
```
