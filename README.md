# Backend Development Learning Journey

A comprehensive, structured approach to mastering backend development with Python and FastAPI, progressing from intermediate to senior-level engineering with strong system design capabilities.

## About This Repository

This repository documents my journey to becoming a proficient backend engineer. It contains detailed notes, hands-on projects, coding exercises, and system design practice covering everything from Python fundamentals to production-ready deployments.

**Duration**: 6-8 months (32 weeks)  
**Daily Commitment**: 2-3 hours  
**Target**: Senior-level backend engineer with system design expertise

## Documentation

- **[Complete Roadmap](./Roadmap.md)** - Detailed week-by-week learning path
- **[Progress Tracker](./PROGRESS.md)** - Current learning status and milestones

## Learning Path Overview

The curriculum is divided into 9 phases covering 32 weeks:

1. **Phase 1** (Weeks 1-2): Python Fundamentals & Advanced Concepts
2. **Phase 2** (Weeks 3-6): FastAPI Mastery
3. **Phase 3** (Weeks 7-10): Database & ORMs
4. **Phase 4** (Weeks 11-13): API Design & Architecture
5. **Phase 5** (Weeks 14-18): Advanced Backend Concepts
6. **Phase 6** (Weeks 19-20): Search & File Storage
7. **Phase 7** (Weeks 21-26): System Design & Scalability
8. **Phase 8** (Weeks 27-29): DevOps & Deployment
9. **Phase 9** (Weeks 30-32): Production Best Practices

## Repository Structure

```
.
├── notes/                              # Learning notes organized by phase and week
│   ├── phase-1-python-fundamentals/
│   │   ├── week-1/
│   │   ├── week-2/
│   │   └── README.md
│   ├── phase-2-fastapi/
│   ├── phase-3-database/
│   ├── phase-4-api-design/
│   ├── phase-5-advanced-concepts/
│   ├── phase-6-search-and-storage/
│   ├── phase-7-system-design/
│   ├── phase-8-devops/
│   ├── phase-9-production/
│   └── cheat-sheets/                   # Quick reference guides
│
├── projects/                           # Mini projects (8 total)
│   ├── 01-cli-data-aggregator/
│   ├── 02-blog-api/
│   ├── 03-ecommerce-database/
│   ├── 04-social-media-api/
│   ├── 05-job-processing-system/
│   ├── 06-content-management/
│   ├── 07-deployment-pipeline/
│   └── 08-enterprise-application/
│
├── exercises/                          # Coding practice exercises
│   ├── python-fundamentals/
│   ├── fastapi/
│   ├── database/
│   └── system-design/
│
├── system-design/                      # System design practice
│   ├── templates/                      # Design document templates
│   ├── solutions/                      # 12+ system design solutions
│   └── practice-log.md
│
├── resources/                          # Curated learning materials
│   ├── books/
│   ├── articles/
│   ├── videos/
│   └── tools/
│
├── snippets/                           # Reusable code snippets
│   ├── auth/
│   ├── database/
│   ├── caching/
│   └── testing/
│
├── templates/                          # Project starter templates
│   ├── fastapi-starter/
│   └── microservice-template/
│
├── diagrams/                           # Architecture diagrams
│   ├── phase-1/
│   ├── phase-2/
│   └── system-designs/
│
├── README.md                           # This file
├── Roadmap.md                          # Complete learning roadmap
└── PROGRESS.md                         # Progress tracking
```

## Technology Stack

### Core Technologies

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL, Redis, MongoDB
- **ORM**: SQLAlchemy 2.0
- **Task Queue**: Celery, RabbitMQ
- **Search**: Elasticsearch
- **Caching**: Redis

### DevOps & Tools

- **Containerization**: Docker
- **Orchestration**: Kubernetes
- **CI/CD**: GitHub Actions
- **Cloud**: AWS / GCP
- **IaC**: Terraform
- **Monitoring**: Prometheus, Grafana
- **Logging**: ELK Stack

## Mini Projects

Each phase includes hands-on projects to reinforce learning:

1. **CLI Data Aggregator** - Async operations, type hints, decorators
2. **Blog API** - FastAPI, JWT auth, WebSockets, testing
3. **E-commerce Database** - Complex schema design, query optimization
4. **Social Media API** - REST, GraphQL, real-time features
5. **Job Processing System** - Celery, message queues, monitoring
6. **Content Management** - Elasticsearch, S3, media processing
7. **Deployment Pipeline** - Docker, Kubernetes, CI/CD
8. **Enterprise Application** - Complete production-ready system

## System Design Practice

Practicing design for 12+ large-scale systems:

- URL Shortener
- Rate Limiter
- Distributed Cache
- Notification Service
- Real-time Chat
- Social Media Feed
- E-commerce Platform
- Video Streaming
- Search Autocomplete
- Ride-sharing Service
- Web Crawler
- Ticket Booking System

## Key Topics Covered

### Backend Fundamentals

- Advanced Python (decorators, async/await, type hints)
- RESTful API design
- GraphQL and gRPC
- WebSockets and real-time communication
- Authentication and authorization (OAuth2, JWT)

### Data Management

- Database design and normalization
- SQL optimization and indexing
- ORM patterns with SQLAlchemy
- NoSQL databases (Redis, MongoDB)
- Database migrations with Alembic

### Performance & Scalability

- Caching strategies (multi-tier, distributed)
- Load balancing and horizontal scaling
- Database sharding and replication
- Message queues and event-driven architecture
- Async workers and background jobs

### System Design

- Capacity estimation
- High-level and detailed design
- CAP theorem and trade-offs
- Microservices architecture
- Distributed systems patterns

### DevOps & Production

- Docker containerization
- Kubernetes orchestration
- CI/CD pipelines
- Infrastructure as Code (Terraform)
- Monitoring, logging, and tracing
- Security best practices

## Learning Resources

### Essential Books

- "Designing Data-Intensive Applications" by Martin Kleppmann
- "System Design Interview" (Vol 1 & 2) by Alex Xu
- "Python Concurrency with asyncio" by Matthew Fowler
- "Building Microservices" by Sam Newman
- "Release It!" by Michael Nygard

### Online Resources

- FastAPI Official Documentation
- Real Python
- System Design Primer (GitHub)
- Hussein Nasser (YouTube - Backend Engineering)
- Tech Dummies Narendra L (System Design)

## Progress Tracking

Track weekly progress in [PROGRESS.md](./PROGRESS.md) with:

- Weekly completion status
- Mini project milestones
- System design practice log
- Hours logged and streaks
- Key learnings and insights

## Getting Started

1. **Review the roadmap**: Read [Roadmap.md](./Roadmap.md) for detailed curriculum
2. **Set up environment**: Install Python 3.11+, Docker, and essential tools
3. **Start Phase 1**: Begin with Python fundamentals refresher
4. **Track progress**: Update [PROGRESS.md](./PROGRESS.md) regularly

## Development Setup

```bash
# Clone the repository
git clone https://github.com/SanjoyPator1/WebDevLearning/tree/backend
cd backend-learn

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (per project)
cd projects/01-cli-data-aggregator
pip install -r requirements.txt
```

## Contributing Notes

This is a personal learning repository, but feel free to:

- Use this structure for your own learning journey
- Suggest improvements via issues
- Share your own learning experiences

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact & Social

- GitHub: [SanjoyPator1](https://github.com/SanjoyPator1)
- LinkedIn: [Sanjoy Pator](https://www.linkedin.com/in/sanjoy-pator-91a41a182/)
- Blog: [Portfolio](https://www.devlopea.com/portfolio/664c69d16fa0291b35450281)

---

**Note**: This is an active learning repository. Content and structure may evolve as I progress through the curriculum.

**Last Updated**: December 2024
