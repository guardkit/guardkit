/**
 * Unit Tests for MCP TypeScript Config Templates
 *
 * Tests template file existence, structure validation, placeholder handling,
 * and configuration correctness for the MCP TypeScript template.
 *
 * Task: TASK-MTS-006
 */

import { describe, it, expect, beforeAll } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

const TEMPLATE_DIR = path.join(
  __dirname,
  '../../installer/core/templates/mcp-typescript'
);

describe('MCP TypeScript Config Templates - File Existence', () => {
  it('should have package.json.template in config directory', () => {
    const templatePath = path.join(TEMPLATE_DIR, 'config/package.json.template');
    expect(fs.existsSync(templatePath)).toBe(true);
  });

  it('should have tsconfig.json.template in config directory', () => {
    const templatePath = path.join(TEMPLATE_DIR, 'config/tsconfig.json.template');
    expect(fs.existsSync(templatePath)).toBe(true);
  });

  it('should have claude-desktop.json.template in config directory', () => {
    const templatePath = path.join(TEMPLATE_DIR, 'config/claude-desktop.json.template');
    expect(fs.existsSync(templatePath)).toBe(true);
  });

  it('should have Dockerfile.template in docker directory', () => {
    const templatePath = path.join(TEMPLATE_DIR, 'docker/Dockerfile.template');
    expect(fs.existsSync(templatePath)).toBe(true);
  });

  it('should have docker-compose.yml.template in docker directory', () => {
    const templatePath = path.join(TEMPLATE_DIR, 'docker/docker-compose.yml.template');
    expect(fs.existsSync(templatePath)).toBe(true);
  });
});

describe('MCP TypeScript Config Templates - package.json.template', () => {
  let content: string;

  beforeAll(() => {
    const templatePath = path.join(TEMPLATE_DIR, 'config/package.json.template');
    if (fs.existsSync(templatePath)) {
      content = fs.readFileSync(templatePath, 'utf-8');
    } else {
      content = '';
    }
  });

  it('should have valid JSON structure when placeholders are replaced', () => {
    if (!content) return; // Skip if template doesn't exist yet

    // Replace placeholders with sample values
    const replaced = content
      .replace(/\{\{ServerName\}\}/g, 'test-server')
      .replace(/\{\{ServerVersion\}\}/g, '1.0.0')
      .replace(/\{\{Description\}\}/g, 'Test MCP Server');

    expect(() => JSON.parse(replaced)).not.toThrow();
  });

  it('should have {{ServerName}} placeholder', () => {
    if (!content) return;
    expect(content).toContain('{{ServerName}}');
  });

  it('should have {{ServerVersion}} placeholder', () => {
    if (!content) return;
    expect(content).toContain('{{ServerVersion}}');
  });

  it('should have {{Description}} placeholder', () => {
    if (!content) return;
    expect(content).toContain('{{Description}}');
  });

  it('should have type: module for ESM support', () => {
    if (!content) return;
    const parsed = JSON.parse(
      content
        .replace(/\{\{ServerName\}\}/g, 'test')
        .replace(/\{\{ServerVersion\}\}/g, '1.0.0')
        .replace(/\{\{Description\}\}/g, 'test')
    );
    expect(parsed.type).toBe('module');
  });

  it('should have dev script with tsx watch', () => {
    if (!content) return;
    const parsed = JSON.parse(
      content
        .replace(/\{\{ServerName\}\}/g, 'test')
        .replace(/\{\{ServerVersion\}\}/g, '1.0.0')
        .replace(/\{\{Description\}\}/g, 'test')
    );
    expect(parsed.scripts.dev).toContain('tsx');
    expect(parsed.scripts.dev).toContain('watch');
  });

  it('should have build script with esbuild', () => {
    if (!content) return;
    const parsed = JSON.parse(
      content
        .replace(/\{\{ServerName\}\}/g, 'test')
        .replace(/\{\{ServerVersion\}\}/g, '1.0.0')
        .replace(/\{\{Description\}\}/g, 'test')
    );
    expect(parsed.scripts.build).toContain('esbuild');
    expect(parsed.scripts.build).toContain('--bundle');
    expect(parsed.scripts.build).toContain('--platform=node');
  });

  it('should have test scripts with vitest', () => {
    if (!content) return;
    const parsed = JSON.parse(
      content
        .replace(/\{\{ServerName\}\}/g, 'test')
        .replace(/\{\{ServerVersion\}\}/g, '1.0.0')
        .replace(/\{\{Description\}\}/g, 'test')
    );
    expect(parsed.scripts.test).toContain('vitest');
    expect(parsed.scripts['test:coverage']).toContain('vitest');
    expect(parsed.scripts['test:coverage']).toContain('--coverage');
  });

  it('should have @modelcontextprotocol/sdk as dependency', () => {
    if (!content) return;
    const parsed = JSON.parse(
      content
        .replace(/\{\{ServerName\}\}/g, 'test')
        .replace(/\{\{ServerVersion\}\}/g, '1.0.0')
        .replace(/\{\{Description\}\}/g, 'test')
    );
    expect(parsed.dependencies['@modelcontextprotocol/sdk']).toBeDefined();
  });

  it('should have zod as dependency for validation', () => {
    if (!content) return;
    const parsed = JSON.parse(
      content
        .replace(/\{\{ServerName\}\}/g, 'test')
        .replace(/\{\{ServerVersion\}\}/g, '1.0.0')
        .replace(/\{\{Description\}\}/g, 'test')
    );
    expect(parsed.dependencies.zod).toBeDefined();
  });

  it('should require Node.js >= 20', () => {
    if (!content) return;
    const parsed = JSON.parse(
      content
        .replace(/\{\{ServerName\}\}/g, 'test')
        .replace(/\{\{ServerVersion\}\}/g, '1.0.0')
        .replace(/\{\{Description\}\}/g, 'test')
    );
    expect(parsed.engines.node).toContain('20');
  });

  it('should have essential devDependencies', () => {
    if (!content) return;
    const parsed = JSON.parse(
      content
        .replace(/\{\{ServerName\}\}/g, 'test')
        .replace(/\{\{ServerVersion\}\}/g, '1.0.0')
        .replace(/\{\{Description\}\}/g, 'test')
    );

    expect(parsed.devDependencies['@types/node']).toBeDefined();
    expect(parsed.devDependencies.esbuild).toBeDefined();
    expect(parsed.devDependencies.tsx).toBeDefined();
    expect(parsed.devDependencies.typescript).toBeDefined();
    expect(parsed.devDependencies.vitest).toBeDefined();
    expect(parsed.devDependencies['@vitest/coverage-v8']).toBeDefined();
  });
});

describe('MCP TypeScript Config Templates - tsconfig.json.template', () => {
  let content: string;

  beforeAll(() => {
    const templatePath = path.join(TEMPLATE_DIR, 'config/tsconfig.json.template');
    if (fs.existsSync(templatePath)) {
      content = fs.readFileSync(templatePath, 'utf-8');
    } else {
      content = '';
    }
  });

  it('should have valid JSON structure', () => {
    if (!content) return;
    expect(() => JSON.parse(content)).not.toThrow();
  });

  it('should target ES2022', () => {
    if (!content) return;
    const parsed = JSON.parse(content);
    expect(parsed.compilerOptions.target).toBe('ES2022');
  });

  it('should use NodeNext module resolution', () => {
    if (!content) return;
    const parsed = JSON.parse(content);
    expect(parsed.compilerOptions.module).toBe('NodeNext');
    expect(parsed.compilerOptions.moduleResolution).toBe('NodeNext');
  });

  it('should have strict mode enabled', () => {
    if (!content) return;
    const parsed = JSON.parse(content);
    expect(parsed.compilerOptions.strict).toBe(true);
  });

  it('should output to dist directory', () => {
    if (!content) return;
    const parsed = JSON.parse(content);
    expect(parsed.compilerOptions.outDir).toBe('./dist');
  });

  it('should have source in src directory', () => {
    if (!content) return;
    const parsed = JSON.parse(content);
    expect(parsed.compilerOptions.rootDir).toBe('./src');
  });

  it('should generate declarations and source maps', () => {
    if (!content) return;
    const parsed = JSON.parse(content);
    expect(parsed.compilerOptions.declaration).toBe(true);
    expect(parsed.compilerOptions.declarationMap).toBe(true);
    expect(parsed.compilerOptions.sourceMap).toBe(true);
  });

  it('should have path alias for @ imports', () => {
    if (!content) return;
    const parsed = JSON.parse(content);
    expect(parsed.compilerOptions.paths['@/*']).toBeDefined();
    expect(parsed.compilerOptions.paths['@/*']).toContain('./src/*');
  });

  it('should include src and exclude node_modules, dist, tests', () => {
    if (!content) return;
    const parsed = JSON.parse(content);
    expect(parsed.include).toContain('src/**/*');
    expect(parsed.exclude).toContain('node_modules');
    expect(parsed.exclude).toContain('dist');
    expect(parsed.exclude).toContain('tests');
  });
});

describe('MCP TypeScript Config Templates - claude-desktop.json.template', () => {
  let content: string;

  beforeAll(() => {
    const templatePath = path.join(TEMPLATE_DIR, 'config/claude-desktop.json.template');
    if (fs.existsSync(templatePath)) {
      content = fs.readFileSync(templatePath, 'utf-8');
    } else {
      content = '';
    }
  });

  it('should have valid JSON structure when placeholders are replaced', () => {
    if (!content) return;

    const replaced = content
      .replace(/\{\{ServerName\}\}/g, 'test-server')
      .replace(/\{\{AbsoluteNodePath\}\}/g, '/usr/local/bin/node')
      .replace(/\{\{AbsoluteProjectPath\}\}/g, '/home/user/project');

    expect(() => JSON.parse(replaced)).not.toThrow();
  });

  it('should have {{ServerName}} placeholder', () => {
    if (!content) return;
    expect(content).toContain('{{ServerName}}');
  });

  it('should have {{AbsoluteNodePath}} placeholder', () => {
    if (!content) return;
    expect(content).toContain('{{AbsoluteNodePath}}');
  });

  it('should have {{AbsoluteProjectPath}} placeholder', () => {
    if (!content) return;
    expect(content).toContain('{{AbsoluteProjectPath}}');
  });

  it('should have mcpServers object structure', () => {
    if (!content) return;
    const replaced = content
      .replace(/\{\{ServerName\}\}/g, 'test-server')
      .replace(/\{\{AbsoluteNodePath\}\}/g, '/usr/local/bin/node')
      .replace(/\{\{AbsoluteProjectPath\}\}/g, '/home/user/project');

    const parsed = JSON.parse(replaced);
    expect(parsed.mcpServers).toBeDefined();
    expect(parsed.mcpServers['test-server']).toBeDefined();
  });

  it('should use tsx for TypeScript execution', () => {
    if (!content) return;
    const replaced = content
      .replace(/\{\{ServerName\}\}/g, 'test-server')
      .replace(/\{\{AbsoluteNodePath\}\}/g, '/usr/local/bin/node')
      .replace(/\{\{AbsoluteProjectPath\}\}/g, '/home/user/project');

    const parsed = JSON.parse(replaced);
    const serverConfig = parsed.mcpServers['test-server'];
    expect(serverConfig.args).toContain('tsx');
  });

  it('should have cwd set to project path', () => {
    if (!content) return;
    const replaced = content
      .replace(/\{\{ServerName\}\}/g, 'test-server')
      .replace(/\{\{AbsoluteNodePath\}\}/g, '/usr/local/bin/node')
      .replace(/\{\{AbsoluteProjectPath\}\}/g, '/home/user/project');

    const parsed = JSON.parse(replaced);
    const serverConfig = parsed.mcpServers['test-server'];
    expect(serverConfig.cwd).toBe('/home/user/project');
  });

  it('should have development environment config', () => {
    if (!content) return;
    const replaced = content
      .replace(/\{\{ServerName\}\}/g, 'test-server')
      .replace(/\{\{AbsoluteNodePath\}\}/g, '/usr/local/bin/node')
      .replace(/\{\{AbsoluteProjectPath\}\}/g, '/home/user/project');

    const parsed = JSON.parse(replaced);
    const serverConfig = parsed.mcpServers['test-server'];
    expect(serverConfig.env.NODE_ENV).toBe('development');
  });

  it('should have absolute path warning in comments or documentation', () => {
    // This test verifies there's either a comment or the template itself
    // makes it clear that paths must be absolute
    if (!content) return;

    // Check for ABSOLUTE or AbsolutePath in placeholders (case-insensitive)
    const hasAbsoluteIndicator =
      content.includes('Absolute') ||
      content.includes('ABSOLUTE') ||
      content.toUpperCase().includes('ABSOLUTE');

    expect(hasAbsoluteIndicator).toBe(true);
  });
});

describe('MCP TypeScript Config Templates - Dockerfile.template', () => {
  let content: string;

  beforeAll(() => {
    const templatePath = path.join(TEMPLATE_DIR, 'docker/Dockerfile.template');
    if (fs.existsSync(templatePath)) {
      content = fs.readFileSync(templatePath, 'utf-8');
    } else {
      content = '';
    }
  });

  it('should use multi-stage build', () => {
    if (!content) return;
    expect(content).toContain('AS builder');
    expect(content).toMatch(/FROM.*node.*AS builder/);
  });

  it('should use Node 20 Alpine base image', () => {
    if (!content) return;
    expect(content).toMatch(/FROM\s+node:20-alpine/);
  });

  it('should copy package files first for layer caching', () => {
    if (!content) return;
    // Package files should be copied before source code
    const packageCopyIndex = content.indexOf('COPY package*.json');
    const srcCopyIndex = content.indexOf('COPY src/');

    expect(packageCopyIndex).toBeGreaterThan(-1);
    expect(srcCopyIndex).toBeGreaterThan(-1);
    expect(packageCopyIndex).toBeLessThan(srcCopyIndex);
  });

  it('should run npm ci for reproducible builds', () => {
    if (!content) return;
    expect(content).toContain('npm ci');
  });

  it('should run build in builder stage', () => {
    if (!content) return;
    expect(content).toContain('npm run build');
  });

  it('should copy dist from builder stage', () => {
    if (!content) return;
    expect(content).toContain('COPY --from=builder');
    expect(content).toContain('/app/dist');
  });

  it('should install production dependencies only in final stage', () => {
    if (!content) return;
    expect(content).toContain('npm ci --production');
  });

  it('should create non-root user for security', () => {
    if (!content) return;
    expect(content).toContain('adduser');
    expect(content).toContain('USER');
  });

  it('should set NODE_ENV to production', () => {
    if (!content) return;
    expect(content).toContain('NODE_ENV=production');
  });

  it('should have health check', () => {
    if (!content) return;
    expect(content).toContain('HEALTHCHECK');
  });

  it('should run the correct command', () => {
    if (!content) return;
    expect(content).toContain('CMD');
    expect(content).toContain('node');
    expect(content).toContain('dist/index.js');
  });
});

describe('MCP TypeScript Config Templates - docker-compose.yml.template', () => {
  let content: string;

  beforeAll(() => {
    const templatePath = path.join(TEMPLATE_DIR, 'docker/docker-compose.yml.template');
    if (fs.existsSync(templatePath)) {
      content = fs.readFileSync(templatePath, 'utf-8');
    } else {
      content = '';
    }
  });

  it('should be valid YAML structure', () => {
    if (!content) return;
    // Basic YAML structure check
    expect(content).toContain('services:');
  });

  it('should have {{ServerName}} placeholder', () => {
    if (!content) return;
    expect(content).toContain('{{ServerName}}');
  });

  it('should reference the Dockerfile', () => {
    if (!content) return;
    expect(content).toContain('dockerfile:');
    expect(content).toContain('Dockerfile');
  });

  it('should have stdin_open for stdio transport', () => {
    if (!content) return;
    expect(content).toContain('stdin_open: true');
  });

  it('should have tty enabled', () => {
    if (!content) return;
    expect(content).toContain('tty: true');
  });

  it('should set production environment', () => {
    if (!content) return;
    expect(content).toContain('NODE_ENV=production');
  });

  it('should have restart policy', () => {
    if (!content) return;
    expect(content).toContain('restart:');
  });
});

describe('MCP TypeScript Config Templates - Placeholder Consistency', () => {
  const placeholders = ['{{ServerName}}', '{{ServerVersion}}', '{{Description}}'];

  it('should use consistent placeholder format across all templates', () => {
    const configDir = path.join(TEMPLATE_DIR, 'config');
    const dockerDir = path.join(TEMPLATE_DIR, 'docker');

    // Skip if directories don't exist yet
    if (!fs.existsSync(configDir) && !fs.existsSync(dockerDir)) {
      return;
    }

    const allContent: string[] = [];

    if (fs.existsSync(configDir)) {
      const configFiles = fs.readdirSync(configDir);
      for (const file of configFiles) {
        if (file.endsWith('.template')) {
          allContent.push(fs.readFileSync(path.join(configDir, file), 'utf-8'));
        }
      }
    }

    if (fs.existsSync(dockerDir)) {
      const dockerFiles = fs.readdirSync(dockerDir);
      for (const file of dockerFiles) {
        if (file.endsWith('.template')) {
          allContent.push(fs.readFileSync(path.join(dockerDir, file), 'utf-8'));
        }
      }
    }

    // Check that all placeholders use mustache-style {{}}
    for (const content of allContent) {
      // Check for incorrect placeholder formats
      expect(content).not.toMatch(/\$\{[^}]+\}/); // Not ${...}
      expect(content).not.toMatch(/<[A-Z_]+>/); // Not <PLACEHOLDER>
      expect(content).not.toMatch(/%[a-zA-Z_]+%/); // Not %placeholder%
    }
  });
});
