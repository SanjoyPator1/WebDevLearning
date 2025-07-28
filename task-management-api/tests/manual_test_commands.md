# Manual Testing Commands for Database Migration

## 1. Start Application

uvicorn app.main:app --reload

## 2. Health Check

curl http://localhost:8000/health

## 3. Login with Seed Data

curl -X POST "http://localhost:8000/auth/login" \
 -H "Content-Type: application/x-www-form-urlencoded" \
 -d "username=admin@taskmanager.com&password=admin123"

## 4. Test Protected Endpoint

# (Replace YOUR_TOKEN with token from step 3)

curl -X GET "http://localhost:8000/auth/me" \
 -H "Authorization: Bearer YOUR_TOKEN"

## 5. Create Task

curl -X POST "http://localhost:8000/tasks/" \
 -H "Content-Type: application/json" \
 -H "Authorization: Bearer YOUR_TOKEN" \
 -d '{"title": "Migration Test Task", "priority": "high"}'

## 6. Get User Tasks

curl -X GET "http://localhost:8000/tasks/" \
 -H "Authorization: Bearer YOUR_TOKEN"
