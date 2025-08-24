#!/usr/bin/env python3
import json
import socket
import threading
import sys
import os
import signal
import time
import logging
from datetime import datetime

# Настройка логирования для видимости всех сообщений
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Выводим в stdout для видимости
    ]
)
logger = logging.getLogger(__name__)

# Импортируем логику из основного сервера с улучшенной обработкой ошибок
try:
    # Проверяем что файл существует
    if not os.path.exists('ddg_mcp_server.py'):
        logger.error("✗ Файл ddg_mcp_server.py не найден")
        sys.exit(1)
        
    from ddg_mcp_server import handle_request
    logger.info("✓ Модуль ddg_mcp_server успешно импортирован")
    
    # Проверяем что функция существует
    if not callable(handle_request):
        logger.error("✗ Функция handle_request не найдена или не вызываема")
        sys.exit(1)
        
except ImportError as e:
    logger.error(f"✗ Ошибка импорта ddg_mcp_server: {e}")
    print("Ошибка: не найден ddg_mcp_server. Убедитесь, что файл в папке.")
    sys.exit(1)
except Exception as e:
    logger.error(f"✗ Неожиданная ошибка при импорте: {e}")
    sys.exit(1)


def send_message_tcp(conn, data):
    """Отправка сообщения через TCP с улучшенной обработкой ошибок"""
    try:
        # Используем ensure_ascii=False для корректной обработки Unicode
        data_str = json.dumps(data, ensure_ascii=False)
        data_bytes = data_str.encode('utf-8')
        
        # Используем старый формат (length + content + newline) для совместимости с тестами
        message = f'{len(data_bytes)}\n'.encode('utf-8') + data_bytes + b'\n'
        
        # Отправляем с проверкой состояния соединения
        conn.sendall(message)
        logger.debug(f"✓ Отправлено сообщение ({len(data_bytes)} байт): {data_str[:100]}...")
        
    except ConnectionResetError:
        logger.warning("⚠️ Соединение разорвано клиентом во время отправки")
        raise
    except socket.error as e:
        logger.error(f"✗ Ошибка сокета при отправке: {e}")
        raise
    except Exception as e:
        logger.error(f"✗ Ошибка отправки сообщения: {e}")
        raise
    
    
def read_message(conn):
    """Чтение сообщения через TCP с улучшенной обработкой ошибок"""
    try:
        # Устанавливаем таймаут
        conn.settimeout(30)
        
        # Считываем первую строку до newline с лучшей обработкой ошибок
        first_line_bytes = b''
        start_time = time.time()
        
        while True:
            # Проверяем таймаут вручную
            if time.time() - start_time > 30:
                logger.warning("⚠️ Таймаут при чтении первой строки")
                return None
                
            try:
                chunk = conn.recv(1)
                if not chunk:
                    logger.debug("📴 Клиент закрыл соединение")
                    return None
                    
                if chunk == b'\n':
                    break
                    
                first_line_bytes += chunk
                
                # Защита от слишком больших сообщений
                if len(first_line_bytes) > 102400:  # 100KB лимит
                    logger.error("✗ Первая строка слишком большая")
                    return None
                    
            except socket.timeout:
                logger.warning("⚠️ Таймаут socket.recv()")
                return None
            except ConnectionResetError:
                logger.warning("⚠️ Соединение разорвано клиентом")
                return None
            except socket.error as e:
                logger.warning(f"⚠️ Ошибка сокета: {e}")
                return None
        
        if not first_line_bytes:
            logger.debug("⚠️ Получена пустая первая строка")
            return None
            
        try:
            first_line = first_line_bytes.decode('utf-8').strip()
        except UnicodeDecodeError as e:
            logger.error(f"✗ Ошибка декодирования UTF-8: {e}")
            return None
            
        logger.debug(f"📝 Первая строка: {first_line[:100]}...")
        
        # Проверяем, это число (старый формат) или JSON (новый формат)
        content = None
        
        try:
            # Пытаемся прочитать как число (старый формат)
            length = int(first_line)
            logger.debug(f"🔍 Обнаружен старый формат, длина: {length} байт")
            
            # Проверяем разумность длины
            if length < 0 or length > 10485760:  # 10MB лимит
                logger.error(f"✗ Некорректная длина сообщения: {length}")
                return None
            
            # Читаем сообщение по длине с улучшенной обработкой ошибок
            content_bytes = b''
            read_start = time.time()
            
            while len(content_bytes) < length:
                if time.time() - read_start > 30:
                    logger.warning("⚠️ Таймаут при чтении сообщения")
                    return None
                    
                try:
                    remaining = length - len(content_bytes)
                    chunk = conn.recv(min(remaining, 4096))
                    if not chunk:
                        logger.warning(f"⚠️ Неожиданное закрытие, получено {len(content_bytes)} из {length} байт")
                        return None
                    content_bytes += chunk
                except (socket.timeout, ConnectionResetError, socket.error) as e:
                    logger.warning(f"⚠️ Ошибка при чтении: {e}")
                    return None
            
            # Пропускаем завершающий newline
            try:
                trailing = conn.recv(1)
                if trailing and trailing != b'\n':
                    logger.debug(f"⚠️ Ожидался newline, получен: {trailing!r}")
            except:
                pass  # Не критично
            
            try:
                content = content_bytes.decode('utf-8')
            except UnicodeDecodeError as e:
                logger.error(f"✗ Ошибка декодирования содержимого: {e}")
                return None
                
        except ValueError:
            # Не число - пробуем как JSON (новый формат)
            logger.debug("🆕 Обнаружен новый MCP формат")
            content = first_line
        
        if not content:
            logger.warning("⚠️ Пустое содержимое сообщения")
            return None
        
        logger.debug(f"📨 Получено сообщение ({len(content)} символов): {content[:200]}...")
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"✗ Ошибка парсинга JSON: {e}")
            logger.error(f"✗ Проблемное сообщение (первые 200 символов): {content[:200]!r}")
            return None
        
    except Exception as e:
        logger.error(f"✗ Неожиданная ошибка в read_message: {e}")
        import traceback
        traceback.print_exc()
        return None

def handle_client(conn, addr):
    """Обработка клиента с улучшенной обработкой ошибок"""
    logger.info(f"✓ Новое подключение от {addr}")
    print(f"\n{'='*60}")
    print(f"[+] Клиент подключился: {addr[0]}:{addr[1]}")
    print(f"{'='*60}")
    
    request_count = 0  # Инициализируем счетчик сразу
    
    try:
        # Устанавливаем keep-alive для стабильности соединения
        try:
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            logger.debug(f"✓ Keep-alive включен для {addr}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось установить keep-alive: {e}")
        
        # Ожидаем сообщения от MCP клиента
        logger.info(f"🔄 Ожидаем MCP сообщения от клиента {addr}")
        
        request_count = 0
        while True:
            try:
                message = read_message(conn)
                if message is None:
                    logger.info(f"📴 Соединение закрыто клиентом {addr}")
                    break
                
                request_count += 1
                method = message.get('method', 'unknown')
                request_id = message.get('id', 'no-id')
                
                print(f"\n[←] Запрос #{request_count} (ID: {request_id}): {method}")
                logger.info(f"📨 Обработка запроса {method} от {addr}")
                
                # Выводим параметры для отладки
                if 'params' in message:
                    params = message['params']
                    if method == 'tools/call':
                        tool_name = params.get('name', 'unknown')
                        print(f"    └─ Инструмент: {tool_name}")
                        if 'arguments' in params:
                            args = params['arguments']
                            if 'query' in args:
                                print(f"    └─ Запрос: '{args['query']}'")
                
                # Обрабатываем запрос с мерой времени
                start_time = time.time()
                try:
                    response = handle_request(message)
                    elapsed = time.time() - start_time
                    logger.debug(f"✓ Запрос {method} обработан за {elapsed:.3f}с")
                except Exception as e:
                    elapsed = time.time() - start_time
                    logger.error(f"✗ Ошибка обработки запроса {method}: {e}")
                    # Создаем ответ об ошибке
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: {str(e)}"
                        }
                    }
                
                # Отправляем ответ
                if response:
                    try:
                        if 'error' in response:
                            print(f"[✗] Ошибка: {response['error'].get('message', 'Unknown error')}")
                            logger.error(f"✗ Ошибка в ответе: {response['error']}")
                        else:
                            print(f"[→] Ответ отправлен (обработка: {elapsed:.2f}с)")
                            logger.info(f"✓ Ответ отправлен за {elapsed:.2f} секунд")
                            
                        send_message_tcp(conn, response)
                        # Минимальная задержка для стабильности
                        time.sleep(0.01)
                        
                    except Exception as e:
                        logger.error(f"✗ Ошибка отправки ответа: {e}")
                        break  # Прерываем соединение при ошибке отправки
                else:
                    logger.warning("⚠️ Получен пустой ответ от handle_request")
                    # Отправляем ошибку клиенту
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": "Internal error: empty response"
                        }
                    }
                    try:
                        send_message_tcp(conn, error_response)
                    except Exception as e:
                        logger.error(f"✗ Ошибка отправки error_response: {e}")
                        break
                        
            except Exception as e:
                logger.error(f"✗ Ошибка в цикле обработки сообщений: {e}")
                break
                
    except ConnectionResetError:
        print(f"\n[!] Клиент {addr} принудительно разорвал соединение")
        logger.warning(f"⚠️ Клиент {addr} принудительно разорвал соединение")
    except Exception as e:
        print(f"\n[!] Ошибка обработки клиента {addr}: {e}")
        logger.error(f"✗ Ошибка обработки клиента {addr}: {e}", exc_info=True)
    finally:
        try:
            conn.close()
        except:
            pass
        print(f"\n[-] Клиент {addr[0]}:{addr[1]} отключился (обработано запросов: {request_count})")
        print(f"{'='*60}\n")
        logger.info(f"📴 Клиент {addr} отключился (обработано {request_count} запросов)")

def main():
    """Запуск TCP-сервера с улучшенной совместимостью MCP"""
    print("\n" + "="*60)
    print("      DuckDuckGo MCP TCP Server")
    print("="*60)
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Улучшенные настройки для стабильности
    server.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    server.settimeout(1.0)  # Таймаут 1 секунда для accept()
    
    try:
        server.bind(('127.0.0.1', 8765))
        server.listen(5)  # Увеличиваем очередь подключений
        
        print(f"\n[✓] Сервер запущен: 127.0.0.1:8765")
        print(f"[✓] Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[i] Для остановки нажмите Ctrl+C")
        print(f"[i] MCP протокол: JSON-RPC 2.0 через TCP")
        print("\n" + "="*60)
        print("Ожидание подключений...\n")
        
        logger.info("TCP сервер успешно запущен на 127.0.0.1:8765")
        
        connection_count = 0
        while True:
            try:
                conn, addr = server.accept()
                connection_count += 1
                print(f"\n[★] Подключение #{connection_count} от {addr[0]}:{addr[1]}")
                
                # Делаем потоки daemon, чтобы они завершались при выходе из программы
                thread = threading.Thread(
                    target=handle_client, 
                    args=(conn, addr), 
                    daemon=True,
                    name=f"Client-{addr[0]}:{addr[1]}"
                )
                thread.start()
                logger.info(f"Запущен поток для обработки клиента {addr}")
                
            except socket.timeout:
                # Это нормально - просто продолжаем ждать
                continue
            except KeyboardInterrupt:
                print("\n\n" + "="*60)
                print("[!] Получен сигнал остановки (Ctrl+C)")
                print("="*60)
                break
                
    except OSError as e:
        if e.errno == 10048:  # Windows: порт уже используется
            print(f"\n" + "="*60)
            print("[✗] ОШИБКА: Порт 8765 уже используется!")
            print("="*60)
            print("\nВозможные решения:")
            print("  1. Закройте другой экземпляр сервера")
            print("  2. Подождите несколько секунд и повторите запуск")
            print("  3. Используйте команду для поиска процесса:")
            print("     netstat -ano | findstr :8765")
            logger.error(f"Порт 8765 уже занят")
        else:
            print(f"\n[✗] Ошибка запуска сервера: {e}")
            logger.error(f"Ошибка запуска сервера: {e}")
    except Exception as e:
        print(f"\n[✗] Неожиданная ошибка: {e}")
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
    finally:
        print("\n" + "="*60)
        print("[...] Остановка сервера...")
        server.close()
        print("[✓] Сервер остановлен")
        print(f"[✓] Время остановки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        logger.info("TCP сервер остановлен")

if __name__ == "__main__":
    try:
        # Проверяем, что все необходимые модули установлены
        try:
            import ddgs
            logger.info("✓ Модуль ddgs установлен")
        except ImportError:
            print("\n[✗] ОШИБКА: Модуль 'ddgs' не установлен!")
            print("Установите его командой: pip install ddgs")
            sys.exit(1)
            
        main()
    except KeyboardInterrupt:
        print("\n[✓] Сервер корректно остановлен пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"\n[✗] Критическая ошибка: {e}")
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)
