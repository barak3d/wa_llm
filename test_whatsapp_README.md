# WhatsApp Connectivity Test Script

A standalone script to test WhatsApp API connectivity without requiring database, embeddings, or LLM services.

## Purpose

This script helps you verify that:
- Your WhatsApp API server is running and accessible
- Authentication credentials are working
- You can list WhatsApp groups
- Basic message sending functionality works (optional)

## Prerequisites

1. **WhatsApp API Server Running**: Make sure your WhatsApp API server is running:
   ```bash
   docker compose up whatsapp-api-server
   # or
   docker compose up
   ```

2. **Environment Configuration**: Create a `.env` file with WhatsApp settings:
   ```env
   WHATSAPP_HOST=http://localhost:3000
   WHATSAPP_BASIC_AUTH_USER=admin
   WHATSAPP_BASIC_AUTH_PASSWORD=admin
   ```

3. **Dependencies**: Install minimal requirements:
   ```bash
   pip install -r test_requirements.txt
   # or if using the full project:
   uv sync --all-extras
   ```

## Usage

Run the test script:
```bash
python test_whatsapp_connectivity.py
```

## What It Tests

### Core Tests (Automatic)
1. **Server Connectivity**: Tests if the WhatsApp API server is reachable
2. **Device Information**: Checks if WhatsApp is logged in and gets device info
3. **Group Listing**: Fetches all groups the bot belongs to

### Optional Test (Interactive)
4. **Message Sending**: Optionally sends a test message to a selected group

## Sample Output

```
🚀 Starting WhatsApp Connectivity Tests...
============================================================
🔧 Setting up WhatsApp client...
   Host: http://localhost:3000
   Auth User: admin
✅ Client initialized

🌐 Testing basic server connectivity...
✅ Server is reachable
   Response code: 200
   Message: Success

📱 Testing device information...
✅ Found 1 device(s)
   Device 1: My Phone (1234567890@s.whatsapp.net)
   Bot JID: 1234567890@s.whatsapp.net
   Bot Number: 1234567890

👥 Testing group listing...
✅ Found 3 group(s)
   Group 1: Test Group
      JID: 1234567890-1234567890@g.us
      Topic: Test group for bot testing
      Participants: 5 (2 admins)
      Created: 2024-01-01 10:00:00

💬 Message sending test...
   Available groups for testing:
      1. Test Group
   
   Do you want to test sending a message? This will send a test message to a group.
   Enter 'yes' to continue, or anything else to skip: no
   Skipping message test

============================================================
📊 WHATSAPP CONNECTIVITY TEST REPORT
============================================================
Overall Status: 3/3 core tests passed

✅ Server Connectivity: PASS
✅ Device Information: PASS
✅ Group Listing: PASS
⏭️  Message Sending: SKIPPED

============================================================
🎉 All core tests passed! WhatsApp connectivity is working properly.
============================================================
```

## Troubleshooting

### Common Issues

1. **Connection Failed**
   ```
   ❌ Failed to connect to server
   ```
   - Check if WhatsApp API server is running: `docker compose ps`
   - Verify WHATSAPP_HOST in .env file
   - Check firewall/network connectivity

2. **Authentication Failed**
   ```
   ❌ Failed to get device info
   ```
   - Check WHATSAPP_BASIC_AUTH_USER and WHATSAPP_BASIC_AUTH_PASSWORD
   - Verify credentials match your WhatsApp API server config

3. **No Devices Found**
   ```
   ❌ No devices found - may not be logged in
   ```
   - WhatsApp Web may not be authenticated
   - Scan QR code or re-authenticate with WhatsApp Web

4. **No Groups Found**
   ```
   ⚠️  No groups found - bot may not be in any groups
   ```
   - Add the bot number to WhatsApp groups
   - Check if groups are properly synced

## What This Script Does NOT Do

- ❌ Start the WhatsApp API server
- ❌ Handle WhatsApp Web QR code scanning
- ❌ Require database connection
- ❌ Use AI/LLM services
- ❌ Test advanced bot features

## Integration with Main App

This script uses the same WhatsApp client code as the main application, so successful tests here indicate that the main app should also be able to connect to WhatsApp.

After running successful tests, you can start the full application:
```bash
docker compose up
# or
python app/main.py
