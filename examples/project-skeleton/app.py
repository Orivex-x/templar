#!/usr/bin/env python3
"""Main application entry point."""

import sys
from pathlib import Path

sys.dont_write_bytecode = True

from templar.Config import Config
from templar.Router import Router
from templar.Renderer import Renderer
from templar.TemplarServer import TemplarServer
from templar.cli.CliOutput import CliOutput
from templar.core.Logger import get_logger
from templar.core.Performance import PerformanceProfiler

# Initialize logger
logger = get_logger(__name__)

# ============================================================
# Configuration Setup
# ============================================================
try:
    config = Config()
    active_config = config.get_active_config()
    
    project_root = Path(active_config.get("project_root"))
    templates_dir = Path(active_config.get("templates_dir", project_root / "templates"))
    themes_dir = Path(active_config.get("themes_dir", project_root / "themes"))
    static_dir = Path(active_config.get("static_dir", project_root / "static"))
    logs_dir = Path(active_config.get("logs_dir", project_root / "logs"))
    
    # Create logs directory
    logs_dir.mkdir(exist_ok=True)
    logger.add_file_handler(str(logs_dir / "app.log"))
    logger.info("Application starting")
    
except Exception as e:
    logger.error(f"Configuration error: {str(e)}")
    raise

# ============================================================
# Router Setup
# ============================================================
router = Router(config)

# Public routes
router.add("/", "index")
router.add("/about", "about")

# Auth routes (when you add authentication)
# router.add("/login", "auth/login")
# router.add("/register", "auth/register")

logger.info("Routes registered")

# ============================================================
# Renderer Setup
# ============================================================
renderer = Renderer(config, templates_dir, themes_dir, static_dir)

# ============================================================
# Start Server
# ============================================================
if __name__ == "__main__":
    try:
        server = TemplarServer(
            config=config,
            output=CliOutput(),
            router=router,
            renderer=renderer,
            templates_dir=templates_dir,
            themes_dir=themes_dir,
            static_dir=static_dir
        )
        
        logger.info("Server started")
        server.start()
        
    except KeyboardInterrupt:
        logger.info("Server shutdown by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        raise
    finally:
        PerformanceProfiler.print_report()
