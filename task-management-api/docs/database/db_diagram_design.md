# Task Management System Database Schema

Use this at https://dbdiagram.io/

```dbml
Table users {
  id uuid [primary key]
  email varchar [unique, not null, note: 'Unique user email address']
  password_hash varchar [not null, note: 'Bcrypt hashed password']
  full_name varchar
  email_verified boolean [default: false, note: 'Email verification status']
  created_at timestamp [default: `now()`, note: 'Auto-generated timestamp']
  updated_at timestamp [default: `now()`, note: 'Auto-updated timestamp']
  deleted_at timestamp [null, note: 'Soft delete timestamp']

  indexes {
    email [unique]
    (deleted_at, email) [note: 'Support soft delete queries']
  }
}

Table teams {
  id uuid [primary key]
  name varchar [not null, note: 'Team display name']
  description text [note: 'Optional team description']
  created_by uuid [not null, ref: > users.id, note: 'Team creator reference']
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
  deleted_at timestamp [null, note: 'Soft delete timestamp']

  indexes {
    created_by
    (deleted_at, name)
  }
}

Table projects {
  id uuid [primary key]
  title varchar [not null, note: 'Project name']
  description text [note: 'Project description']
  team_id uuid [not null, ref: > teams.id, note: 'Parent team reference']
  created_by uuid [not null, ref: > users.id, note: 'Project creator reference']
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
  deleted_at timestamp [null, note: 'Soft delete timestamp']

  indexes {
    team_id
    created_by
    (deleted_at, team_id)
  }
}

Table tasks {
  id uuid [primary key]
  title varchar [not null, note: 'Task title, required field']
  description text [note: 'Detailed task description']
  priority varchar [not null, default: 'medium', note: 'Priority: low, medium, high']
  due_date timestamp [null, note: 'Optional task deadline']
  completed boolean [default: false, note: 'Task completion status']
  project_id uuid [not null, ref: > projects.id, note: 'Parent project reference']
  assigned_to uuid [null, ref: > users.id, note: 'Task assignee reference']
  created_by uuid [not null, ref: > users.id, note: 'Task creator reference']
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
  deleted_at timestamp [null, note: 'Soft delete timestamp']

  indexes {
    project_id
    assigned_to
    created_by
    due_date
    (completed, due_date) [note: 'Support task filtering queries']
    (deleted_at, project_id)
  }
}

Table team_members {
  id uuid [primary key]
  team_id uuid [not null, ref: > teams.id, note: 'Team reference']
  user_id uuid [not null, ref: > users.id, note: 'User reference']
  role varchar [not null, default: 'member', note: 'Role: owner, admin, member']
  joined_at timestamp [default: `now()`, note: 'Membership start date']
  left_at timestamp [null, note: 'Soft leave timestamp']

  indexes {
    team_id
    user_id
    (team_id, user_id) [unique, note: 'Prevent duplicate memberships']
    (left_at, team_id) [note: 'Support active member queries']
  }
}

Table task_attachments {
  id uuid [primary key]
  task_id uuid [not null, ref: > tasks.id, note: 'Parent task reference']
  filename varchar [not null, note: 'Original uploaded filename']
  stored_filename varchar [not null, note: 'UUID-based stored filename']
  content_type varchar [not null, note: 'MIME type of the file']
  file_size integer [not null, note: 'File size in bytes']
  description text [note: 'Optional file description']
  uploaded_at timestamp [default: `now()`, note: 'Upload timestamp']

  indexes {
    task_id
    content_type
    uploaded_at
  }
}

Table task_comments {
  id uuid [primary key]
  task_id uuid [not null, ref: > tasks.id, note: 'Parent task reference']
  user_id uuid [not null, ref: > users.id, note: 'Comment author reference']
  content text [not null, note: 'Comment text content']
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
  deleted_at timestamp [null, note: 'Soft delete timestamp']

  indexes {
    task_id
    user_id
    created_at
    (deleted_at, task_id) [note: 'Support active comment queries']
  }
}

```

# 📘 Task Management System: Database Schema Overview

---

## 🔗 Relationship Documentation

> **Note:** Relationships are defined inline with foreign key columns.  
> This section documents the relationship semantics.

### 🧩 Primary Entity Relationships

- `teams.created_by` → `users.id` — _Team creator_
- `projects.team_id` → `teams.id` — _Project belongs to team_
- `projects.created_by` → `users.id` — _Project creator_
- `tasks.project_id` → `projects.id` — _Task belongs to project_
- `tasks.assigned_to` → `users.id` — _Task assignment_
- `tasks.created_by` → `users.id` — _Task creator_

### 👥 Membership Relationships

- `team_members.team_id` → `teams.id` — _Team membership_
- `team_members.user_id` → `users.id` — _User membership_

### 📎 Content Relationships

- `task_attachments.task_id` → `tasks.id` — _Task file attachments_
- `task_comments.task_id` → `tasks.id` — _Task discussion comments_
- `task_comments.user_id` → `users.id` — _Comment authorship_

---

## 🗂️ Table Groups for Visual Organization

```dbml
TableGroup "User Management" {
  users
  team_members
}

TableGroup "Organization Structure" {
  teams
  projects
}

TableGroup "Task Management" {
  tasks
  task_comments
  task_attachments
}

```

---

## 🧠 Notes on Schema Design

### ✅ 1. UUID Primary Keys

- Ensures global uniqueness
- Helps with data migration and distributed systems
- Prevents enumeration attacks

### 🕓 2. Soft Delete Pattern

- Implemented using `deleted_at` timestamp
- Keeps data retrievable while hiding it from UI
- Maintains referential integrity

### 🧭 3. Hierarchical Structure

- `Users → Teams → Projects → Tasks`
- Clear ownership and permission boundaries
- Designed for multi-tenant architecture

### 🛡️ 4. Flexible Membership

- Role-based access control (Owner, Admin, Member)
- Membership timeline with join/leave tracking

### 🧰 5. Rich Task Features

- Priority levels (`low`, `medium`, `high`)
- Optional due dates
- File attachments with metadata
- Threaded comments for collaboration

### 📝 6. Audit Trail

- Tracks creation & update timestamps
- Logs who created each record
- Helps in accountability and debugging

### ⚡ 7. Performance Optimization

- Indexes for common query paths
- Composite indexes for filtered searches
- FK indexes for efficient joins

---

## 🚀 Usage Instructions

1.  Copy the **DBML** code
2.  Open [dbdiagram.io](https://dbdiagram.io/)
3.  Paste the code into the editor
4.  Click **Generate** to visualize the schema
5.  Export diagram as **PNG**, **PDF**, or **SQL**
