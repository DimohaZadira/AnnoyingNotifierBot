#!/usr/bin/env python3
"""
Тест парсинга аргументов команды begin_notif
"""

def test_parse_args():
    """Тестирует парсинг аргументов"""
    
    # Тестовые случаи
    test_cases = [
        {
            "input": ["sosal", "10", "10:00", "@dimoha_zadira", "@ilya_savitsky"],
            "expected": {
                "message": "sosal",
                "interval": 10,
                "time": "10:00",
                "tags": ["@dimoha_zadira", "@ilya_savitsky"]
            }
        },
        {
            "input": ["Пора", "пить", "воду!", "30", "09:00"],
            "expected": {
                "message": "Пора пить воду!",
                "interval": 30,
                "time": "09:00",
                "tags": []
            }
        },
        {
            "input": ["Тест", "15", "14:30", "@user1", "@user2", "@user3"],
            "expected": {
                "message": "Тест",
                "interval": 15,
                "time": "14:30",
                "tags": ["@user1", "@user2", "@user3"]
            }
        },
        {
            "input": ["@user1", "Сообщение", "45", "16:00", "@user2"],
            "expected": {
                "message": "@user1 Сообщение",
                "interval": 45,
                "time": "16:00",
                "tags": ["@user2"]
            }
        }
    ]
    
    print("🧪 Тестирование парсинга аргументов")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Тест {i}:")
        print(f"   Вход: {test_case['input']}")
        
        # Имитируем новую логику парсинга из бота
        args = test_case['input']
        
        # Ищем интервал и время среди аргументов
        interval_minutes = None
        start_time = None
        interval_index = -1
        time_index = -1
        
        import re
        
        for i, arg in enumerate(args):
            # Проверяем, является ли аргумент интервалом (число)
            if interval_minutes is None:
                try:
                    potential_interval = int(arg)
                    if potential_interval > 0:
                        interval_minutes = potential_interval
                        interval_index = i
                        continue
                except ValueError:
                    pass
            
            # Проверяем, является ли аргумент временем (формат HH:MM)
            if start_time is None and re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', arg):
                start_time = arg
                time_index = i
        
        # Проверяем, что нашли интервал и время
        if interval_minutes is None:
            print(f"   ❌ Ошибка: не найден интервал")
            continue
        
        if start_time is None:
            print(f"   ❌ Ошибка: не найдено время")
            continue
        
        # Проверяем порядок: интервал должен быть перед временем
        if interval_index > time_index:
            print(f"   ❌ Ошибка: неправильный порядок аргументов")
            continue
        
        # Собираем сообщение и теги
        message_parts = []
        tagged_users = []
        
        for i, arg in enumerate(args):
            if i == interval_index or i == time_index:
                continue  # Пропускаем интервал и время
            
            if arg.startswith('@'):
                tagged_users.append(arg)
            else:
                message_parts.append(arg)
        
        # Собираем сообщение
        message = " ".join(message_parts)
        
        # Проверяем результат
        result = {
            "message": message,
            "interval": interval_minutes,
            "time": start_time,
            "tags": tagged_users
        }
        
        expected = test_case['expected']
        
        print(f"   Результат:")
        print(f"     Сообщение: '{result['message']}'")
        print(f"     Интервал: {result['interval']}")
        print(f"     Время: {result['time']}")
        print(f"     Теги: {result['tags']}")
        
        # Проверяем соответствие ожидаемому результату
        if (result['message'] == expected['message'] and 
            result['interval'] == expected['interval'] and 
            result['time'] == expected['time'] and 
            result['tags'] == expected['tags']):
            print(f"   ✅ Успешно!")
        else:
            print(f"   ❌ Ошибка! Ожидалось: {expected}")
    
    print(f"\n🎉 Тестирование завершено!")

if __name__ == "__main__":
    test_parse_args() 