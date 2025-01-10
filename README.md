# Face Recognition Backend API && ReactJs 

## Overview

This project provides a backend for a face recognition application, using **FastAPI**, **Prisma ORM** for PostgreSQL, and **Milvus** for vector database storage and similarity search. **DeepFace** is used for facial recognition and embedding extraction.

## Features

- Employee registration with face embedding storage.
- Visitor registration with face embedding storage.
- Face recognition for employees and visitors.
- Integration with Prisma (PostgreSQL) for structured data storage.
- Integration with Milvus for vector similarity search.
- Preloading of DeepFace model for optimized performance.

## Installation

### Prerequisites

- Python 3.9+
- PostgreSQL
- Milvus
- Node.js (for Prisma migrations)

### Environment Variables

Create a `.env` file with the following variables:

```
DATABASE_URL=postgresql://user:password@localhost:5432/database_name
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

### Dependencies

Install the required Python packages:

```bash
pip install fastapi uvicorn prisma pymilvus deepface Pillow numpy python-dotenv pytz
```

## API Endpoints

### 1. Root Endpoint

**GET /**

**Description:** Test endpoint to verify the server is running.

**Response:**

```json
{"message": "Face App Backend"}
```

### 2. Employee Registration

**POST /register-employee/**

**Description:** Register a new employee with personal details and face embedding.

**Form Data:**

- `name`: Employee name (string)
- `age`: Employee age (integer)
- `gender`: Employee gender (string)
- `photo`: Employee photo (file)
- `designation`: Job designation (string)
- `contactNumber`: Contact number (string)
- `department`: Department (string)
- `description`: Additional description (string)

**Response:**

```json
{"message": "Employee registered successfully."}
```

### 3. Visitor Registration

**POST /register-visitor/**

**Description:** Register a visitor with personal details and face embedding.

**Form Data:**

- `name`: Visitor name (string)
- `age`: Visitor age (integer)
- `gender`: Visitor gender (string)
- `photo`: Visitor photo (file)
- `contact`: Contact number (string)
- `purposeOfVisit`: Purpose of the visit (string)
- `description`: Additional description (string)

**Response:**

```json
{"message": "Visitor registered successfully."}
```

### 4. Recognize Employee

**POST /recognize-employee/**

**Description:** Recognize an employee from a photo.

**Form Data:**

- `photo`: Uploaded photo (file)

**Response:**

If a match is found:

```json
{"name": "John Doe", "similarity": 0.85, "status": "success"}
```

If no match is found:

```json
{"message": "No match found", "status": "failed"}
```

### 5. Recognize Visitor

**POST /recognize-visitor/**

**Description:** Recognize a visitor from a photo.

**Form Data:**

- `photo`: Uploaded photo (file)

**Response:**

If a match is found:

```json
{"name": "Jane Doe", "similarity": 0.90, "status": "success"}
```

If no match is found:

```json
{"message": "No match found", "status": "failed"}
```

## Backend Architecture

### 1. FastAPI

- Framework for building the backend.
- Provides routing, middleware, and dependency injection.

### 2. Prisma ORM

- Manages structured data in PostgreSQL.
- Used to store:
  - Employee details
  - Visitor details

### 3. Milvus

- Vector database for storing face embeddings.
- Used for similarity searches.

### 4. DeepFace

- Extracts facial embeddings.
- **Model used:** VGG-Face.

## Database Structure

### PostgreSQL Tables

#### Employees Table

| Column         | Type   | Description          |
|----------------|--------|----------------------|
| `id`           | UUID   | Primary key          |
| `name`         | String | Employee name        |
| `age`          | Integer| Employee age         |
| `gender`       | String | Employee gender      |
| `photoBase64`  | Text   | Base64-encoded photo |
| `designation`  | String | Job designation      |
| `contactNumber`| String | Contact number       |
| `department`   | String | Department           |
| `description`  | String | Additional description|

#### Visitors Table

| Column          | Type   | Description          |
|-----------------|--------|----------------------|
| `id`            | UUID   | Primary key          |
| `name`          | String | Visitor name         |
| `age`           | Integer| Visitor age          |
| `gender`        | String | Visitor gender       |
| `photoBase64`   | Text   | Base64-encoded photo |
| `contact`       | String | Contact number       |
| `purposeOfVisit`| String | Purpose of the visit |
| `description`   | String | Additional description|

## Key Functions

1. **`extract_face_embedding(photo_bytes: bytes)`**
   - Extracts face embedding from photo bytes using DeepFace.
   - Returns a 4096-dimensional embedding.

2. **`save_to_milvus(collection_name, name, embedding)`**
   - Saves normalized embeddings to Milvus.

3. **`search_in_milvus(collection_name, query_embedding, threshold=0.6)`**
   - Searches Milvus for a match to the query embedding.
   - Returns the best match if similarity exceeds the threshold.

4. **`save_to_prisma(name, age, gender, photo_base64, table, additional_data)`**
   - Saves user details to PostgreSQL using Prisma ORM.

## Running the Application

### Run Locally

```bash
uvicorn main:app --reload
```

### Access the API

- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Future Enhancements

- Implement rate limiting for API endpoints.
- Add authentication and authorization.
- Use GPU acceleration for faster embedding extraction.
- Integrate more facial recognition models.


# Screenshots
## Backend : FastAPI
![image](https://github.com/user-attachments/assets/12862f2c-7968-459b-9be9-49c1c8ebde38)

## Milvus DB : using Attu for UI
![image](https://github.com/user-attachments/assets/6462c683-bbe5-4629-9d33-995653400419)

## Primsa - Using Postgres (ORM with Prisma Python Client)
![image](https://github.com/user-attachments/assets/f36fd55b-29f9-451c-b9af-f38f6f4185f8)



# FrontEnd using React JS
## Landing Page
![image](https://github.com/user-attachments/assets/c0f6985a-3434-4525-b96e-624303e2cf0e)

## Main Dashboard
![image](https://github.com/user-attachments/assets/c4274325-7dc0-4970-a828-963479b7302e)

## Check In interface : Dashboard For checkIn (Visitor / Employee) : Face recognition
![image](https://github.com/user-attachments/assets/5a35c84c-3de3-4889-80f0-86ad9f29307b)

## Custom Error-Page for handling unauthorized requests
![image](https://github.com/user-attachments/assets/dfbc3a0a-0a45-490c-9aee-9586eb90c65a)

## Face recognition Working
![image](https://github.com/user-attachments/assets/eaad9a27-8a57-47fe-8ef3-cbcb819432b4)

## Self Check-In model for visitor/employee
Employee
![image](https://github.com/user-attachments/assets/faa08b9b-37f4-4e7b-bd2d-afdd52458f2e)

Visitor
![image](https://github.com/user-attachments/assets/4385bac8-06d9-4ebd-8043-6933235bb8f7)




# Scope for Improvements
1) Rate limiter for requests
2) Authentication
3) Session using redux and redux tools (setting up store and auth-sessions)
4) Form validations
5) Pydantics models for Proper models











