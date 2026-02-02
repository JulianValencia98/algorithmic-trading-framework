"""
Global Application State Manager

Singleton que mantiene el estado global de la aplicación.
Permite a los componentes consultar si el sistema está pausado globalmente.
"""
import threading
from typing import Optional


class GlobalState:
    """
    Singleton que mantiene el estado global de la aplicación.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicializa el estado global."""
        if self._initialized:
            return
        
        self._globally_paused = False
        self._app_director = None  # Referencia al AppDirector
        self._lock = threading.Lock()
        self._initialized = True
    
    def set_app_director(self, app_director):
        """
        Establece la referencia al AppDirector.
        
        Args:
            app_director: Instancia del AppDirector
        """
        with self._lock:
            self._app_director = app_director
    
    def set_globally_paused(self, paused: bool):
        """
        Actualiza el estado de pausa global.
        
        Args:
            paused: True si está pausado globalmente, False si no
        """
        with self._lock:
            self._globally_paused = paused
    
    def is_globally_paused(self) -> bool:
        """
        Verifica si el sistema está pausado globalmente.
        
        Returns:
            True si está pausado, False si no
        """
        with self._lock:
            # Priorizar el estado directo del AppDirector si está disponible
            if self._app_director and hasattr(self._app_director, 'is_globally_paused'):
                return self._app_director.is_globally_paused()
            # Fallback al estado local
            return self._globally_paused
    
    def should_skip_action(self, action_type: str = "general") -> bool:
        """
        Determina si se debe saltar una acción basado en el estado global.
        
        Args:
            action_type: Tipo de acción ("event", "notification", "log", "general")
            
        Returns:
            True si se debe saltar la acción, False si se debe ejecutar
        """
        return self.is_globally_paused()


# Instancia global del estado
global_state = GlobalState()