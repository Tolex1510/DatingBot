# Архитектура системы

## Обзор

Dating Bot построен на микросервисной архитектуре с использованием RabbitMQ для асинхронного взаимодействия между сервисами.

## Схема архитектуры (Mermaid)

```mermaid
flowchart TB
    subgraph External["Внешние системы"]
        TG["Telegram"]
        S3["Minio S3"]
    end

    subgraph Clients["Клиенты"]
        BotClient["Telegram Bot"]
    end

    BotClient <--> TG
    
    subgraph Services["Сервисы"]
        BotService["Bot Service"]
        UserService["User Service"]
        ProfileService["Profile Service"]
        MatchService["Match Service"]
        ChatService["Chat Service"]
        RatingService["Rating Service"]
    end

    subgraph Infrastructure["Инфраструктура"]
        Redis["Redis"]
        RabbitMQ["RabbitMQ"]
        PostgreSQL["PostgreSQL"]
    end

    subgraph Workers["Workers"]
        CeleryWorkers["Celery Workers"]
    end

    %% Client to Services
    BotClient --> BotService
    
    %% Services interactions
    BotService --> UserService
    BotService --> ProfileService
    BotService --> MatchService
    BotService --> ChatService
    BotService --> RatingService
    
    %% Services to Infrastructure
    UserService --> PostgreSQL
    ProfileService --> PostgreSQL
    MatchService --> PostgreSQL
    ChatService --> PostgreSQL
    RatingService --> PostgreSQL
    
    ProfileService --> Redis
    BotService --> Redis
    RatingService --> Redis
    
    ProfileService --> RabbitMQ
    MatchService --> RabbitMQ
    RatingService --> RabbitMQ
    ChatService --> RabbitMQ
    
    RabbitMQ --> CeleryWorkers
    
    ProfileService --> S3
```

## Потоки данных

```mermaid
sequenceDiagram
    participant U as Пользователь
    participant B as Bot Service
    participant P as Profile Service
    participant M as Match Service
    participant R as Rating Service
    participant DB as PostgreSQL
    participant C as Redis
    participant MQ as RabbitMQ
    participant W as Celery

    U->>B: /start
    B->>P: Create profile
    P->>DB: Save profile
    DB-->>P: OK
    P-->>B: Profile created
    B-->>U: Анкета создана

    U->>B: Показать анкету
    B->>R: Get next profile
    R->>C: Check cache
    alt Cache hit
        C-->>R: Profiles
    else Cache miss
        R->>DB: Query ranked
        DB-->>R: Profiles
        R->>C: Cache profiles
    end
    R-->>B: Profile
    B-->>U: Показать анкету

    U->>B: Лайк
    B->>M: Process like
    M->>DB: Save like
    M->>MQ: Publish event
    MQ-->>M: ACK
    M-->>B: Like saved
    B-->>U: Лайк поставлен

    MQ->>W: Process event
    W->>M: Check match
    M->>DB: Check mutual like
    alt Match found
        M->>DB: Create match
        M->>MQ: Notify
        MQ->>W: Send notification
        W->>B: Send message
        B-->>U: Это мэтч!
    end

    W->>R: Update rating
    R->>DB: Recalculate
    R->>C: Update cache
```

## Сервисы

### Bot Service
Обработка команд Telegram, интерфейс пользователя, отправка уведомлений о мэтчах и сообщениях.

### User Service
Управление пользователями Telegram: регистрация, профиль, настройки.

### Profile Service
CRUD операции с анкетами: создание, редактирование, поиск, загрузка фотографий в S3.

### Match Service
Обработка лайков, проверка взаимных лайков, создание мэтчей, отправка уведомлений.

### Chat Service
Управление чатами между пользователями, отправка и получение сообщений.

### Rating Service
Расчёт рейтингов (3 уровня), ранжирование анкет, кэширование отсортированных списков.

| Сервис | Порт |
|--------|------|
| Bot Service | 8001 |
| User Service | 8002 |
| Profile Service | 8003 |
| Match Service | 8004 |
| Chat Service | 8005 |
| Rating Service | 8006 |

## Технологический стек

| Компонент | Технология |
|-----------|-------------|
| Backend | Python FastAPI |
| Bot | python-telegram-bot |
| Database | PostgreSQL |
| Cache | Redis |
| Queue | RabbitMQ |
| Tasks | Celery |
| Storage | Minio (S3) |
| Gateway | Nginx |

## Взаимодействие

- **Синхронное**: REST API через Nginx Gateway
- **Асинхронное**: RabbitMQ → Celery Workers

## Масштабирование

- Горизонтальное масштабирование сервисов
- Redis для кэширования
- RabbitMQ для балансировки нагрузки
