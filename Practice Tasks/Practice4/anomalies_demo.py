#!/usr/bin/env python3
"""
Демонстрация аномалий изоляции в PostgreSQL
Аномалии: Dirty Read (невозможен в PG), Non-repeatable Read, Phantom Read, Lost Update
"""

import psycopg2
import psycopg2.extras
import threading
import time
import sys
from datetime import datetime

class Colors:
    """Цвета для терминала"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class Logger:
    """Логирование с таймстемпами"""
    @staticmethod
    def log(message, color=Colors.RESET):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"{color}[{timestamp}] {message}{Colors.RESET}")
    
    @staticmethod
    def info(message):
        Logger.log(f"ℹ️  {message}", Colors.CYAN)
    
    @staticmethod
    def success(message):
        Logger.log(f"✅ {message}", Colors.GREEN)
    
    @staticmethod
    def error(message):
        Logger.log(f"❌ {message}", Colors.RED)
    
    @staticmethod
    def warning(message):
        Logger.log(f"⚠️  {message}", Colors.YELLOW)
    
    @staticmethod
    def anomaly(message):
        Logger.log(f"🔴 {message}", Colors.RED + Colors.BOLD)

class DatabaseConnection:
    """Менеджер соединений с БД"""
    def __init__(self, auto_commit=False):
        self.conn = None
        self.auto_commit = auto_commit
    
    def __enter__(self):
        self.conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="testdb",
            user="testuser",
            password="testpass"
        )
        self.conn.autocommit = self.auto_commit
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

class AnomaliesDemo:
    def __init__(self):
        self.setup_database()
    
    def setup_database(self):
        """Сброс базы данных к начальному состоянию"""
        with DatabaseConnection(auto_commit=True) as conn:
            cur = conn.cursor()
            cur.execute("TRUNCATE accounts RESTART IDENTITY CASCADE")
            cur.execute("""
                INSERT INTO accounts (id, name, balance) VALUES 
                (1, 'Alice', 1000),
                (2, 'Bob', 500),
                (3, 'Charlie', 750)
            """)
            Logger.success("База данных инициализирована")
            self.show_balance("Начальное состояние")
    
    def show_balance(self, title="Текущее состояние"):
        """Показать текущее состояние таблицы"""
        with DatabaseConnection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name, balance FROM accounts ORDER BY id")
            rows = cur.fetchall()
            Logger.info(f"{title}:")
            for row in rows:
                print(f"   {row[0]}. {row[1]}: {row[2]}")

    # ===========================================
    # 1. Dirty Read (Грязное чтение) - НЕВОЗМОЖЕН В POSTGRESQL
    # ===========================================
    def demo_dirty_read(self):
        """
        Демонстрация: Dirty Read НЕВОЗМОЖЕН в PostgreSQL
        Из-за механизма MVCC читающая транзакция всегда видит только закоммиченные данные
        """
        Logger.info("\n" + "="*70)
        Logger.info("ДЕМОНСТРАЦИЯ 1: DIRTY READ (Грязное чтение)")
        Logger.info("="*70)
        
        Logger.warning("ОСОБЕННОСТЬ POSTGRESQL: Dirty Read НЕВОЗМОЖЕН из-за MVCC")
        Logger.info("Даже на уровне READ UNCOMMITTED PostgreSQL работает как READ COMMITTED")
        
        # Транзакция 2: Bob изменяет данные, но не коммитит
        def transaction_bob():
            with DatabaseConnection() as conn:
                conn.autocommit = False
                cur = conn.cursor()
                
                Logger.info("[Bob] BEGIN TRANSACTION")
                cur.execute("BEGIN")
                
                Logger.info("[Bob] UPDATE accounts SET balance = balance - 200 WHERE id = 2")
                cur.execute("UPDATE accounts SET balance = balance - 200 WHERE id = 2")
                
                Logger.info("[Bob] (НЕ КОММИТИТ, ждет 3 секунды...)")
                time.sleep(3)
                
                Logger.warning("[Bob] ROLLBACK - отмена изменений")
                cur.execute("ROLLBACK")
        
        # Транзакция 1: Alice читает данные
        def transaction_alice():
            time.sleep(0.5)
            with DatabaseConnection() as conn:
                conn.autocommit = False
                cur = conn.cursor()
                
                Logger.info("[Alice] BEGIN TRANSACTION (пробуем READ UNCOMMITTED)")
                # PostgreSQL игнорирует READ UNCOMMITTED и работает как READ COMMITTED
                cur.execute("BEGIN ISOLATION LEVEL READ UNCOMMITTED")
                
                Logger.info("[Alice] SELECT balance FROM accounts WHERE id = 2")
                cur.execute("SELECT balance FROM accounts WHERE id = 2")
                balance = cur.fetchone()[0]
                
                # В PostgreSQL всегда будет 500, а не 300
                if balance == 300:
                    Logger.anomaly(f"[Alice] Прочитала balance = {balance} (грязное чтение!)")
                else:
                    Logger.success(f"[Alice] Прочитала balance = {balance} (грязное чтение НЕВОЗМОЖНО в PG)")
                
                cur.execute("COMMIT")
        
        # Запуск параллельных транзакций
        threads = [
            threading.Thread(target=transaction_alice),
            threading.Thread(target=transaction_bob)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Проверка результата
        with DatabaseConnection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT balance FROM accounts WHERE id = 2")
            final_balance = cur.fetchone()[0]
            Logger.info(f"Итоговый баланс Bob: {final_balance} (правильно: 500)")
        
        self.show_balance("После dirty read")
        Logger.info("💡 ВЫВОД: PostgreSQL защищает от Dirty Read на любом уровне изоляции")

    # ===========================================
    # 2. Non-repeatable Read
    # ===========================================
    def demo_non_repeatable_read(self):
        """
        Аномалия: Неповторяемое чтение - данные меняются внутри транзакции
        """
        Logger.info("\n" + "="*70)
        Logger.info("ДЕМОНСТРАЦИЯ 2: NON-REPEATABLE READ")
        Logger.info("="*70)
        
        self.setup_database()
        
        # Транзакция 2: Bob изменяет данные и коммитит
        def transaction_bob():
            time.sleep(1.5)
            with DatabaseConnection() as conn:
                conn.autocommit = False
                cur = conn.cursor()
                
                Logger.info("[Bob] BEGIN TRANSACTION")
                cur.execute("BEGIN")
                
                Logger.info("[Bob] UPDATE accounts SET balance = 900 WHERE id = 1")
                cur.execute("UPDATE accounts SET balance = 900 WHERE id = 1")
                
                Logger.info("[Bob] COMMIT")
                cur.execute("COMMIT")
        
        # Транзакция 1: Alice читает дважды
        def transaction_alice():
            with DatabaseConnection() as conn:
                conn.autocommit = False
                cur = conn.cursor()
                
                Logger.info("[Alice] BEGIN TRANSACTION (READ COMMITTED)")
                cur.execute("BEGIN ISOLATION LEVEL READ COMMITTED")
                
                Logger.info("[Alice] Первое чтение: SELECT balance FROM accounts WHERE id = 1")
                cur.execute("SELECT balance FROM accounts WHERE id = 1")
                balance1 = cur.fetchone()[0]
                Logger.info(f"[Alice] Первое чтение: {balance1}")
                
                Logger.info("[Alice] Ожидание 3 секунды...")
                time.sleep(3)
                
                Logger.info("[Alice] Второе чтение: SELECT balance FROM accounts WHERE id = 1")
                cur.execute("SELECT balance FROM accounts WHERE id = 1")
                balance2 = cur.fetchone()[0]
                Logger.info(f"[Alice] Второе чтение: {balance2}")
                
                if balance1 != balance2:
                    Logger.anomaly(f"Non-repeatable read! {balance1} -> {balance2}")
                else:
                    Logger.success("Нет аномалии")
                
                cur.execute("COMMIT")
        
        # Запуск
        threads = [
            threading.Thread(target=transaction_alice),
            threading.Thread(target=transaction_bob)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        self.show_balance("После non-repeatable read")

    # ===========================================
    # 3. Phantom Read
    # ===========================================
    def demo_phantom_read(self):
        """
        Аномалия: Фантомное чтение - появляются новые строки
        Исправлено: указание явного id=4 для новой записи
        """
        Logger.info("\n" + "="*70)
        Logger.info("ДЕМОНСТРАЦИЯ 3: PHANTOM READ")
        Logger.info("="*70)
        
        self.setup_database()
        
        # Транзакция 2: Bob вставляет новую запись с id=4
        def transaction_bob():
            time.sleep(2)
            with DatabaseConnection() as conn:
                conn.autocommit = False
                cur = conn.cursor()
                
                Logger.info("[Bob] BEGIN TRANSACTION")
                cur.execute("BEGIN")
                
                # Исправлено: явно указываем id=4, чтобы избежать конфликта
                Logger.info("[Bob] INSERT INTO accounts (id, name, balance) VALUES (4, 'David', 800)")
                cur.execute("INSERT INTO accounts (id, name, balance) VALUES (4, 'David', 800)")
                
                Logger.info("[Bob] COMMIT")
                cur.execute("COMMIT")
        
        # Транзакция 1: Alice считает количество дважды
        def transaction_alice():
            with DatabaseConnection() as conn:
                conn.autocommit = False
                cur = conn.cursor()
                
                Logger.info("[Alice] BEGIN TRANSACTION (READ COMMITTED)")
                cur.execute("BEGIN ISOLATION LEVEL READ COMMITTED")
                
                Logger.info("[Alice] Первый подсчет: SELECT COUNT(*) FROM accounts WHERE balance > 700")
                cur.execute("SELECT COUNT(*) FROM accounts WHERE balance > 700")
                count1 = cur.fetchone()[0]
                Logger.info(f"[Alice] Первый подсчет: {count1} записей")
                
                Logger.info("[Alice] Ожидание 3 секунды...")
                time.sleep(3)
                
                Logger.info("[Alice] Второй подсчет: SELECT COUNT(*) FROM accounts WHERE balance > 700")
                cur.execute("SELECT COUNT(*) FROM accounts WHERE balance > 700")
                count2 = cur.fetchone()[0]
                Logger.info(f"[Alice] Второй подсчет: {count2} записей")
                
                if count1 != count2:
                    Logger.anomaly(f"Phantom read! {count1} -> {count2} записей")
                else:
                    Logger.success("Нет фантомов (READ COMMITTED защищает от фантомов?)")
                
                cur.execute("COMMIT")
        
        # Запуск
        threads = [
            threading.Thread(target=transaction_alice),
            threading.Thread(target=transaction_bob)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        self.show_balance("После phantom read")
        
        # Очистка - удаляем David, если он есть
        with DatabaseConnection(auto_commit=True) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM accounts WHERE name = 'David'")

    # ===========================================
    # 4. Lost Update
    # ===========================================
    def demo_lost_update(self):
        """
        Аномалия: Потерянное обновление
        """
        Logger.info("\n" + "="*70)
        Logger.info("ДЕМОНСТРАЦИЯ 4: LOST UPDATE")
        Logger.info("="*70)
        
        self.setup_database()
        
        # Транзакция A: Alice
        def transaction_alice():
            with DatabaseConnection() as conn:
                conn.autocommit = False
                cur = conn.cursor()
                
                Logger.info("[Alice] BEGIN")
                cur.execute("BEGIN")
                
                Logger.info("[Alice] SELECT balance FROM accounts WHERE id = 1")
                cur.execute("SELECT balance FROM accounts WHERE id = 1")
                balance = cur.fetchone()[0]
                Logger.info(f"[Alice] Прочитала: {balance}")
                
                time.sleep(1.5)
                
                new_balance = balance - 100
                Logger.info(f"[Alice] UPDATE accounts SET balance = {new_balance}")
                cur.execute("UPDATE accounts SET balance = %s WHERE id = 1", (new_balance,))
                
                Logger.info("[Alice] COMMIT")
                cur.execute("COMMIT")
        
        # Транзакция B: Bob
        def transaction_bob():
            time.sleep(0.5)
            with DatabaseConnection() as conn:
                conn.autocommit = False
                cur = conn.cursor()
                
                Logger.info("[Bob] BEGIN")
                cur.execute("BEGIN")
                
                Logger.info("[Bob] SELECT balance FROM accounts WHERE id = 1")
                cur.execute("SELECT balance FROM accounts WHERE id = 1")
                balance = cur.fetchone()[0]
                Logger.info(f"[Bob] Прочитал: {balance}")
                
                time.sleep(1)
                
                new_balance = balance - 200
                Logger.info(f"[Bob] UPDATE accounts SET balance = {new_balance}")
                cur.execute("UPDATE accounts SET balance = %s WHERE id = 1", (new_balance,))
                
                Logger.info("[Bob] COMMIT")
                cur.execute("COMMIT")
        
        # Запуск
        threads = [
            threading.Thread(target=transaction_alice),
            threading.Thread(target=transaction_bob)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        with DatabaseConnection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT balance FROM accounts WHERE id = 1")
            final_balance = cur.fetchone()[0]
            
            if final_balance != 700:
                Logger.anomaly(f"Lost update! Ожидалось 700, получено {final_balance}")
            else:
                Logger.success(f"Корректный результат: {final_balance}")
        
        self.show_balance("После lost update")
        
        # Демонстрация исправления
        self.demo_lost_update_fixed()
    
    def demo_lost_update_fixed(self):
        """
        Исправление lost update с помощью SELECT FOR UPDATE
        """
        Logger.info("\n" + "="*70)
        Logger.info("ИСПРАВЛЕНИЕ LOST UPDATE с SELECT FOR UPDATE")
        Logger.info("="*70)
        
        self.setup_database()
        
        def transaction_alice_fixed():
            with DatabaseConnection() as conn:
                conn.autocommit = False
                cur = conn.cursor()
                
                Logger.info("[Alice-Fixed] BEGIN")
                cur.execute("BEGIN")
                
                Logger.info("[Alice-Fixed] SELECT balance FROM accounts WHERE id = 1 FOR UPDATE")
                cur.execute("SELECT balance FROM accounts WHERE id = 1 FOR UPDATE")
                balance = cur.fetchone()[0]
                Logger.info(f"[Alice-Fixed] Заблокировала строку, balance = {balance}")
                
                time.sleep(1.5)
                
                new_balance = balance - 100
                cur.execute("UPDATE accounts SET balance = %s WHERE id = 1", (new_balance,))
                
                Logger.info("[Alice-Fixed] COMMIT")
                cur.execute("COMMIT")
        
        def transaction_bob_fixed():
            time.sleep(0.5)
            with DatabaseConnection() as conn:
                conn.autocommit = False
                cur = conn.cursor()
                
                Logger.info("[Bob-Fixed] BEGIN")
                cur.execute("BEGIN")
                
                Logger.info("[Bob-Fixed] SELECT balance FROM accounts WHERE id = 1 FOR UPDATE (ждет Alice...)")
                cur.execute("SELECT balance FROM accounts WHERE id = 1 FOR UPDATE")
                balance = cur.fetchone()[0]
                Logger.info(f"[Bob-Fixed] Получил блокировку, balance = {balance}")
                
                new_balance = balance - 200
                cur.execute("UPDATE accounts SET balance = %s WHERE id = 1", (new_balance,))
                
                Logger.info("[Bob-Fixed] COMMIT")
                cur.execute("COMMIT")
        
        threads = [
            threading.Thread(target=transaction_alice_fixed),
            threading.Thread(target=transaction_bob_fixed)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        with DatabaseConnection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT balance FROM accounts WHERE id = 1")
            final_balance = cur.fetchone()[0]
            
            if final_balance == 700:
                Logger.success(f"✅ Исправлено! Итоговый баланс: {final_balance}")
            else:
                Logger.error(f"Ошибка: баланс = {final_balance}")
        
        self.show_balance("После исправления")

def main():
    print(f"\n{Colors.BOLD}{Colors.PURPLE}")
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║     ДЕМОНСТРАЦИЯ АНОМАЛИЙ ИЗОЛЯЦИИ В POSTGRESQL                  ║")
    print("║     Dirty Read (НЕВОЗМОЖЕН) | Non-repeatable | Phantom | Lost    ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")
    
    demo = AnomaliesDemo()
    
    try:
        demo.demo_dirty_read()
        time.sleep(2)
        
        demo.demo_non_repeatable_read()
        time.sleep(2)
        
        demo.demo_phantom_read()
        time.sleep(2)
        
        demo.demo_lost_update()
        
        print(f"\n{Colors.GREEN}{'='*70}")
        print("📊 ИТОГОВАЯ ТАБЛИЦА ЗАЩИТЫ ОТ АНОМАЛИЙ")
        print("="*70)
        print("| Аномалия              | PostgreSQL Уровень изоляции                 |")
        print("|-----------------------|----------------------------------------------|")
        print("| Dirty Read            | НЕВОЗМОЖЕН (MVCC защищает на любом уровне)  |")
        print("| Non-repeatable Read   | REPEATABLE READ                             |")
        print("| Phantom Read          | SERIALIZABLE                                |")
        print("| Lost Update           | SELECT FOR UPDATE / оптимистическая блокировка |")
        print("="*70)
        print(f"{Colors.RESET}")
        
    except KeyboardInterrupt:
        Logger.warning("\nПрограмма прервана пользователем")
    except Exception as e:
        Logger.error(f"Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()