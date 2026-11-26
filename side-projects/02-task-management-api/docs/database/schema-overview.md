# Database Schema Overview

## Complete Entity-Relationship Diagram

```mermaid
erDiagram
    USER {
        uuid id PK
        string email UK "Unique, required"
        string password_hash "Bcrypt hashed"
        string full_name
        boolean email_verified "Default false"
        datetime created_at "Auto-generated"
        datetime updated_at "Auto-updated"
        datetime deleted_at "Soft delete"
    }

    TEAM {
        uuid id PK
        string name "Team display name"
        string description "Optional description"
        uuid created_by FK "References USER(id)"
        datetime created_at
        datetime updated_at
        datetime deleted_at
    }

    PROJECT {
        uuid id PK
        string title "Project name"
        string description "Project description"
        uuid team_id FK "References TEAM(id)"
        uuid created_by FK "References USER(id)"
        datetime created_at
        datetime updated_at
        datetime deleted_at
    }

    TASK {
        uuid id PK
        string title "Task title, required"
        string description "Task details"
        string priority "low, medium, high"
        datetime due_date "Optional deadline"
        boolean completed "Default false"
        uuid project_id FK "References PROJECT(id)"
        uuid assigned_to FK "References USER(id)"
        uuid created_by FK "References USER(id)"
        datetime created_at
        datetime updated_at
        datetime deleted_at
    }

    TEAM_MEMBER {
        uuid id PK
        uuid team_id FK
        uuid user_id FK
        string role "owner, admin, member"
        datetime joined_at
        datetime left_at "Soft leave"
    }

    TASK_ATTACHMENT {
        uuid id PK
        uuid task_id FK
        string filename "Original filename"
        string stored_filename "UUID filename"
        string content_type "MIME type"
        integer file_size "Bytes"
        string description "Optional description"
        datetime uploaded_at
    }

    TASK_COMMENT {
        uuid id PK
        uuid task_id FK
        uuid user_id FK
        string content "Comment text"
        datetime created_at
        datetime updated_at
        datetime deleted_at
    }

    %% Primary Relationships
    USER ||--o{ TASK : "creates (created_by)"
    USER ||--o{ TASK : "assigned (assigned_to)"
    USER ||--o{ PROJECT : "creates"
    USER ||--o{ TEAM : "creates"
    USER ||--o{ TASK_COMMENT : "writes"

    %% Hierarchical Relationships
    TEAM ||--o{ PROJECT : "contains"
    PROJECT ||--o{ TASK : "contains"

    %% Membership Relationships
    TEAM ||--o{ TEAM_MEMBER : "has_members"
    USER ||--o{ TEAM_MEMBER : "member_of"

    %% Content Relationships
    TASK ||--o{ TASK_ATTACHMENT : "has_attachments"
    TASK ||--o{ TASK_COMMENT : "has_comments"
```

## Design Principles

### 1. **Soft Deletes**

All main entities use `deleted_at` timestamp instead of hard deletes:

- Preserves data integrity
- Enables audit trails
- Allows data recovery
- Maintains foreign key relationships

### 2. **UUID Primary Keys**

Using UUID instead of auto-incrementing integers:

- Better security (no ID enumeration)
- Distributed system compatibility
- No ID collision in merges
- Better for APIs (no guessable IDs)

### 3. **Audit Fields**

Common audit fields on all entities:

- `created_at`: When record was created
- `updated_at`: When record was last modified
- `created_by`: Who created the record
- `deleted_at`: When record was soft-deleted

### 4. **Relationship Integrity**

Proper foreign key constraints ensure:

- Data consistency
- Referential integrity
- Cascade delete handling
- Index optimization for joins
