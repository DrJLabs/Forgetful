"""
MCP Server Async Initialization Manager

This module handles proper async initialization of all MCP performance components,
preventing race conditions and ensuring components start in the correct order.
"""

import asyncio
import logging
from typing import Optional, List, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum
import time

logger = logging.getLogger(__name__)


class InitializationStatus(Enum):
    """Status of component initialization"""
    PENDING = "pending"
    INITIALIZING = "initializing"  
    INITIALIZED = "initialized"
    FAILED = "failed"


@dataclass
class ComponentInfo:
    """Information about an initialization component"""
    name: str
    initializer: Callable
    dependencies: List[str]
    status: InitializationStatus = InitializationStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error: Optional[str] = None
    
    @property
    def duration_ms(self) -> float:
        """Get initialization duration in milliseconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0


class MCPInitializationManager:
    """Manager for coordinating async initialization of MCP components"""
    
    def __init__(self):
        self._components: Dict[str, ComponentInfo] = {}
        self._initialization_task: Optional[asyncio.Task] = None
        self._initialization_complete = False
        self._initialization_lock = asyncio.Lock()
        
    def register_component(self, 
                          name: str, 
                          initializer: Callable,
                          dependencies: List[str] = None):
        """Register a component for initialization"""
        self._components[name] = ComponentInfo(
            name=name,
            initializer=initializer,
            dependencies=dependencies or []
        )
        logger.debug(f"Registered component: {name}")
    
    async def initialize_all(self, timeout: float = 30.0) -> bool:
        """Initialize all registered components in dependency order"""
        async with self._initialization_lock:
            if self._initialization_complete:
                logger.debug("Initialization already complete")
                return True
            
            if self._initialization_task and not self._initialization_task.done():
                logger.debug("Initialization already in progress")
                try:
                    await asyncio.wait_for(self._initialization_task, timeout=timeout)
                    return self._initialization_complete
                except asyncio.TimeoutError:
                    logger.error("Initialization timed out")
                    return False
            
            # Start new initialization
            self._initialization_task = asyncio.create_task(
                self._do_initialization()
            )
            
            try:
                await asyncio.wait_for(self._initialization_task, timeout=timeout)
                return self._initialization_complete
            except asyncio.TimeoutError:
                logger.error("Initialization timed out")
                return False
    
    async def _do_initialization(self):
        """Perform the actual initialization"""
        try:
            logger.info("Starting MCP component initialization")
            
            # Calculate initialization order based on dependencies
            init_order = self._calculate_init_order()
            
            # Initialize components in order
            for component_name in init_order:
                await self._initialize_component(component_name)
            
            self._initialization_complete = True
            logger.info("MCP component initialization complete")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            self._initialization_complete = False
    
    def _calculate_init_order(self) -> List[str]:
        """Calculate initialization order based on dependencies"""
        # Simple topological sort
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(name: str):
            if name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {name}")
            if name in visited:
                return
            
            temp_visited.add(name)
            
            component = self._components.get(name)
            if component:
                for dep in component.dependencies:
                    if dep in self._components:
                        visit(dep)
            
            temp_visited.remove(name)
            visited.add(name)
            order.append(name)
        
        for component_name in self._components:
            visit(component_name)
        
        return order
    
    async def _initialize_component(self, name: str):
        """Initialize a specific component"""
        component = self._components[name]
        
        try:
            logger.debug(f"Initializing component: {name}")
            component.status = InitializationStatus.INITIALIZING
            component.start_time = time.time()
            
            # Call the initializer
            if asyncio.iscoroutinefunction(component.initializer):
                await component.initializer()
            else:
                component.initializer()
            
            component.end_time = time.time()
            component.status = InitializationStatus.INITIALIZED
            
            logger.info(f"Component {name} initialized in {component.duration_ms:.2f}ms")
            
        except Exception as e:
            component.end_time = time.time()
            component.status = InitializationStatus.FAILED
            component.error = str(e)
            
            logger.error(f"Failed to initialize component {name}: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get initialization status for all components"""
        return {
            "initialization_complete": self._initialization_complete,
            "components": {
                name: {
                    "status": comp.status.value,
                    "duration_ms": comp.duration_ms,
                    "error": comp.error
                }
                for name, comp in self._components.items()
            }
        }
    
    def is_initialized(self) -> bool:
        """Check if initialization is complete"""
        return self._initialization_complete
    
    async def shutdown(self):
        """Shutdown all components gracefully"""
        logger.info("Shutting down MCP components")
        
        # Cancel initialization if running
        if self._initialization_task and not self._initialization_task.done():
            self._initialization_task.cancel()
            try:
                await self._initialization_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown components in reverse order
        init_order = self._calculate_init_order()
        for component_name in reversed(init_order):
            component = self._components[component_name]
            if component.status == InitializationStatus.INITIALIZED:
                try:
                    # Look for shutdown method
                    if hasattr(component.initializer, '__self__'):
                        obj = component.initializer.__self__
                        if hasattr(obj, 'shutdown'):
                            if asyncio.iscoroutinefunction(obj.shutdown):
                                await obj.shutdown()
                            else:
                                obj.shutdown()
                            logger.debug(f"Shutdown component: {component_name}")
                except Exception as e:
                    logger.error(f"Error shutting down component {component_name}: {e}")


# Global initialization manager
_init_manager: Optional[MCPInitializationManager] = None


def get_init_manager() -> MCPInitializationManager:
    """Get the global initialization manager"""
    global _init_manager
    if _init_manager is None:
        _init_manager = MCPInitializationManager()
    return _init_manager


def register_component(name: str, 
                      initializer: Callable,
                      dependencies: List[str] = None):
    """Register a component for initialization"""
    manager = get_init_manager()
    manager.register_component(name, initializer, dependencies)


async def initialize_mcp_optimizations(timeout: float = 30.0) -> bool:
    """Initialize all MCP performance optimizations"""
    manager = get_init_manager()
    return await manager.initialize_all(timeout)


def is_mcp_initialized() -> bool:
    """Check if MCP optimizations are initialized"""
    manager = get_init_manager()
    return manager.is_initialized()


async def shutdown_mcp_optimizations():
    """Shutdown all MCP optimizations gracefully"""
    manager = get_init_manager()
    await manager.shutdown()


def setup_mcp_components():
    """Setup MCP component registration"""
    from app.utils.connection_pool import get_connection_pool
    from app.utils.performance_monitor import get_performance_monitor
    from app.utils.batch_processor import get_batch_processor
    
    # Register components with dependencies
    register_component(
        "performance_monitor",
        lambda: get_performance_monitor()._start_background_monitoring(),
        dependencies=[]
    )
    
    register_component(
        "connection_pool",
        lambda: asyncio.create_task(get_connection_pool().start_health_monitoring()),
        dependencies=[]
    )
    
    register_component(
        "batch_processor", 
        lambda: get_batch_processor()._start_processing(),
        dependencies=[]
    )
    
    logger.info("MCP components registered for initialization")