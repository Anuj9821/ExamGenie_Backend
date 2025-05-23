﻿# ExamGenie Backend

ExamGenie is an intelligent exam paper generation system that helps teachers create customized question papers efficiently. This repository contains the backend API built with Django REST Framework.

## Features

- User authentication and authorization
- Question bank management with file uploads to AWS S3
- AI-powered exam paper generation
- User profile management
- RESTful API endpoints for frontend integration

## Tech Stack

- **Django**: Web framework
- **Django REST Framework**: API development
- **MongoDB**: Database (via PyMongo)
- **AWS S3**: File storage for question banks
- **JWT**: Authentication
- **Python**: Programming language

## Prerequisites

- Python 3.9+
- MongoDB
- AWS Account with S3 access

## Installation

1. Clone the repository:
    ```bash
    git clone git@github.com:Anuj9821/ExamGenie_Backend.git
    cd ExamGenie_Backend

2. Create and activate a virtual environment:
    ```bash
    python -m venv venv

    # On Windows
    venv\Scripts\activate

    # On macOS/Linux
    source venv/bin/activate

3. Install dependencies:
    ```bash
    pip install -r requirements.txt

4. Create a .env file in the project root with the following variables:
    ```bash
    # MongoDB Configuration
    MONGODB_URI=url
    MONGODB_DB=examgenie_database

    # Django Secret Key
    SECRET_KEY=your_django_secret_key

    # Debug Mode
    DEBUG=True

5. Run migrations:
    ```bash
    python manage.py makemigrations
    python manage.py migrate

6. Create a superuser:
    ```bash
    python manage.py createsuperuser

7. Start the development server:
    ```bash
    python manage.py runserver

## API Endpoints
1. Authentication
    ```bash
    POST /api/auth/register/: Register a new user
    POST /api/auth/login/: Login and get access token
    POST /api/auth/refresh/: Refresh access token
    GET /api/auth/me/: Get current user details

2. Question Banks
    ```bash
    POST /api/questions/upload/: Upload a question bank file
    GET /api/questions/: List all question banks
    GET /api/questions/{id}/: Get a specific question bank
    DELETE /api/questions/{id}/: Delete a question bank

3. Papers
    ```bash
    POST /api/papers/generate/: Generate a new exam paper
    GET /api/papers/: List all generated papers
    GET /api/papers/{id}/: Get a specific paper
    DELETE /api/papers/{id}/: Delete a paper

4. Profiles
    ```bash
    GET /api/profiles/: Get user profile
    PUT /api/profiles/: Update user profile