# GC25 Project Documentation (v2.0)

## Overview

GC25 is a comprehensive system designed for scheduling meetings, generating reports, handling chat functionality, and managing asynchronous updates. 

Recently, the system underwent a major architecture revamp to simplify deployment and improve maintainability. The legacy 5-microservice gRPC architecture has been consolidated into a **modular monolith**. 

## System Architecture

The new system consists of the following core components:

1. **Unified Backend (ackend/)**: A single FastAPI application handling all domains:
   - **Authentication**: JWT-based user authentication and role-based access.
   - **Chat & AI**: Real-time websocket communication powered by LangGraph and Gemini.
   - **Reporting**: PDF generation for organizational health.
   - **Admin Dashboard**: Endpoints for visualizing company mood trends.
2. **Asynchronous Workers (ackend/tasks.py)**: Celery background workers that handle heavy processing, database updates, and email notifications. Scheduled via Celery Beat.
3. **Frontend (opensoft/)**: A Next.js/TypeScript frontend interface for users.
4. **Data Layer**: 
   - **MongoDB** via the Beanie ODM for primary data persistence.
   - **Redis** as a Celery message broker and result backend.

## Fully Dockerized Setup

The entire stack is containerized using docker compose. The setup provisions MongoDB, Redis, the unified API backend, Celery workers, Celery Beat, and the Next.js frontend automatically.

### Quick Start (Execution Instructions)

Run these exact commands in order from the repository root:

1. **Prepare Environment Variables**:
   `ash
   cp .env.example .env
   # Make sure to open .env and fill in your GEMINI_API_KEY and email credentials
   `

2. **Initialize Database and Seed Data**:
   `ash
   # Spin up MongoDB in the background
   docker compose up -d mongodb
   
   # Wait a few seconds for MongoDB to initialize, then run the seeder script
   # (Requires python and motor/beanie to be installed locally, or run it inside the container)
   python seed_db.py
   `

3. **Build and Launch the Stack**:
   `ash
   # Spin up the frontend, backend, workers, and redis
   docker compose up --build
   `

4. **Access the Application**:  
   Open [http://localhost:3000](http://localhost:3000) in your browser.

### Shut down services
`ash
docker compose down
`

## Technology Stack

- **Frontend**: Next.js with TypeScript
- **Backend API**: Python (FastAPI)
- **Task Processing**: Celery & Celery Beat
- **Message Broker**: Redis
- **Database**: MongoDB
- **ODM**: Beanie
- **WebSockets**: Native FastAPI WebSockets
- **AI/LLM**: LangGraph, Gemini 2.0 Flash
- **Containerization**: Docker & Docker Compose
