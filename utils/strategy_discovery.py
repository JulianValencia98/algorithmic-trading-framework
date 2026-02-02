"""
Utilidades para detección automática de estrategias y símbolos.
"""
import os
import importlib
import inspect
from typing import List, Dict, Any
from strategies.strategy_base import StrategyBase


class StrategyDiscovery:
    """Clase para descubrir dinámicamente estrategias disponibles en el framework."""
    
    @staticmethod
    def get_all_strategies() -> Dict[str, Any]:
        """
        Descubre todas las estrategias disponibles en la carpeta strategies/.
        
        Returns:
            Dict con nombre de estrategia como key y clase como value
        """
        strategies = {}
        strategy_dir = "strategies"
        
        # Buscar todos los archivos .py en la carpeta strategies
        if os.path.exists(strategy_dir):
            for file in os.listdir(strategy_dir):
                if file.endswith('.py') and file != '__init__.py' and file != 'strategy_base.py':
                    module_name = file[:-3]  # Remover .py
                    
                    try:
                        # Importar el módulo dinámicamente
                        module = importlib.import_module(f"strategies.{module_name}")
                        
                        # Buscar clases que hereden de StrategyBase
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if (issubclass(obj, StrategyBase) and 
                                obj != StrategyBase and 
                                obj.__module__ == module.__name__):
                                strategies[name] = obj
                                
                    except Exception as e:
                        print(f"Error importando estrategia {module_name}: {e}")
                        
        return strategies
    
    @staticmethod
    def get_strategy_symbols() -> Dict[str, List[str]]:
        """
        Obtiene los símbolos configurados para cada estrategia.
        
        Returns:
            Dict con nombre de estrategia como key y lista de símbolos como value
        """
        strategies = StrategyDiscovery.get_all_strategies()
        strategy_symbols = {}
        
        for strategy_name, strategy_class in strategies.items():
            try:
                # Crear instancia temporal para obtener parámetros
                instance = strategy_class()
                params = instance.get_parameters()
                
                # Obtener símbolos de los parámetros (si están definidos)
                if 'symbols' in params:
                    strategy_symbols[strategy_name] = params['symbols']
                elif 'symbol' in params:
                    strategy_symbols[strategy_name] = [params['symbol']]
                else:
                    # Símbolos por defecto si no están especificados
                    strategy_symbols[strategy_name] = ['EURUSD', 'GBPUSD', 'USDJPY']
                    
            except Exception as e:
                print(f"Error obteniendo símbolos para {strategy_name}: {e}")
                strategy_symbols[strategy_name] = ['EURUSD']  # Fallback
                
        return strategy_symbols
    
    @staticmethod
    def get_all_unique_symbols() -> List[str]:
        """
        Obtiene una lista única de todos los símbolos usados por las estrategias.
        
        Returns:
            Lista de símbolos únicos
        """
        strategy_symbols = StrategyDiscovery.get_strategy_symbols()
        all_symbols = set()
        
        for symbols_list in strategy_symbols.values():
            all_symbols.update(symbols_list)
            
        return sorted(list(all_symbols))
    
    @staticmethod
    def print_strategy_info():
        """Imprime información detallada sobre estrategias disponibles."""
        strategies = StrategyDiscovery.get_all_strategies()
        strategy_symbols = StrategyDiscovery.get_strategy_symbols()
        
        print("\n=== ESTRATEGIAS DISPONIBLES ===")
        for strategy_name, strategy_class in strategies.items():
            try:
                instance = strategy_class()
                params = instance.get_parameters()
                symbols = strategy_symbols.get(strategy_name, [])
                
                print(f"\n📊 {strategy_name}")
                print(f"   Magic Number: {instance.magic_number}")
                print(f"   Descripción: {params.get('description', 'N/A')}")
                print(f"   Símbolos: {', '.join(symbols)}")
                print(f"   Max Posiciones: {params.get('max_open_positions', 1)}")
                print(f"   Cierre antes apertura: {params.get('close_before_open', False)}")
                
            except Exception as e:
                print(f"❌ Error procesando {strategy_name}: {e}")
                
        print(f"\n📈 Total estrategias: {len(strategies)}")
        print(f"🎯 Símbolos únicos: {len(StrategyDiscovery.get_all_unique_symbols())}")
        print("===============================\n")


if __name__ == "__main__":
    # Test de la funcionalidad
    StrategyDiscovery.print_strategy_info()