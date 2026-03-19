# Схема базы данных

## Обзор

База данных PostgreSQL хранит информацию о пользователях, их анкетах, взаимодействиях и рейтингах.

## Таблицы

### tg_users

Таблица пользователей Telegram.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| id | UUID | PK | Уникальный идентификатор |
| tg_id | BIGINT | UNIQUE, NOT NULL | ID пользователя в Telegram |
| username | VARCHAR(255) | | Имя пользователя |
| first_name | VARCHAR(255) | NOT NULL | Имя |
| last_name | VARCHAR(255) | | Фамилия |
| created_at | TIMESTAMP | NOT NULL | Дата создания |
| updated_at | TIMESTAMP | | Дата обновления |

### profiles

Таблица анкет пользователей.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| id | UUID | PK | Уникальный идентификатор |
| user_id | UUID | FK -> tg_users.id | Ссылка на пользователя |
| name | VARCHAR(255) | | Имя |
| age | INTEGER | NOT NULL | Возраст |
| gender | VARCHAR(20) | NOT NULL | Пол |
| city | VARCHAR(100) | NOT NULL | Город |
| country | VARCHAR(100) | | Страна |
| bio | TEXT | | О себе |
| interests | JSONB | | Интересы |
| preferences | JSONB | | Предпочтения |
| created_at | TIMESTAMP | NOT NULL | Дата создания |
| updated_at | TIMESTAMP | | Дата обновления |

### photos

Таблица фотографий анкет.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| id | UUID | PK | Уникальный идентификатор |
| profile_id | UUID | FK -> profiles.id | Ссылка на анкету |
| url | VARCHAR(500) | NOT NULL | URL изображения |
| is_primary | BOOLEAN | DEFAULT FALSE | Главное фото |
| created_at | TIMESTAMP | NOT NULL | Дата загрузки |

### likes

Таблица лайков.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| id | UUID | PK | Уникальный идентификатор |
| liker_id | UUID | FK -> tg_users.id | Кто поставил лайк |
| liked_id | UUID | FK -> tg_users.id | Кому поставили лайк |
| created_at | TIMESTAMP | NOT NULL | Дата лайка |

### matches

Таблица мэтчей (взаимных лайков).

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| id | UUID | PK | Уникальный идентификатор |
| user_id | UUID | FK -> tg_users.id | Первый пользователь |
| matched_user_id | UUID | FK -> tg_users.id | Второй пользователь |
| chat_id | UUID | | Ссылка на чат |
| created_at | TIMESTAMP | NOT NULL | Дата мэтча |

### chats

Таблица чатов между пользователями.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| id | UUID | PK | Уникальный идентификатор |
| match_id | UUID | FK -> matches.id | Ссылка на мэтч |
| user_id | UUID | FK -> tg_users.id | Участник чата |
| last_message_id | UUID | | Последнее сообщение |
| created_at | TIMESTAMP | NOT NULL | Дата создания |
| updated_at | TIMESTAMP | | Дата обновления |

### messages

Таблица сообщений.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| id | UUID | PK | Уникальный идентификатор |
| chat_id | UUID | FK -> chats.id | Ссылка на чат |
| sender_id | UUID | FK -> tg_users.id | Отправитель |
| text | TEXT | | Текст сообщения |
| created_at | TIMESTAMP | NOT NULL | Дата отправки |

### ratings

Таблица рейтингов пользователей.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| id | UUID | PK | Уникальный идентификатор |
| user_id | UUID | FK -> tg_users.id | Ссылка на пользователя |
| primary_rating | FLOAT | DEFAULT 0 | Первичный рейтинг |
| behavioral_rating | FLOAT | DEFAULT 0 | Поведенческий рейтинг |
| final_rating | FLOAT | DEFAULT 0 | Итоговый рейтинг |
| updated_at | TIMESTAMP | | Дата обновления |

### referrals

Таблица рефералов (приглашённых пользователей).

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| id | UUID | PK | Уникальный идентификатор |
| referrer_id | UUID | FK -> tg_users.id | Пригласивший |
| referred_id | UUID | FK -> tg_users.id | Приглашённый |
| created_at | TIMESTAMP | NOT NULL | Дата приглашения |

## ER-диаграмма

![DB Scheme](DB%20scheme.png)

## Связи между таблицами

```
tg_users (1) ────── (1) profiles
      │
      ├── (1:N) likes
      │
      ├── (1:N) matches
      │         │
      │         └── (1:1) chats
      │                   │
      │                   └── (1:N) messages
      │
      ├── (1:N) ratings
      │
      └── (1:N) referrals
```

## Индексы

| Таблица | Колонки | Тип | Описание |
|---------|---------|-----|----------|
| tg_users | tg_id | UNIQUE | Уникальный Telegram ID |
| profiles | user_id | UNIQUE | Уникальная анкета |
| profiles | city, gender | INDEX | Поиск по городу и полу |
| likes | liker_id | INDEX | Лайки пользователя |
| likes | liked_id | INDEX | Лайки на анкету |
| matches | user_id | INDEX | Мэтчи пользователя |
| chats | match_id | INDEX | Поиск чата по мэтчу |
| messages | chat_id | INDEX | Сообщения чата |
| ratings | final_rating | INDEX | Сортировка по рейтингу |

## Миграции

Миграции выполняются с помощью Alembic:

```bash
alembic revision --autogenerate -m "create users table"
alembic upgrade head
```
