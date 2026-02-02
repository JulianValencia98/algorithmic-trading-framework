from datetime import datetime
import MetaTrader5 as mt5
from time import sleep

from Easy_Trading import BasicTrading
from trading_director.app_director import AppDirector, BotConfig
from strategies.simple_time_strategy import SimpleTimeStrategy
from utils.utils import Utils
from utils.strategy_discovery import StrategyDiscovery


def print_help():
    """Muestra los comandos disponibles."""
    print("\n=== Comandos Disponibles ===")
    print("  status               - Muestra el estado de todos los bots")
    print("  status <bot_id>      - Muestra el estado de un bot específico")
    print("  stats                - Muestra estadísticas de trading de todos los bots")
    print("  stats <bot_id>       - Muestra estadísticas de trading de un bot")
    print("  sync                 - Sincroniza trades con historial MT5 ahora")
    print("  pause                - Pausa un bot (selección por menú)")
    print("  resume               - Reanuda un bot pausado (selección por menú)")
    print("  help                 - Muestra esta ayuda")
    print("  exit                 - Detiene todos los bots y sale")
    print("\n=== Estados de Bots ===")
    print("  ▶️  running         - Bot ejecutando estrategia")
    print("  🕐 waiting_market   - Esperando apertura del mercado")
    print("  ⏸️  paused          - Bot pausado manualmente")
    print("  ⏹️  stopped         - Bot detenido")
    print("============================\n")


def handle_commands(app_director: AppDirector, bt: BasicTrading):
    """Maneja comandos interactivos del usuario."""
    print_help()
    
    while True:
        try:
            cmd = input(f"{Utils.dateprint()} > ").strip()
            
            if not cmd:
                continue
            
            parts = cmd.split()
            command = parts[0].lower()
            
            if command == "status":
                if len(parts) > 1:
                    # Status de un bot específico
                    bot_id = parts[1]
                    status = app_director.get_bot_status(bot_id)
                    if status:
                        print(f"\n[{status['bot_id']}]")
                        print(f"  Status: {status['status']}")
                        print(f"  Symbol: {status['symbol']}")
                        print(f"  Timeframe: {status['timeframe']}")
                        print(f"  Interval: {status['interval_seconds']}s")
                        print(f"  Alive: {status['is_alive']}\n")
                    else:
                        print(f"Bot '{bot_id}' no existe.")
                else:
                    # Status de todos los bots
                    all_status = app_director.get_all_bots_status()
                    if all_status:
                        print("\n=== Estado de Bots ===")
                        for status in all_status:
                            # Iconos según estado
                            if status['status'] == 'running':
                                status_icon = "▶️"
                            elif status['status'] == 'paused':
                                status_icon = "⏸️"
                            elif status['status'] == 'waiting_market':
                                status_icon = "🕐"
                            else:
                                status_icon = "⏹️"
                            print(f"{status_icon} [{status['bot_id']}] {status['status']} | {status['symbol']} | Magic: {status.get('magic_number', 'N/A')}")
                        print()
                    else:
                        print("No hay bots activos.")
            
            elif command == "stats":
                if len(parts) > 1:
                    # Stats de un bot específico
                    bot_id = parts[1]
                    stats = app_director.get_bot_trading_stats(bot_id)
                    if stats and stats['total_trades'] > 0:
                        print(f"\n=== Estadísticas de Trading: {bot_id} ===")
                        print(f"  Total trades: {stats['total_trades']}")
                        print(f"  Abiertos: {stats['open_trades']} | Cerrados: {stats['closed_trades']}")
                        print(f"  Ganados: {stats['wins']} | Perdidos: {stats['losses']}")
                        print(f"  Win Rate: {stats['win_rate']}%")
                        print(f"  Profit Total: ${stats['total_profit']}")
                        print(f"  Profit Promedio: ${stats['avg_profit']}")
                        print()
                    else:
                        print(f"No hay trades registrados para '{bot_id}'.")
                else:
                    # Stats de todos los bots
                    all_stats = app_director.get_all_trading_stats()
                    if all_stats:
                        print("\n=== Estadísticas de Trading ===")
                        for stats in all_stats:
                            emoji = "📈" if stats['total_profit'] > 0 else "📉"
                            print(f"{emoji} [{stats['bot_id']}] {stats['wins']}W/{stats['losses']}L ({stats['win_rate']}%) | ${stats['total_profit']}")
                        print()
                    else:
                        print("No hay estadísticas de trading registradas.")
            
            elif command == "pause":
                bots = app_director.list_bots()
                # Incluir bots en running o waiting_market (ambos pueden ser pausados)
                running_bots = [bot_id for bot_id in bots if app_director.get_bot_status(bot_id)['status'] in ['running', 'waiting_market']]
                
                if not running_bots:
                    print("No hay bots corriendo para pausar.")
                else:
                    print("\n=== Bots Activos ===")
                    for i, bot_id in enumerate(running_bots, 1):
                        status = app_director.get_bot_status(bot_id)['status']
                        icon = "▶️" if status == 'running' else "🕐"
                        print(f"  {i}. {icon} {bot_id} ({status})")
                    print()
                    
                    try:
                        choice = input("Selecciona el número del bot a pausar (0 para cancelar): ").strip()
                        if choice == '0':
                            print("Operación cancelada.")
                        else:
                            bot_index = int(choice) - 1
                            if 0 <= bot_index < len(running_bots):
                                bot_id = running_bots[bot_index]
                                app_director.pause_bot(bot_id)
                            else:
                                print("Número inválido.")
                    except ValueError:
                        print("Entrada inválida. Debe ser un número.")
            
            elif command == "resume":
                bots = app_director.list_bots()
                paused_bots = [bot_id for bot_id in bots if app_director.get_bot_status(bot_id)['status'] == 'paused']
                
                if not paused_bots:
                    print("No hay bots pausados para reanudar.")
                else:
                    print("\n=== Bots Pausados ===")
                    for i, bot_id in enumerate(paused_bots, 1):
                        print(f"  {i}. {bot_id}")
                    print()
                    
                    try:
                        choice = input("Selecciona el número del bot a reanudar (0 para cancelar): ").strip()
                        if choice == '0':
                            print("Operación cancelada.")
                        else:
                            bot_index = int(choice) - 1
                            if 0 <= bot_index < len(paused_bots):
                                bot_id = paused_bots[bot_index]
                                app_director.resume_bot(bot_id)
                            else:
                                print("Número inválido.")
                    except ValueError:
                        print("Entrada inválida. Debe ser un número.")
            
            elif command == "sync":
                # Sincronización manual con historial MT5
                last_sync = app_director.get_last_sync_time()
                if last_sync:
                    print(f"Última sincronización: {last_sync.strftime('%Y-%m-%d %H:%M:%S')}")
                app_director.sync_trades_now()
            
            elif command == "help":
                print_help()
            
            elif command == "exit":
                print("Saliendo...")
                app_director.stop_all_bots()
                bt.shutdown()
                print("Finalizado correctamente.")
                break
            
            else:
                print(f"Comando desconocido: '{command}'. Escribe 'help' para ver los comandos disponibles.")
        
        except EOFError:
            # Input cerrado, salir
            break
        except Exception as e:
            print(f"Error procesando comando: {e}")


def create_default_bots() -> list:
    """
    Crea bots por defecto basados en las estrategias disponibles.
    
    Returns:
        Lista de BotConfig para las estrategias encontradas
    """
    bots = []
    strategies = StrategyDiscovery.get_all_strategies()
    strategy_symbols = StrategyDiscovery.get_strategy_symbols()
    
    print(f"{Utils.dateprint()} - Detectando estrategias disponibles...")
    StrategyDiscovery.print_strategy_info()
    
    for strategy_name, strategy_class in strategies.items():
        symbols = strategy_symbols.get(strategy_name, ['EURUSD'])  # Default fallback
        
        # Crear un bot por cada símbolo de la estrategia
        for symbol in symbols:
            try:
                strategy_instance = strategy_class()
                params = strategy_instance.get_parameters()
                
                # Configuración por defecto del bot
                bot = BotConfig(
                    strategy=strategy_instance,
                    symbol=symbol,
                    timeframe=mt5.TIMEFRAME_M1,  # Timeframe por defecto
                    interval_seconds=60,
                    data_points=100
                )
                
                bots.append(bot)
                print(f"   📊 Bot creado: {bot.bot_id} (Magic: {strategy_instance.magic_number})")
                
            except Exception as e:
                print(f"   ❌ Error creando bot para {strategy_name}-{symbol}: {e}")
    
    return bots


def main():
    """Función principal que inicializa el framework con detección automática de estrategias."""
    # Inicializar componentes compartidos
    bt = BasicTrading()
    app_director = AppDirector(bt, notification_service=None)
    
    print(f"{Utils.dateprint()} - Iniciando App Director con detección automática de estrategias...\n")
    
    try:
        # Crear bots automáticamente basados en estrategias disponibles
        default_bots = create_default_bots()
        
        if not default_bots:
            print("❌ No se encontraron estrategias válidas. Creando bot de respaldo...")
            # Crear bot de respaldo si no hay estrategias
            fallback_bot = BotConfig(
                strategy=SimpleTimeStrategy(),
                symbol="EURUSD",
                timeframe=mt5.TIMEFRAME_M1,
                interval_seconds=60,
                data_points=100
            )
            default_bots = [fallback_bot]
        
        # Agregar todos los bots detectados
        for bot in default_bots:
            app_director.add_bot(bot)
        
        print(f"\n{Utils.dateprint()} - Bots activos: {app_director.list_bots()}")
        print(f"{Utils.dateprint()} - Total de {len(default_bots)} bot(s) configurado(s)")
        print(f"{Utils.dateprint()} - Escribe 'help' para ver comandos disponibles.\n")
        
        # Iniciar interfaz de comandos (bloqueante)
        handle_commands(app_director, bt)
    
    except KeyboardInterrupt:
        print(f"\n{Utils.dateprint()} - Interrupción manual detectada. Deteniendo todos los bots...")
        app_director.stop_all_bots()
        bt.shutdown()
        print(f"{Utils.dateprint()} - Finalizado correctamente.")
    
    except Exception as e:
        print(f"❌ Error crítico en main: {e}")
        try:
            app_director.stop_all_bots()
            bt.shutdown()
        except:
            pass


if __name__ == "__main__":
    main()