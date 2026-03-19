# API Эндпоинты

## Пользователи

### Регистрация пользователя

```
POST /api/v1/users/register
```

**Тело запроса:**
```json
{
  "telegram_id": 123456789,
  "username": "string",
  "first_name": "string",
  "last_name": "string"
}
```

**Ответ:**
```json
{
  "id": "uuid",
  "telegram_id": 123456789,
  "username": "string",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Получение профиля пользователя

```
GET /api/v1/users/{user_id}
```

**Ответ:**
```json
{
  "id": "uuid",
  "telegram_id": 123456789,
  "username": "string",
  "first_name": "string",
  "last_name": "string",
  "profile": {
    "age": 25,
    "gender": "male",
    "city": "Moscow",
    "interests": ["music", "sports"],
    "photos": ["url1", "url2"]
  },
  "rating": {
    "primary": 0.75,
    "behavioral": 0.82,
    "final": 0.79
  }
}
```

## Анкеты

### Создание анкеты

```
POST /api/v1/profiles
```

**Тело запроса:**
```json
{
  "age": 25,
  "gender": "male",
  "city": "Moscow",
  "country": "Russia",
  "interests": ["music", "sports", "travel"],
  "bio": "Looking for serious relationship",
  "preferences": {
    "min_age": 20,
    "max_age": 30,
    "gender": "female",
    "city": "Moscow"
  }
}
```

### Обновление анкеты

```
PUT /api/v1/profiles/{profile_id}
```

### Удаление анкеты

```
DELETE /api/v1/profiles/{profile_id}
```

### Получение списка анкет

```
GET /api/v1/profiles
```

**Параметры запроса:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| limit | int | Количество анкет (по умолчанию 10) |
| offset | int | Смещение |
| min_rating | float | Минимальный рейтинг |
| gender | string | Пол |

### Получение следующей анкеты для просмотра

```
GET /api/v1/profiles/next
```

**Ответ:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "age": 25,
  "gender": "female",
  "city": "Moscow",
  "interests": ["music", "travel"],
  "photos": ["url1", "url2"],
  "rating": 0.75
}
```

## Взаимодействия

### Лайк анкеты

```
POST /api/v1/profiles/{profile_id}/like
```

**Тело запроса:**
```json
{
  "liked_profile_id": "uuid"
}
```

**Ответ:**
```json
{
  "match": true,
  "chat_id": "uuid"
}
```

### Пропуск анкеты

```
POST /api/v1/profiles/{profile_id}/skip
```

### Суперлайк

```
POST /api/v1/profiles/{profile_id}/superlike
```

## Мэтчи

### Получение списка мэтчей

```
GET /api/v1/matches
```

**Ответ:**
```json
{
  "matches": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "matched_user_id": "uuid",
      "matched_at": "2024-01-01T00:00:00Z",
      "chat_id": "uuid"
    }
  ]
}
```

## Рейтинг

### Получение рейтинга пользователя

```
GET /api/v1/rating/{user_id}
```

**Ответ:**
```json
{
  "primary_rating": 0.75,
  "behavioral_rating": 0.82,
  "final_rating": 0.79,
  "rank": 150,
  "total_users": 1000
}
```

### Принудительный пересчёт рейтинга

```
POST /api/v1/rating/{user_id}/recalculate
```

## Фотографии

### Загрузка фотографии

```
POST /api/v1/photos/upload
```

**Тело запроса:**
```
Content-Type: multipart/form-data
```

**Ответ:**
```json
{
  "id": "uuid",
  "url": "https://minio.example.com/photos/uuid.jpg",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Удаление фотографии

```
DELETE /api/v1/photos/{photo_id}
```

## Метрики

### Получение статистики

```
GET /api/v1/metrics
```

**Ответ:**
```json
{
  "total_users": 1000,
  "active_users": 500,
  "total_matches": 250,
  "avg_rating": 0.65,
  "daily_likes": 1000,
  "daily_messages": 5000
}
```
