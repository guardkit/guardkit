#!/usr/bin/env python3
"""
Diagnostic script for template-create Phase 7.5 issues.

Usage:
    python3 debug-template-create.py /path/to/codebase

This script adds comprehensive logging to trace execution flow and identify
why Phase 7.5 (Agent Enhancement) is not running.
"""

import sys
import logging
from pathlib import Path

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('template-create-debug.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def validate_environment():
    """Validate that environment is set up correctly."""
    logger.info("="*60)
    logger.info("ENVIRONMENT VALIDATION")
    logger.info("="*60)
    
    # Check Python version
    import sys
    logger.info(f"Python version: {sys.version}")
    
    # Check if installer module can be imported
    try:
        import importlib
        orchestrator_module = importlib.import_module(
            'installer.global.commands.lib.template_create_orchestrator'
        )
        logger.info("✓ Orchestrator module imported successfully")
    except ImportError as e:
        logger.error(f"✗ Failed to import orchestrator: {e}")
        return False
    
    return True

def inject_debug_logging():
    """Inject additional logging into orchestrator."""
    import importlib
    orchestrator_module = importlib.import_module(
        'installer.global.commands.lib.template_create_orchestrator'
    )
    
    TemplateCreateOrchestrator = orchestrator_module.TemplateCreateOrchestrator
    
    # Monkey patch _complete_workflow to add logging
    original_complete_workflow = TemplateCreateOrchestrator._complete_workflow
    
    def logged_complete_workflow(self):
        logger.info("="*60)
        logger.info("ENTERING _complete_workflow()")
        logger.info("="*60)
        logger.info(f"Config: dry_run={self.config.dry_run}")
        logger.info(f"Agents count: {len(self.agents) if self.agents else 0}")
        
        result = original_complete_workflow(self)
        
        logger.info("="*60)
        logger.info("EXITING _complete_workflow()")
        logger.info("="*60)
        
        return result
    
    TemplateCreateOrchestrator._complete_workflow = logged_complete_workflow
    
    # Monkey patch _phase7_write_agents to add logging
    original_phase7 = TemplateCreateOrchestrator._phase7_write_agents
    
    def logged_phase7(self, agents, output_path):
        logger.info("="*60)
        logger.info("ENTERING _phase7_write_agents()")
        logger.info("="*60)
        logger.info(f"Agents to write: {len(agents)}")
        logger.info(f"Output path: {output_path}")
        
        result = original_phase7(self, agents, output_path)
        
        logger.info(f"Phase 7 result type: {type(result)}")
        logger.info(f"Phase 7 result value: {result}")
        logger.info(f"Phase 7 result is None: {result is None}")
        if result is not None:
            logger.info(f"Phase 7 result length: {len(result)}")
        
        logger.info("="*60)
        logger.info("EXITING _phase7_write_agents()")
        logger.info("="*60)
        
        return result
    
    TemplateCreateOrchestrator._phase7_write_agents = logged_phase7
    
    # Monkey patch _ensure_templates_on_disk to add logging
    original_ensure = TemplateCreateOrchestrator._ensure_templates_on_disk
    
    def logged_ensure(self, output_path):
        logger.info("="*60)
        logger.info("ENTERING _ensure_templates_on_disk()")
        logger.info("="*60)
        logger.info(f"Flag _templates_written_to_disk: {self._templates_written_to_disk}")
        logger.info(f"Templates count: {self.templates.total_count if self.templates else 0}")
        
        original_ensure(self, output_path)
        
        logger.info(f"After ensure - Flag: {self._templates_written_to_disk}")
        
        # Check filesystem
        templates_dir = output_path / "templates"
        if templates_dir.exists():
            template_files = list(templates_dir.glob("**/*.template"))
            logger.info(f"Template files on disk: {len(template_files)}")
        else:
            logger.info("Template directory does not exist on disk")
        
        logger.info("="*60)
        logger.info("EXITING _ensure_templates_on_disk()")
        logger.info("="*60)
    
    TemplateCreateOrchestrator._ensure_templates_on_disk = logged_ensure
    
    # Monkey patch _phase7_5_enhance_agents to add logging
    original_phase7_5 = TemplateCreateOrchestrator._phase7_5_enhance_agents
    
    def logged_phase7_5(self, output_path):
        logger.info("="*60)
        logger.info("ENTERING _phase7_5_enhance_agents()")
        logger.info("="*60)
        logger.info(f"Output path: {output_path}")
        logger.info(f"Agents count: {len(self.agents) if self.agents else 0}")
        
        # Check if agents directory exists
        agents_dir = output_path / "agents"
        if agents_dir.exists():
            agent_files = list(agents_dir.glob("*.md"))
            logger.info(f"Agent files on disk: {len(agent_files)}")
            for agent_file in agent_files:
                size = agent_file.stat().st_size
                logger.info(f"  - {agent_file.name}: {size} bytes")
        else:
            logger.info("Agents directory does not exist on disk")
        
        result = original_phase7_5(self, output_path)
        
        logger.info(f"Phase 7.5 result: {result}")
        
        logger.info("="*60)
        logger.info("EXITING _phase7_5_enhance_agents()")
        logger.info("="*60)
        
        return result
    
    TemplateCreateOrchestrator._phase7_5_enhance_agents = logged_phase7_5
    
    logger.info("✓ Debug logging injected into orchestrator")

def run_template_create(codebase_path: Path):
    """Run template creation with debug logging."""
    import importlib
    orchestrator_module = importlib.import_module(
        'installer.global.commands.lib.template_create_orchestrator'
    )
    
    run_template_create_fn = orchestrator_module.run_template_create
    
    logger.info("="*60)
    logger.info("STARTING TEMPLATE CREATION")
    logger.info("="*60)
    logger.info(f"Codebase path: {codebase_path}")
    
    result = run_template_create_fn(
        codebase_path=codebase_path,
        output_location='global',
        verbose=True,
        custom_name='debug-test'
    )
    
    logger.info("="*60)
    logger.info("TEMPLATE CREATION COMPLETE")
    logger.info("="*60)
    logger.info(f"Success: {result.success}")
    logger.info(f"Template name: {result.template_name}")
    logger.info(f"Agent count: {result.agent_count}")
    logger.info(f"Errors: {result.errors}")
    logger.info(f"Warnings: {result.warnings}")
    
    return result

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python3 debug-template-create.py /path/to/codebase")
        sys.exit(1)
    
    codebase_path = Path(sys.argv[1])
    
    if not codebase_path.exists():
        print(f"Error: Codebase path does not exist: {codebase_path}")
        sys.exit(1)
    
    # Validate environment
    if not validate_environment():
        print("Environment validation failed")
        sys.exit(1)
    
    # Inject debug logging
    inject_debug_logging()
    
    # Run template creation
    result = run_template_create(codebase_path)
    
    # Report results
    print("\n" + "="*60)
    print("DEBUG RESULTS")
    print("="*60)
    print(f"Check template-create-debug.log for detailed execution trace")
    print(f"Success: {result.success}")
    print(f"Agent count: {result.agent_count}")
    
    if result.success:
        print("\nNext steps:")
        print("1. Check the agent files in:")
        print(f"   {result.output_path}/agents/")
        print("2. Verify if agents are enhanced (150-250 lines) or basic (36 lines)")
        print("3. Review template-create-debug.log for execution flow")
    
    sys.exit(0 if result.success else 1)

if __name__ == "__main__":
    main()