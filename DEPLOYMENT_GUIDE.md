# Hestia Deployment Guide

## Environment Setup

### Prerequisites
- Flutter SDK
- Python 3.8+
- Node.js and npm
- Firebase CLI

### Initial Setup
```bash
# Make scripts executable
chmod +x setup_environment.sh test_local.sh deploy.sh

# Run the setup script
./setup_environment.sh
```

## Project Structure
```
hestia/
├── athena_parent_copilot/     # Flutter app
├── functions/                 # Firebase Functions (Python)
├── hestia-graphrag/          # Python virtual environment for GraphRAG
├── data/                     # Training data
└── test/                     # Test scripts
```

## Virtual Environments

### Firebase Functions
- Location: `functions/venv/`
- Activate: `cd functions && source venv/bin/activate`
- Dependencies: `functions/requirements.txt`

### GraphRAG Module
- Location: `hestia-graphrag/`
- Activate: `cd hestia-graphrag && source bin/activate`
- Used for: AI query processing and knowledge graph operations

## Configuration

### Environment Variables
Update `config.env` with:
- `OPENAI_API_KEY`: Your OpenAI API key
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`: Neo4j database credentials
- Other service credentials as needed

### Firebase Configuration
- Project ID: `athena-parent-copilot`
- Functions region: `us-central1`
- Hosting: Flutter web build

## Development Workflow

### Local Testing
```bash
# Test Firebase Functions locally
./test_local.sh

# Test Flutter app
cd athena_parent_copilot
flutter run -d chrome
```

### Deployment
```bash
# Full deployment (functions + hosting)
./deploy.sh

# Functions only
firebase deploy --only functions

# Hosting only
firebase deploy --only hosting
```

## Available Firebase Functions

1. **get_chat**: Private AI chat functionality
2. **auto_respond_post**: Automatic community post responses
3. **change_user_id_email**: User email management
4. **test_function**: Deployment verification

## Troubleshooting

### Common Issues
1. **Python dependencies**: Ensure correct virtual environment is activated
2. **Firebase authentication**: Run `firebase login` if needed
3. **Flutter build errors**: Run `flutter clean && flutter pub get`
4. **Function deployment**: Check `functions/requirements.txt` for missing dependencies

### Logs
- Firebase Functions: `firebase functions:log`
- Local emulator: Check console output during `firebase emulators:start`