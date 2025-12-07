# security-specialist - Extended Reference

This file contains detailed documentation for the `security-specialist` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/security-specialist-ext.md
```


## Implementation Patterns

### Secure Authentication System
```typescript
// auth/SecureAuthService.ts
import bcrypt from 'bcrypt';
import crypto from 'crypto';
import jwt from 'jsonwebtoken';
import speakeasy from 'speakeasy';
import { RateLimiter } from 'rate-limiter-flexible';

interface AuthConfig {
  jwtSecret: string;
  jwtExpiry: string;
  refreshTokenExpiry: string;
  passwordPolicy: PasswordPolicy;
  mfaRequired: boolean;
  maxLoginAttempts: number;
  lockoutDuration: number;
}

interface PasswordPolicy {
  minLength: number;
  requireUppercase: boolean;
  requireLowercase: boolean;
  requireNumbers: boolean;
  requireSpecialChars: boolean;
  preventCommonPasswords: boolean;
  preventPasswordReuse: number;
  maxAge: number; // days
}

export class SecureAuthService {
  private readonly saltRounds = 12;
  private readonly tokenVersion = new Map<string, number>();
  private readonly failedAttempts = new Map<string, number>();
  private readonly rateLimiter: RateLimiter;
  
  constructor(private config: AuthConfig) {
    // Rate limiting setup
    this.rateLimiter = new RateLimiter({
      points: 5, // Number of attempts
      duration: 900, // Per 15 minutes
      blockDuration: 900, // Block for 15 minutes
    });
  }
  
  // Password validation
  validatePassword(password: string, email?: string): ValidationResult {
    const errors: string[] = [];
    const policy = this.config.passwordPolicy;
    
    // Length check
    if (password.length < policy.minLength) {
      errors.push(`Password must be at least ${policy.minLength} characters`);
    }
    
    // Complexity checks
    if (policy.requireUppercase && !/[A-Z]/.test(password)) {
      errors.push('Password must contain uppercase letters');
    }
    
    if (policy.requireLowercase && !/[a-z]/.test(password)) {
      errors.push('Password must contain lowercase letters');
    }
    
    if (policy.requireNumbers && !/\d/.test(password)) {
      errors.push('Password must contain numbers');
    }
    
    if (policy.requireSpecialChars && !/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      errors.push('Password must contain special characters');
    }
    
    // Check against common passwords
    if (policy.preventCommonPasswords && this.isCommonPassword(password)) {
      errors.push('Password is too common');
    }
    
    // Check for personal information
    if (email && this.containsPersonalInfo(password, email)) {
      errors.push('Password should not contain personal information');
    }
    
    // Calculate entropy
    const entropy = this.calculateEntropy(password);
    if (entropy < 50) {
      errors.push('Password is not strong enough');
    }
    
    return {
      valid: errors.length === 0,
      errors,
      strength: this.calculateStrength(password),
      entropy,
    };
  }
  
  // Secure password hashing
  async hashPassword(password: string): Promise<string> {
    // Add pepper (application-wide secret)
    const peppered = password + process.env.PASSWORD_PEPPER;
    return bcrypt.hash(peppered, this.saltRounds);
  }
  
  // Secure password verification with timing attack protection
  async verifyPassword(password: string, hash: string): Promise<boolean> {
    const peppered = password + process.env.PASSWORD_PEPPER;
    return bcrypt.compare(peppered, hash);
  }
  
  // JWT token generation with additional security
  generateTokens(userId: string, sessionId: string): TokenPair {
    // Increment token version for revocation
    const version = (this.tokenVersion.get(userId) || 0) + 1;
    this.tokenVersion.set(userId, version);
    
    // Access token with short expiry
    const accessToken = jwt.sign(
      {
        sub: userId,
        sid: sessionId,
        ver: version,
        type: 'access',
        iat: Date.now(),
      },
      this.config.jwtSecret,
      {
        expiresIn: this.config.jwtExpiry,
        algorithm: 'HS256',
        issuer: 'secure-app',
        audience: 'api',
      }
    );
    
    // Refresh token with longer expiry
    const refreshToken = jwt.sign(
      {
        sub: userId,
        sid: sessionId,
        ver: version,
        type: 'refresh',
        iat: Date.now(),
        jti: crypto.randomUUID(), // Unique token ID
      },
      this.config.jwtSecret,
      {
        expiresIn: this.config.refreshTokenExpiry,
        algorithm: 'HS256',
      }
    );
    
    return { accessToken, refreshToken };
  }
  
  // Token validation with additional checks
  async validateToken(token: string, type: 'access' | 'refresh'): Promise<TokenPayload> {
    try {
      const payload = jwt.verify(token, this.config.jwtSecret, {
        algorithms: ['HS256'],
        issuer: 'secure-app',
        audience: type === 'access' ? 'api' : undefined,
      }) as any;
      
      // Check token type
      if (payload.type !== type) {
        throw new Error('Invalid token type');
      }
      
      // Check token version for revocation
      const currentVersion = this.tokenVersion.get(payload.sub);
      if (currentVersion && payload.ver < currentVersion) {
        throw new Error('Token has been revoked');
      }
      
      // Check if session is still valid
      if (!(await this.isSessionValid(payload.sid))) {
        throw new Error('Session expired');
      }
      
      return payload;
    } catch (error) {
      throw new UnauthorizedError('Invalid token');
    }
  }
  
  // MFA setup and verification
  setupMFA(userId: string): MFASetup {
    const secret = speakeasy.generateSecret({
      name: `SecureApp (${userId})`,
      length: 32,
    });
    
    return {
      secret: secret.base32,
      qrCode: secret.otpauth_url!,
      backupCodes: this.generateBackupCodes(),
    };
  }
  
  verifyMFA(token: string, secret: string): boolean {
    return speakeasy.totp.verify({
      secret,
      encoding: 'base32',
      token,
      window: 2, // Allow 2 intervals before/after
    });
  }
  
  // Generate cryptographically secure backup codes
  private generateBackupCodes(count: number = 10): string[] {
    return Array.from({ length: count }, () =>
      crypto.randomBytes(4).toString('hex').toUpperCase()
    );
  }
  
  // Account lockout protection
  async handleFailedLogin(identifier: string): Promise<void> {
    const attempts = (this.failedAttempts.get(identifier) || 0) + 1;
    this.failedAttempts.set(identifier, attempts);
    
    if (attempts >= this.config.maxLoginAttempts) {
      await this.lockAccount(identifier);
      throw new AccountLockedError(
        `Account locked due to ${attempts} failed attempts`
      );
    }
    
    // Exponential backoff
    const delay = Math.min(1000 * Math.pow(2, attempts - 1), 30000);
    await new Promise(resolve => setTimeout(resolve, delay));
  }
  
  // Session management with Redis
  async createSession(userId: string, metadata: SessionMetadata): Promise<string> {
    const sessionId = crypto.randomUUID();
    const session = {
      id: sessionId,
      userId,
      createdAt: Date.now(),
      lastActivity: Date.now(),
      ipAddress: metadata.ipAddress,
      userAgent: metadata.userAgent,
      fingerprint: metadata.fingerprint,
    };
    
    await this.redis.setex(
      `session:${sessionId}`,
      this.config.sessionTimeout,
      JSON.stringify(session)
    );
    
    return sessionId;
  }
  
  // Password entropy calculation
  private calculateEntropy(password: string): number {
    const charset = this.getCharsetSize(password);
    return password.length * Math.log2(charset);
  }
  
  private getCharsetSize(password: string): number {
    let size = 0;
    if (/[a-z]/.test(password)) size += 26;
    if (/[A-Z]/.test(password)) size += 26;
    if (/\d/.test(password)) size += 10;
    if (/[^a-zA-Z0-9]/.test(password)) size += 32;
    return size;
  }
}
```

### Security Headers Middleware
```typescript
// middleware/securityHeaders.ts
import helmet from 'helmet';
import { Request, Response, NextFunction } from 'express';

export function securityHeaders() {
  return helmet({
    // Content Security Policy
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'", "'unsafe-inline'", 'https://trusted-cdn.com'],
        styleSrc: ["'self'", "'unsafe-inline'", 'https://fonts.googleapis.com'],
        fontSrc: ["'self'", 'https://fonts.gstatic.com'],
        imgSrc: ["'self'", 'data:', 'https:'],
        connectSrc: ["'self'", 'https://api.example.com'],
        frameSrc: ["'none'"],
        objectSrc: ["'none'"],
        upgradeInsecureRequests: [],
      },
    },
    
    // Strict Transport Security
    hsts: {
      maxAge: 31536000,
      includeSubDomains: true,
      preload: true,
    },
    
    // Additional headers
    referrerPolicy: { policy: 'strict-origin-when-cross-origin' },
    permittedCrossDomainPolicies: { permittedPolicies: 'none' },
  });
}

// Custom security headers
export function customSecurityHeaders(req: Request, res: Response, next: NextFunction) {
  // Prevent clickjacking
  res.setHeader('X-Frame-Options', 'DENY');
  
  // Prevent MIME type sniffing
  res.setHeader('X-Content-Type-Options', 'nosniff');
  
  // Enable XSS filter
  res.setHeader('X-XSS-Protection', '1; mode=block');
  
  // Permissions Policy
  res.setHeader('Permissions-Policy', 
    'geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=()');
  
  // Clear site data on logout
  if (req.path === '/logout') {
    res.setHeader('Clear-Site-Data', '"cache", "cookies", "storage"');
  }
  
  next();
}

// CORS configuration
export function corsConfig() {
  return {
    origin: (origin: string | undefined, callback: Function) => {
      const allowedOrigins = process.env.ALLOWED_ORIGINS?.split(',') || [];
      
      if (!origin || allowedOrigins.includes(origin)) {
        callback(null, true);
      } else {
        callback(new Error('Not allowed by CORS'));
      }
    },
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-CSRF-Token'],
    exposedHeaders: ['X-Total-Count', 'X-Page-Count'],
    maxAge: 86400, // 24 hours
  };
}
```

### Input Validation and Sanitization
```python

# security/validation.py
import re
import bleach
import html
from typing import Any, Dict, List, Optional
from datetime import datetime
import validators
from sqlalchemy import text

class SecurityValidator:
    """Comprehensive input validation and sanitization"""
    
    # SQL injection patterns
    SQL_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE)\b)",
        r"(--|\||;|\/\*|\*\/|@@|@)",
        r"(xp_|sp_|0x)",
        r"(\bEXEC(\s|\()|EXECUTE(\s|\())",
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>.*?</iframe>",
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\"
        r"%2e%2e%2f",
        r"%252e%252e%252f",
    ]
    
    @classmethod
    def validate_email(cls, email: str) -> tuple[bool, str]:
        """Validate email address"""
        if not email or len(email) > 254:
            return False, "Invalid email length"
        
        if not validators.email(email):
            return False, "Invalid email format"
        
        # Check for suspicious patterns
        if any(pattern in email.lower() for pattern in ['script', 'javascript', '<', '>']):
            return False, "Email contains invalid characters"
        
        return True, email.lower().strip()
    
    @classmethod
    def validate_username(cls, username: str) -> tuple[bool, str]:
        """Validate username"""
        if not username or len(username) < 3 or len(username) > 30:
            return False, "Username must be between 3 and 30 characters"
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "Username can only contain letters, numbers, underscores, and hyphens"
        
        # Check for reserved names
        reserved = ['admin', 'root', 'administrator', 'system', 'null', 'undefined']
        if username.lower() in reserved:
            return False, "Username is reserved"
        
        return True, username
    
    @classmethod
    def sanitize_html(cls, content: str, allowed_tags: Optional[List[str]] = None) -> str:
        """Sanitize HTML content"""
        if allowed_tags is None:
            allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li']
        
        allowed_attributes = {
            'a': ['href', 'title'],
        }
        
        # Clean with bleach
        cleaned = bleach.clean(
            content,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True
        )
        
        # Additional XSS prevention
        cleaned = html.escape(cleaned, quote=True)
        
        return cleaned
    
    @classmethod
    def validate_sql_input(cls, value: str) -> tuple[bool, str]:
        """Validate input for SQL injection attempts"""
        for pattern in cls.SQL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return False, "Input contains potentially dangerous SQL"
        
        return True, value
    
    @classmethod
    def validate_file_upload(cls, file_data: bytes, filename: str, 
                           allowed_types: List[str]) -> tuple[bool, str]:
        """Validate file uploads"""
        import magic
        
        # Check file extension
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        if ext not in allowed_types:
            return False, f"File type .{ext} not allowed"
        
        # Check MIME type
        mime = magic.from_buffer(file_data, mime=True)
        mime_mapping = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        }
        
        if ext in mime_mapping and mime != mime_mapping[ext]:
            return False, "File content does not match extension"
        
        # Check for embedded executables
        if b'#!/' in file_data[:100] or b'<?php' in file_data:
            return False, "File contains executable content"
        
        # Check file size (10MB limit)
        if len(file_data) > 10 * 1024 * 1024:
            return False, "File size exceeds 10MB limit"
        
        return True, filename
    
    @classmethod
    def validate_path(cls, path: str) -> tuple[bool, str]:
        """Validate file paths to prevent traversal attacks"""
        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, path):
                return False, "Path contains traversal attempt"
        
        # Normalize and check
        import os
        normalized = os.path.normpath(path)
        if normalized.startswith('..') or normalized.startswith('/'):
            return False, "Invalid path"
        
        return True, normalized
    
    @classmethod
    def sanitize_json(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize JSON data"""
        def clean_value(value: Any) -> Any:
            if isinstance(value, str):
                # Remove null bytes
                value = value.replace('\x00', '')
                # Escape HTML
                value = html.escape(value)
                return value
            elif isinstance(value, dict):
                return {k: clean_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [clean_value(item) for item in value]
            else:
                return value
        
        return clean_value(data)
    
    @classmethod
    def validate_url(cls, url: str, allowed_schemes: List[str] = None) -> tuple[bool, str]:
        """Validate URLs"""
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        if not validators.url(url):
            return False, "Invalid URL format"
        
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        if parsed.scheme not in allowed_schemes:
            return False, f"URL scheme {parsed.scheme} not allowed"
        
        # Check for SSRF attempts
        dangerous_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '169.254.169.254']
        if any(host in parsed.netloc for host in dangerous_hosts):
            return False, "URL points to internal resource"
        
        return True, url
```

### Infrastructure Security Scanning
```yaml

# security/security-scan.yml
name: Security Scanning

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  # Dependency scanning
  dependency-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run OWASP Dependency Check
        uses: dependency-check/Dependency-Check_Action@main
        with:
          project: 'app'
          path: '.'
          format: 'ALL'
          args: >
            --enableRetired
            --enableExperimental
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: dependency-check-report
          path: reports/
  
  # SAST scanning
  sast-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/owasp-top-ten
            p/r2c-security-audit
      
      - name: Run CodeQL
        uses: github/codeql-action/analyze@v2
        with:
          languages: javascript, python, csharp
  
  # Container scanning
  container-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Trivy scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
      
      - name: Scan Docker images
        run: |
          docker build -t app:scan .
          trivy image --severity HIGH,CRITICAL app:scan
  
  # Infrastructure scanning
  infrastructure-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Terraform security scan
        uses: triat/terraform-security-scan@v3
        with:
          tfsec_version: latest
      
      - name: Checkov scan
        uses: bridgecrewio/checkov-action@master
        with:
          directory: ./infrastructure
          framework: terraform,kubernetes
  
  # Secret scanning
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: TruffleHog scan
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: main
          head: HEAD
      
      - name: Gitleaks scan
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Kubernetes Security Policies
```yaml

# k8s/security-policies.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: restricted
  annotations:
    seccomp.security.alpha.kubernetes.io/allowedProfileNames: 'runtime/default'
    apparmor.security.beta.kubernetes.io/allowedProfileNames: 'runtime/default'
    seccomp.security.alpha.kubernetes.io/defaultProfileName: 'runtime/default'
    apparmor.security.beta.kubernetes.io/defaultProfileName: 'runtime/default'
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  supplementalGroups:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
  readOnlyRootFilesystem: true

---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress

---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-app-traffic
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53

---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-quota
  namespace: production
spec:
  hard:
    requests.cpu: "100"
    requests.memory: "200Gi"
    limits.cpu: "200"
    limits.memory: "400Gi"
    persistentvolumeclaims: "10"
    services.loadbalancers: "2"
    services.nodeports: "0"
```

### Security Compliance Checklist
```python

# compliance/security_audit.py
from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum
import json

class ComplianceLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class ComplianceCheck:
    id: str
    name: str
    description: str
    level: ComplianceLevel
    framework: str  # OWASP, PCI-DSS, GDPR, etc.
    
    def check(self) -> bool:
        """Override in subclasses"""
        raise NotImplementedError

class SecurityAuditor:
    """Automated security compliance auditing"""
    
    def __init__(self):
        self.checks = self._initialize_checks()
    
    def _initialize_checks(self) -> List[ComplianceCheck]:
        """Initialize all compliance checks"""
        return [
            # Authentication checks
            PasswordPolicyCheck(),
            MFAEnabledCheck(),
            SessionTimeoutCheck(),
            AccountLockoutCheck(),
            
            # Authorization checks
            RBACImplementedCheck(),
            PrincipleOfLeastPrivilegeCheck(),
            
            # Data protection
            EncryptionAtRestCheck(),
            EncryptionInTransitCheck(),
            PIIProtectionCheck(),
            DataRetentionPolicyCheck(),
            
            # Network security
            HTTPSOnlyCheck(),
            SecurityHeadersCheck(),
            CORSConfigurationCheck(),
            
            # Application security
            InputValidationCheck(),
            SQLInjectionProtectionCheck(),
            XSSProtectionCheck(),
            CSRFProtectionCheck(),
            
            # Infrastructure security
            ContainerSecurityCheck(),
            SecretManagementCheck(),
            LoggingAndMonitoringCheck(),
            
            # Compliance specific
            GDPRComplianceCheck(),
            PCIDSSComplianceCheck(),
            HIPAAComplianceCheck(),
        ]
    
    def run_audit(self) -> Dict[str, Any]:
        """Run full security audit"""
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total": len(self.checks),
                "passed": 0,
                "failed": 0,
                "critical_issues": 0,
            },
            "checks": [],
            "recommendations": [],
        }
        
        for check in self.checks:
            try:
                passed = check.check()
                result = {
                    "id": check.id,
                    "name": check.name,
                    "passed": passed,
                    "level": check.level.value,
                    "framework": check.framework,
                }
                
                if passed:
                    results["summary"]["passed"] += 1
                else:
                    results["summary"]["failed"] += 1
                    if check.level == ComplianceLevel.CRITICAL:
                        results["summary"]["critical_issues"] += 1
                    results["recommendations"].append(check.get_recommendation())
                
                results["checks"].append(result)
                
            except Exception as e:
                results["checks"].append({
                    "id": check.id,
                    "name": check.name,
                    "error": str(e),
                })
        
        return results
    
    def generate_report(self, results: Dict[str, Any], format: str = "json") -> str:
        """Generate compliance report"""
        if format == "json":
            return json.dumps(results, indent=2)
        elif format == "html":
            return self._generate_html_report(results)
        elif format == "markdown":
            return self._generate_markdown_report(results)
        else:
            raise ValueError(f"Unsupported format: {format}")
```

### Application Security
1. Implement defense in depth
2. Follow principle of least privilege
3. Validate all input
4. Encode all output
5. Use parameterized queries
6. Implement proper error handling

### Authentication & Authorization
1. Use strong password policies
2. Implement MFA
3. Use secure session management
4. Implement proper RBAC
5. Regular permission audits
6. Token rotation and revocation

### Data Protection
1. Encrypt sensitive data at rest
2. Use TLS for data in transit
3. Implement key rotation
4. Secure backup storage
5. Data classification
6. Privacy by design

### Infrastructure Security
1. Regular security updates
2. Network segmentation
3. Firewall configuration
4. Container scanning
5. Secret management
6. Security monitoring


## Related Templates

This specialist ensures security across all technology stacks:

### FastAPI/Python Security Templates
- **fastapi-python/templates/core/config.py.template** - Secure configuration with secret management, JWT settings, and CORS configuration
- **fastapi-python/templates/api/router.py.template** - API endpoints with authentication dependencies

### React/TypeScript Security Patterns
- **react-typescript/templates/api/*.template** - API client patterns requiring secure token handling
- **nextjs-fullstack/templates/workflows-ci.yml.template** - CI pipeline with security scanning integration

### Infrastructure Security Templates
- **react-fastapi-monorepo/templates/docker/docker-compose.service.yml.template** - Container security configuration

---


## Template Code Examples

### ✅ DO: Secure FastAPI Configuration

```python

# core/config.py - Secure configuration pattern
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from typing import List
import secrets

class Settings(BaseSettings):
    # Security Settings - REQUIRED, no defaults for secrets
    SECRET_KEY: str = Field(
        ...,  # Required, no default
        description="Secret key for JWT (min 32 chars, use: secrets.token_urlsafe(32))"
    )

    ALGORITHM: str = Field(
        default="HS256",
        description="JWT algorithm (HS256 for symmetric, RS256 for asymmetric)"
    )

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=15,  # Short-lived access tokens
        ge=5,
        le=60,
        description="Access token expiry (keep short for security)"
    )

    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Refresh token expiry"
    )

    # CORS - Explicit allowlist, no wildcards
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=[],  # Empty by default - must be explicitly configured
        description="Allowed CORS origins (never use '*' in production)"
    )

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("BACKEND_CORS_ORIGINS", mode='before')
    @classmethod
    def validate_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            origins = [origin.strip() for origin in v.split(",")]
        else:
            origins = v

        # Block wildcard in production
        if "*" in origins:
            raise ValueError("Wildcard CORS origin not allowed")
        return origins

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
```

**Why**: Never hardcode secrets, enforce minimum security requirements, and validate configuration at startup.

### ✅ DO: Implement Secure Authentication Dependencies

```python

# dependencies/auth.py - Secure authentication pattern
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import hashlib

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

class SecurityDependencies:
    """Reusable security dependencies for FastAPI"""

    @staticmethod
    async def get_current_user(
        request: Request,
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
    ):
        """
        Validate JWT and return current user.
        Includes rate limiting and suspicious activity detection.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            # Decode token with explicit algorithm
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )

            user_id: str = payload.get("sub")
            token_type: str = payload.get("type")
            token_version: int = payload.get("ver", 0)

            if user_id is None or token_type != "access":
                raise credentials_exception

            # Check token expiration explicitly
            exp = payload.get("exp")
            if exp and datetime.utcnow().timestamp() > exp:
                raise credentials_exception

        except JWTError:
            # Log failed authentication attempt
            await log_security_event(
                event="auth_failure",
                ip=request.client.host,
                details="Invalid JWT token"
            )
            raise credentials_exception

        # Fetch user and validate
        user = await crud.user.get(db, id=int(user_id))
        if user is None:
            raise credentials_exception

        # Check if user's tokens were invalidated
        if user.token_version > token_version:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )

        return user

    @staticmethod
    async def require_admin(
        current_user = Depends(get_current_user)
    ):
        """Dependency to require admin privileges"""
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        return current_user

    @staticmethod
    async def rate_limit(
        request: Request,
        limit: int = 100,
        window: int = 60
    ):
        """Rate limiting dependency"""
        client_ip = request.client.host
        key = f"rate_limit:{client_ip}"

        # Check rate limit (pseudo-code - use Redis in production)
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, window)

        if current > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
```

**Why**: Centralized authentication with proper error handling, token validation, and rate limiting.

### ✅ DO: Secure API Endpoints

```typescript
// React/TypeScript - Secure API client pattern
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

class SecureApiClient {
  private client: AxiosInstance;
  private refreshPromise: Promise<string> | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.VITE_API_URL,
      timeout: 10000,
      withCredentials: true,  // Send cookies
    });

    // Request interceptor - add auth header
    this.client.interceptors.request.use((config) => {
      const token = this.getAccessToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      // Add CSRF token if available
      const csrfToken = this.getCsrfToken();
      if (csrfToken) {
        config.headers['X-CSRF-Token'] = csrfToken;
      }

      return config;
    });

    // Response interceptor - handle 401 and refresh tokens
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        // Prevent infinite loops
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            // Use singleton promise to prevent multiple refresh calls
            if (!this.refreshPromise) {
              this.refreshPromise = this.refreshToken();
            }

            const newToken = await this.refreshPromise;
            this.refreshPromise = null;

            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return this.client(originalRequest);
          } catch (refreshError) {
            // Refresh failed - clear tokens and redirect to login
            this.clearTokens();
            window.location.href = '/auth/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  private getAccessToken(): string | null {
    return localStorage.getItem('access_token');
  }

  private getCsrfToken(): string | null {
    // Get CSRF token from cookie or meta tag
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || null;
  }

  private async refreshToken(): Promise<string> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      throw new Error('No refresh token');
    }

    const response = await axios.post(`${process.env.VITE_API_URL}/auth/refresh`, {
      refresh_token: refreshToken
    });

    const { access_token } = response.data;
    localStorage.setItem('access_token', access_token);
    return access_token;
  }

  private clearTokens(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }
}

export const api = new SecureApiClient();
```

**Why**: Secure token storage, automatic refresh, CSRF protection, and proper error handling.

### ✅ DO: Secure Docker Configuration

```yaml

# docker-compose.yml - Security-hardened configuration
version: '3.8'

services:
  backend:
    build:
      context: ./apps/backend
      dockerfile: Dockerfile
    # Run as non-root user
    user: "1000:1000"
    # Read-only filesystem where possible
    read_only: true
    # Temporary directories for runtime
    tmpfs:
      - /tmp
      - /var/run
    # Security options
    security_opt:
      - no-new-privileges:true
    # Resource limits
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          memory: 256M
    # Network isolation
    networks:
      - backend-network
    # Environment from secrets
    environment:
      - DATABASE_URL_FILE=/run/secrets/db_url
      - SECRET_KEY_FILE=/run/secrets/secret_key
    secrets:
      - db_url
      - secret_key
    # Health check
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  db:
    image: postgres:16-alpine
    # Run as postgres user
    user: postgres
    # No external access
    expose:
      - "5432"
    # Network isolation
    networks:
      - backend-network
    # Volume with proper permissions
    volumes:
      - db-data:/var/lib/postgresql/data:Z
    # Environment from secrets
    environment:
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
    secrets:
      - db_password

networks:
  backend-network:
    driver: bridge
    internal: true  # No external access

secrets:
  db_url:
    file: ./secrets/db_url.txt
  secret_key:
    file: ./secrets/secret_key.txt
  db_password:
    file: ./secrets/db_password.txt

volumes:
  db-data:
```

**Why**: Non-root users, read-only filesystems, network isolation, secrets management, and resource limits.

### ❌ DON'T: Expose Secrets in Configuration

```python

# BAD - Secrets hardcoded
SECRET_KEY = "mysecretkey123"  # NEVER DO THIS!
DATABASE_URL = "postgresql://user:password@localhost/db"  # Password in code!

# BAD - Weak validation
class Settings(BaseSettings):
    SECRET_KEY: str = "default-secret"  # Default secret is a vulnerability!
    DEBUG: bool = True  # Debug mode in production exposes info

# GOOD - Secrets from environment, no defaults for sensitive values
class Settings(BaseSettings):
    SECRET_KEY: str = Field(..., min_length=32)  # Required, no default
    DEBUG: bool = Field(default=False)  # Safe default
```

### ❌ DON'T: Use Weak Authentication Patterns

```typescript
// BAD - Storing tokens insecurely
localStorage.setItem('password', userPassword);  // NEVER store passwords!
document.cookie = `token=${token}`;  // No HttpOnly, SameSite, Secure flags

// BAD - No token validation
const token = localStorage.getItem('token');
fetch('/api/data', { headers: { Authorization: token } });  // No Bearer prefix, no validation

// GOOD - Secure token handling
// Store only access tokens (short-lived)
localStorage.setItem('access_token', token);

// Use httpOnly cookies for refresh tokens (set by server)
// Validate token format before use
const validateToken = (token: string): boolean => {
  if (!token || typeof token !== 'string') return false;
  const parts = token.split('.');
  return parts.length === 3;  // JWT has 3 parts
};
```

---


## Template Best Practices

### Authentication & Authorization

✅ **Use short-lived access tokens**:
```python
ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
    default=15,  # 15 minutes max
    ge=5,
    le=60
)
```

✅ **Implement token rotation**:
```python

# Increment user's token_version to invalidate all existing tokens
async def logout_all_sessions(db: AsyncSession, user_id: int):
    user = await crud.user.get(db, id=user_id)
    user.token_version += 1
    await db.commit()
```

✅ **Use bcrypt with high cost factor**:
```python
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Minimum 12 rounds
)
```

### Input Validation

✅ **Validate all inputs with Pydantic**:
```python
from pydantic import BaseModel, EmailStr, Field, field_validator
import re

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(
        min_length=3,
        max_length=30,
        pattern=r'^[a-zA-Z0-9_]+$'  # Alphanumeric only
    )
    password: str = Field(min_length=12)

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain special character')
        return v
```

✅ **Sanitize outputs**:
```python
import html

def sanitize_output(data: str) -> str:
    return html.escape(data, quote=True)
```

### Security Headers

✅ **Configure security headers in FastAPI**:
```python
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()

# Force HTTPS in production
if settings.ENVIRONMENT == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["example.com", "*.example.com"]
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

### Logging & Monitoring

✅ **Log security events**:
```python
import logging
from datetime import datetime

security_logger = logging.getLogger("security")

async def log_security_event(
    event: str,
    ip: str,
    user_id: int | None = None,
    details: str = ""
):
    security_logger.warning(
        f"SECURITY_EVENT: {event}",
        extra={
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event,
            "ip_address": ip,
            "user_id": user_id,
            "details": details
        }
    )
```

---


## Template Anti-Patterns

### ❌ NEVER: Trust Client Input

```python

# BAD - Using client-provided user ID
@router.get("/users/{user_id}/profile")
async def get_profile(user_id: int):
    return await crud.user.get(db, id=user_id)  # IDOR vulnerability!

# GOOD - Use authenticated user from token
@router.get("/users/me/profile")
async def get_my_profile(
    current_user = Depends(get_current_user)
):
    return current_user  # Always returns authenticated user's data
```

### ❌ NEVER: Expose Internal Errors

```python

# BAD - Leaking internal details
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))  # Exposes stack trace!

# GOOD - Generic error message, log details internally
except Exception as e:
    logger.error(f"Internal error: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Internal server error")
```

### ❌ NEVER: Use Wildcard CORS

```python

# BAD - Allows any origin
BACKEND_CORS_ORIGINS = ["*"]

# GOOD - Explicit allowlist
BACKEND_CORS_ORIGINS = [
    "https://myapp.com",
    "https://admin.myapp.com"
]
```

### ❌ NEVER: Store Sensitive Data in JWT

```python

# BAD - Sensitive data in token payload
payload = {
    "sub": user.id,
    "email": user.email,
    "password_hash": user.hashed_password,  # NEVER!
    "ssn": user.ssn  # NEVER!
}

# GOOD - Minimal payload
payload = {
    "sub": str(user.id),
    "type": "access",
    "ver": user.token_version
}
```

### ❌ NEVER: Disable Security for Convenience

```python

# BAD - Disabling security checks
@router.post("/admin/action")
async def admin_action():  # No authentication!
    pass

# BAD - Bypassing validation
class Config:
    validate_assignment = False  # Allows invalid data!

# GOOD - Always enforce security
@router.post("/admin/action")
async def admin_action(
    current_user = Depends(require_admin)
):
    pass
```

---


## Cross-Stack Security Checklist

When reviewing security across different technology stacks:

### FastAPI/Python
- [ ] SECRET_KEY from environment (min 32 chars)
- [ ] No default values for secrets
- [ ] bcrypt for password hashing (12+ rounds)
- [ ] JWT with short expiry (≤15 min access, ≤7 days refresh)
- [ ] CORS explicitly configured (no wildcards)
- [ ] Rate limiting implemented
- [ ] Input validation with Pydantic
- [ ] Security headers configured

### React/TypeScript
- [ ] Access tokens in memory/localStorage (short-lived)
- [ ] Refresh tokens in httpOnly cookies
- [ ] CSRF protection enabled
- [ ] No sensitive data in client-side storage
- [ ] API errors don't expose internals
- [ ] Content Security Policy headers

### Docker/Infrastructure
- [ ] Non-root container users
- [ ] Read-only filesystems where possible
- [ ] Secrets via Docker secrets/env files
- [ ] Network isolation between services
- [ ] Resource limits configured
- [ ] Health checks enabled
- [ ] No exposed development ports

### CI/CD Pipeline
- [ ] Secret scanning enabled (TruffleHog, Gitleaks)
- [ ] Dependency scanning (OWASP, Snyk)
- [ ] SAST scanning (Semgrep, CodeQL)
- [ ] Container scanning (Trivy)
- [ ] No secrets in build logs


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat security-specialist-ext.md
```

Or in Claude Code:
```
Please read security-specialist-ext.md for detailed examples.
```
