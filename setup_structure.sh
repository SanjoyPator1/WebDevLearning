#!/bin/bash

# Backend Learning Repository Setup Script
# This script creates the complete folder structure for your learning journey

set -e  # Exit on error

echo "🚀 Setting up Backend Learning Repository Structure..."
echo ""

# Function to create a directory if it doesn't exist
create_dir() {
    if [ ! -d "$1" ]; then
        mkdir -p "$1"
        echo "✅ Created: $1"
    else
        echo "⏭️  Already exists: $1"
    fi
}

# Function to create a file if it doesn't exist
create_file() {
    if [ ! -f "$1" ]; then
        touch "$1"
        echo "✅ Created file: $1"
    else
        echo "⏭️  File already exists: $1"
    fi
}

# Create main directories
echo ""
echo "📁 Creating main directories..."
echo ""

# Notes structure
echo "Creating notes structure..."
create_dir "notes"
create_dir "notes/cheat-sheets"

# Phase 1: Python Fundamentals
create_dir "notes/phase-1-python-fundamentals"
for week in {1..2}; do
    create_dir "notes/phase-1-python-fundamentals/week-$week"
done
create_file "notes/phase-1-python-fundamentals/README.md"

# Phase 2: FastAPI
create_dir "notes/phase-2-fastapi"
for week in {3..6}; do
    create_dir "notes/phase-2-fastapi/week-$week"
done
create_file "notes/phase-2-fastapi/README.md"

# Phase 3: Database
create_dir "notes/phase-3-database"
for week in {7..10}; do
    create_dir "notes/phase-3-database/week-$week"
done
create_file "notes/phase-3-database/README.md"

# Phase 4: API Design
create_dir "notes/phase-4-api-design"
for week in {11..13}; do
    create_dir "notes/phase-4-api-design/week-$week"
done
create_file "notes/phase-4-api-design/README.md"

# Phase 5: Advanced Concepts
create_dir "notes/phase-5-advanced-concepts"
for week in {14..18}; do
    create_dir "notes/phase-5-advanced-concepts/week-$week"
done
create_file "notes/phase-5-advanced-concepts/README.md"

# Phase 6: Search and Storage
create_dir "notes/phase-6-search-and-storage"
for week in {19..20}; do
    create_dir "notes/phase-6-search-and-storage/week-$week"
done
create_file "notes/phase-6-search-and-storage/README.md"

# Phase 7: System Design
create_dir "notes/phase-7-system-design"
for week in {21..26}; do
    create_dir "notes/phase-7-system-design/week-$week"
done
create_file "notes/phase-7-system-design/README.md"

# Phase 8: DevOps
create_dir "notes/phase-8-devops"
for week in {27..29}; do
    create_dir "notes/phase-8-devops/week-$week"
done
create_file "notes/phase-8-devops/README.md"

# Phase 9: Production
create_dir "notes/phase-9-production"
for week in {30..32}; do
    create_dir "notes/phase-9-production/week-$week"
done
create_file "notes/phase-9-production/README.md"

# Projects structure
echo ""
echo "Creating projects structure..."
projects=(
    "01-cli-data-aggregator"
    "02-blog-api"
    "03-ecommerce-database"
    "04-social-media-api"
    "05-job-processing-system"
    "06-content-management"
    "07-deployment-pipeline"
    "08-enterprise-application"
)

create_dir "projects"
for project in "${projects[@]}"; do
    create_dir "projects/$project"
    create_file "projects/$project/README.md"
    create_file "projects/$project/requirements.txt"
    create_file "projects/$project/.env.example"
    create_file "projects/$project/.gitignore"
done

# Exercises structure with numerical prefixes
echo ""
echo "Creating exercises structure..."

# 01-python-fundamentals
create_dir "exercises/01-python-fundamentals"
create_dir "exercises/01-python-fundamentals/01-decorators"
create_dir "exercises/01-python-fundamentals/01-decorators/solutions"
create_dir "exercises/01-python-fundamentals/02-context-managers"
create_dir "exercises/01-python-fundamentals/02-context-managers/solutions"
create_dir "exercises/01-python-fundamentals/03-generators"
create_dir "exercises/01-python-fundamentals/03-generators/solutions"
create_dir "exercises/01-python-fundamentals/04-async"
create_dir "exercises/01-python-fundamentals/04-async/solutions"
create_dir "exercises/01-python-fundamentals/05-type-hints"
create_dir "exercises/01-python-fundamentals/05-type-hints/solutions"

# 02-fastapi
create_dir "exercises/02-fastapi"
create_dir "exercises/02-fastapi/01-basic-routes"
create_dir "exercises/02-fastapi/02-dependency-injection"
create_dir "exercises/02-fastapi/03-authentication"
create_dir "exercises/02-fastapi/04-testing"

# 03-database
create_dir "exercises/03-database"
create_dir "exercises/03-database/01-sql-queries"
create_dir "exercises/03-database/02-sqlalchemy"
create_dir "exercises/03-database/03-optimization"

# 04-system-design
create_dir "exercises/04-system-design"
create_dir "exercises/04-system-design/01-url-shortener"
create_dir "exercises/04-system-design/02-rate-limiter"
create_dir "exercises/04-system-design/03-cache"


# System Design structure
echo ""
echo "Creating system design structure..."
create_dir "system-design"
create_dir "system-design/templates"
create_dir "system-design/solutions"

system_designs=(
    "01-url-shortener"
    "02-rate-limiter"
    "03-distributed-cache"
    "04-notification-service"
    "05-chat-application"
    "06-news-feed"
    "07-ecommerce"
    "08-video-streaming"
    "09-autocomplete"
    "10-ride-sharing"
    "11-web-crawler"
    "12-ticket-booking"
)

for design in "${system_designs[@]}"; do
    create_dir "system-design/solutions/$design"
    create_dir "system-design/solutions/$design/diagrams"
    create_file "system-design/solutions/$design/requirements.md"
    create_file "system-design/solutions/$design/design.md"
done

create_file "system-design/practice-log.md"
create_file "system-design/templates/design-template.md"

# Resources structure
echo ""
echo "Creating resources structure..."
create_dir "resources"
create_dir "resources/books"
create_dir "resources/articles"
create_dir "resources/videos"
create_dir "resources/tools"

create_file "resources/books/reading-list.md"
create_file "resources/articles/saved-articles.md"
create_file "resources/videos/tutorials.md"
create_file "resources/tools/recommended-tools.md"

# Snippets structure
echo ""
echo "Creating snippets structure..."
create_dir "snippets"
create_dir "snippets/auth"
create_dir "snippets/database"
create_dir "snippets/caching"
create_dir "snippets/testing"

# Templates structure
echo ""
echo "Creating templates structure..."
create_dir "templates"
create_dir "templates/fastapi-starter"
create_dir "templates/fastapi-starter/app"
create_dir "templates/fastapi-starter/tests"
create_file "templates/fastapi-starter/README.md"
create_file "templates/fastapi-starter/requirements.txt"
create_file "templates/fastapi-starter/docker-compose.yml"

create_dir "templates/microservice-template"
create_dir "templates/microservice-template/app"
create_dir "templates/microservice-template/tests"
create_dir "templates/microservice-template/k8s"
create_file "templates/microservice-template/README.md"

# Diagrams structure
echo ""
echo "Creating diagrams structure..."
create_dir "diagrams"
create_dir "diagrams/phase-1"
create_dir "diagrams/phase-2"
create_dir "diagrams/phase-3"
create_dir "diagrams/phase-4"
create_dir "diagrams/phase-5"
create_dir "diagrams/phase-6"
create_dir "diagrams/phase-7"
create_dir "diagrams/phase-8"
create_dir "diagrams/phase-9"
create_dir "diagrams/system-designs"

# Create PROGRESS.md if it doesn't exist
echo ""
echo "Creating progress tracker..."
if [ ! -f "PROGRESS.md" ]; then
    cat > PROGRESS.md << 'EOF'
# Learning Progress Tracker

**Start Date**: [Add your start date]  
**Target Completion**: [Add target date]

## Overall Progress: 0% (Week 0 of 32)

---

## 📊 Phase Progress

### Phase 1: Python Fundamentals ⏳
- Week 1: ⏳ Not Started
- Week 2: ⏳ Not Started
- Mini Project 1: ⏳ Not Started

### Phase 2: FastAPI Mastery ⏳
- Week 3: ⏳ Not Started
- Week 4: ⏳ Not Started
- Week 5: ⏳ Not Started
- Week 6: ⏳ Not Started
- Mini Project 2: ⏳ Not Started

### Phase 3: Database & ORMs ⏳
- Week 7: ⏳ Not Started
- Week 8: ⏳ Not Started
- Week 9: ⏳ Not Started
- Week 10: ⏳ Not Started
- Mini Project 3: ⏳ Not Started

### Phase 4: API Design & Architecture ⏳
- Week 11: ⏳ Not Started
- Week 12: ⏳ Not Started
- Week 13: ⏳ Not Started
- Mini Project 4: ⏳ Not Started

### Phase 5: Advanced Backend Concepts ⏳
- Week 14: ⏳ Not Started
- Week 15: ⏳ Not Started
- Week 16: ⏳ Not Started
- Week 17: ⏳ Not Started
- Week 18: ⏳ Not Started
- Mini Project 5: ⏳ Not Started

### Phase 6: Search, File Storage & Services ⏳
- Week 19: ⏳ Not Started
- Week 20: ⏳ Not Started
- Mini Project 6: ⏳ Not Started

### Phase 7: System Design & Scalability ⏳
- Week 21: ⏳ Not Started
- Week 22: ⏳ Not Started
- Week 23: ⏳ Not Started
- Week 24: ⏳ Not Started
- Week 25: ⏳ Not Started
- Week 26: ⏳ Not Started

### Phase 8: DevOps & Deployment ⏳
- Week 27: ⏳ Not Started
- Week 28: ⏳ Not Started
- Week 29: ⏳ Not Started
- Mini Project 7: ⏳ Not Started

### Phase 9: Production Best Practices ⏳
- Week 30: ⏳ Not Started
- Week 31: ⏳ Not Started
- Week 32: ⏳ Not Started
- Mini Project 8: ⏳ Not Started

---

## 🎯 Mini Projects Checklist

- [ ] Project 1: CLI Data Aggregator
- [ ] Project 2: Blog API
- [ ] Project 3: E-commerce Database
- [ ] Project 4: Social Media API
- [ ] Project 5: Job Processing System
- [ ] Project 6: Content Management Platform
- [ ] Project 7: Deployment Pipeline
- [ ] Project 8: Enterprise Application

---

## 🏗️ System Design Practice

**Completed**: 0/12

- [ ] URL Shortener
- [ ] Rate Limiter
- [ ] Distributed Cache
- [ ] Notification Service
- [ ] Real-time Chat Application
- [ ] Social Media News Feed
- [ ] E-commerce Platform
- [ ] Video Streaming Platform
- [ ] Search Autocomplete
- [ ] Ride-sharing Service
- [ ] Web Crawler
- [ ] Ticket Booking System

---

## 📅 Weekly Log

### Week 0 - Setup
**Date**: [Current Date]

**Activities**:
- ✅ Set up repository structure
- ✅ Created roadmap
- ⏳ Ready to start Phase 1

---

## 📈 Statistics

- **Total Hours Logged**: 0
- **Current Streak**: 0 days
- **Longest Streak**: 0 days
- **Notes Created**: 0
- **Exercises Completed**: 0
- **Projects Completed**: 0/8
- **System Designs Completed**: 0/12

---

## 💡 Key Learnings & Insights

### Week 0
- Repository structure set up successfully
- Ready to begin learning journey

---

## 🎯 Current Focus

**This Week**: Setup and preparation  
**Next Week**: Phase 1 - Python Fundamentals

---

## 📝 Notes

Add any additional notes, reflections, or observations here.
EOF
    echo "✅ Created: PROGRESS.md"
else
    echo "⏭️  PROGRESS.md already exists"
fi

# Create .gitignore if it doesn't exist
echo ""
echo "Creating .gitignore..."
if [ ! -f ".gitignore" ]; then
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
env.bak/
venv.bak/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environments
.venv/
venv/
ENV/
env/

# Environment variables
.env
.env.local
.env.*.local
*.env

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
*.sublime-project
*.sublime-workspace

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Databases
*.db
*.sqlite
*.sqlite3

# Logs
*.log
logs/
log/

# Docker
docker-compose.override.yml

# Jupyter Notebooks
.ipynb_checkpoints
*.ipynb

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# pytype static type analyzer
.pytype/

# Temporary files
*.tmp
tmp/
temp/
*.bak

# OS specific
Thumbs.db
.DS_Store

# Node modules (if using any frontend tooling)
node_modules/

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/

# Compiled files
*.pyc
*.pyo
*.pyd

# Secrets and credentials
secrets/
credentials/
*.key
*.pem
*.crt

# Generated documentation
docs/_build/
site/
EOF
    echo "✅ Created: .gitignore"
else
    echo "⏭️  .gitignore already exists"
fi

# Create a template for system design
echo ""
echo "Creating system design template..."
if [ ! -f "system-design/templates/design-template.md" ]; then
    cat > system-design/templates/design-template.md << 'EOF'
# System Design: [System Name]

**Date**: [Current Date]  
**Time Taken**: [X minutes]  
**Difficulty**: [Easy/Medium/Hard]

---

## 1. Requirements Clarification (5 minutes)

### Functional Requirements
- [ ] Requirement 1
- [ ] Requirement 2
- [ ] Requirement 3

### Non-Functional Requirements
- [ ] Scalability
- [ ] Availability
- [ ] Latency
- [ ] Consistency
- [ ] Durability

### Assumptions
- Assumption 1
- Assumption 2

### Out of Scope
- Item 1
- Item 2

---

## 2. Capacity Estimation (5 minutes)

### Traffic Estimates
- **Daily Active Users (DAU)**: 
- **Requests per second (QPS)**: 
- **Peak QPS**: 
- **Read/Write ratio**: 

### Storage Estimates
- **Data per user/item**: 
- **Total data for X years**: 
- **Database size**: 

### Bandwidth Estimates
- **Incoming data**: 
- **Outgoing data**: 

### Memory Estimates
- **Cache size (20% rule)**: 

---

## 3. System Interface Definition (5 minutes)

### API Endpoints

```
POST /api/v1/resource
GET /api/v1/resource/{id}
PUT /api/v1/resource/{id}
DELETE /api/v1/resource/{id}
```

### Request/Response Examples

```json
// Request
{
  "field1": "value1"
}

// Response
{
  "id": "123",
  "field1": "value1"
}
```

---

## 4. High-Level Design (10 minutes)

### Components
1. **Component 1**: Description
2. **Component 2**: Description
3. **Component 3**: Description

### Architecture Diagram

```
[Draw or describe the high-level architecture]

Client -> Load Balancer -> App Servers -> Database
                        -> Cache
                        -> Message Queue
```

### Data Flow
1. Step 1
2. Step 2
3. Step 3

---

## 5. Detailed Design (15 minutes)

### Database Schema

```sql
CREATE TABLE users (
  id BIGINT PRIMARY KEY,
  username VARCHAR(50),
  created_at TIMESTAMP
);
```

### Caching Strategy
- **What to cache**: 
- **Cache invalidation**: 
- **Cache eviction policy**: 

### Load Balancing
- **Algorithm**: 
- **Health checks**: 

### Database Scaling
- **Sharding strategy**: 
- **Replication**: 
- **Partitioning**: 

### Message Queue (if applicable)
- **Queue type**: 
- **Message format**: 
- **Consumer groups**: 

---

## 6. Bottlenecks & Trade-offs (10 minutes)

### Potential Bottlenecks
1. **Database**: 
   - Problem: 
   - Solution: 

2. **Network**: 
   - Problem: 
   - Solution: 

### Trade-offs
1. **Consistency vs Availability**: 
2. **Latency vs Throughput**: 
3. **Cost vs Performance**: 

### Single Points of Failure
- Component 1 + mitigation
- Component 2 + mitigation

---

## 7. Additional Considerations

### Monitoring & Alerting
- Metrics to track
- Alert thresholds

### Security
- Authentication
- Authorization
- Data encryption

### Failure Scenarios
- Scenario 1 + handling
- Scenario 2 + handling

---

## 8. Follow-up Questions

1. How would you handle [specific scenario]?
2. What if the scale increased 10x?
3. How would you ensure data consistency?

---

## 9. Implementation Notes

[Any specific implementation details or code snippets]

---

## 10. References

- [Link to relevant articles]
- [Link to similar systems]
EOF
    echo "✅ Created: system-design/templates/design-template.md"
fi

# Create README files for each phase with basic structure
echo ""
echo "Creating phase README files..."

phases=(
    "phase-1-python-fundamentals:Python Fundamentals:1-2:Master advanced Python concepts"
    "phase-2-fastapi:FastAPI Mastery:3-6:Build production-ready APIs"
    "phase-3-database:Database & ORMs:7-10:Master database design and optimization"
    "phase-4-api-design:API Design & Architecture:11-13:Learn API design patterns"
    "phase-5-advanced-concepts:Advanced Backend Concepts:14-18:Performance and distributed systems"
    "phase-6-search-and-storage:Search & File Storage:19-20:Search engines and object storage"
    "phase-7-system-design:System Design & Scalability:21-26:Design scalable systems"
    "phase-8-devops:DevOps & Deployment:27-29:Docker, Kubernetes, CI/CD"
    "phase-9-production:Production Best Practices:30-32:Security, testing, monitoring"
)

for phase_info in "${phases[@]}"; do
    IFS=':' read -r phase_dir phase_name weeks goal <<< "$phase_info"
    readme_file="notes/$phase_dir/README.md"
    
    if [ ! -f "$readme_file" ] || [ ! -s "$readme_file" ]; then
        cat > "$readme_file" << EOF
# $phase_name

**Duration**: Weeks $weeks  
**Goal**: $goal

---

## 📚 Overview

[Add phase overview here]

---

## 🎯 Learning Objectives

- Objective 1
- Objective 2
- Objective 3

---

## 📖 Weekly Breakdown

EOF
        
        # Add week sections based on the weeks range
        IFS='-' read -r start_week end_week <<< "$weeks"
        for ((week=start_week; week<=end_week; week++)); do
            cat >> "$readme_file" << EOF
### Week $week
**Topics**: 
- Topic 1
- Topic 2

**Notes**: \`week-$week/\`

EOF
        done
        
        cat >> "$readme_file" << EOF

---

## 🛠️ Mini Project

[Describe the mini project for this phase]

**Requirements**:
- Requirement 1
- Requirement 2

**Skills Practiced**:
- Skill 1
- Skill 2

---

## 📚 Resources

- [Resource 1](url)
- [Resource 2](url)

---

## ✅ Completion Checklist

- [ ] Complete all week notes
- [ ] Complete all exercises
- [ ] Build mini project
- [ ] Review and refactor code
- [ ] Document learnings

---

## 📝 Personal Notes

Add your own insights, challenges, and breakthroughs here.
EOF
        echo "✅ Created: $readme_file"
    fi
done

# Create summary
echo ""
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✨ Setup Complete! ✨"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📁 Created folder structure with:"
echo "   • 9 learning phases with 32 weeks"
echo "   • 8 mini project directories"
echo "   • Exercise directories for practice"
echo "   • System design templates and solutions"
echo "   • Resources and snippets folders"
echo "   • Progress tracker and templates"
echo ""
echo "📝 Next steps:"
echo "   1. Review PROGRESS.md and add your start date"
echo "   2. Commit this structure to git:"
echo "      git add ."
echo "      git commit -m 'Initial folder structure setup'"
echo "      git push origin main"
echo "   3. Start with Phase 1, Week 1!"
echo ""
echo "🚀 Happy Learning!"
echo "═══════════════════════════════════════════════════════════"
echo ""