# Hestia AI Firebase Functions

This directory contains the Firebase Cloud Functions for the Hestia AI Parenting Assistant.

## Functions

1. **get_chat**: Handles private chat with the Hestia AI assistant
2. **auto_respond_post**: Automatically responds to community posts
3. **change_user_id_email**: Updates a user's email address

## Deployment

To deploy the functions, you can use the provided deployment script:

```bash
./scripts/deploy_firebase_functions.sh
```

Or manually deploy using the Firebase CLI:

```bash
firebase deploy --only functions
```

## Development

### Prerequisites

- Node.js and npm
- Firebase CLI (`npm install -g firebase-tools`)
- Python 3.12 or later

### Setup

1. Install the Firebase CLI:
   ```bash
   npm install -g firebase-tools
   ```

2. Login to Firebase:
   ```bash
   firebase login
   ```

3. Install Python dependencies:
   ```bash
   cd functions
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

### Testing Locally

You can test the functions locally using the Firebase Emulator:

```bash
firebase emulators:start
```

## Architecture

The functions use the following components:

- **Knowledge Graph Retriever**: Uses Neo4j to retrieve relevant information from the knowledge graph
- **OpenAI API**: Generates responses based on the retrieved information
- **Firestore**: Stores chat messages and community posts/comments

## Configuration

The functions use the following environment variables:

- **OPENAI_API_KEY**: Your OpenAI API key
- **NEO4J_URI**: URI for the Neo4j database
- **NEO4J_USERNAME**: Username for the Neo4j database
- **NEO4J_PASSWORD**: Password for the Neo4j database

These are configured in the Firebase project settings.
