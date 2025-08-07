#!/usr/bin/env python3
"""
WhatsApp Connectivity Test Script

A standalone script to test WhatsApp API connectivity without requiring
database, embeddings, or LLM services. Only tests the WhatsApp API integration.

Usage:
    python test_whatsapp_connectivity.py

Prerequisites:
    - WhatsApp API server must be running (e.g., via docker compose)
    - .env file with WHATSAPP_* configuration
"""

import asyncio
import logging
import sys
from typing import Optional

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseSettings
    from pydantic.config import ConfigDict as SettingsConfigDict

# Import only WhatsApp client components
from src.whatsapp.client import WhatsAppClient
from src.whatsapp.models import SendMessageRequest

# Minimal configuration - only WhatsApp related settings
class TestSettings(BaseSettings):
    whatsapp_host: str = "http://localhost:3000"
    whatsapp_basic_auth_user: Optional[str] = None
    whatsapp_basic_auth_password: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

class WhatsAppConnectivityTester:
    def __init__(self, settings: TestSettings):
        self.settings = settings
        self.client: Optional[WhatsAppClient] = None
        self.test_results = {}
        
    async def setup_client(self):
        """Initialize WhatsApp client with configuration"""
        print(f"🔧 Setting up WhatsApp client...")
        print(f"   Host: {self.settings.whatsapp_host}")
        print(f"   Auth User: {self.settings.whatsapp_basic_auth_user or 'None'}")
        
        self.client = WhatsAppClient(
            base_url=self.settings.whatsapp_host,
            username=self.settings.whatsapp_basic_auth_user,
            password=self.settings.whatsapp_basic_auth_password,
        )
        print("✅ Client initialized")
        
    async def test_basic_connectivity(self):
        """Test if we can reach the WhatsApp API server"""
        print("\n🌐 Testing basic server connectivity...")
        try:
            # Try to get devices - this is a simple endpoint that should work if connected
            if self.client is None:
                raise Exception("Client not initialized")
            response = await self.client.get_devices()
            print(f"✅ Server is reachable")
            print(f"   Response code: {response.code}")
            print(f"   Message: {response.message}")
            self.test_results['connectivity'] = True
            return True
        except Exception as e:
            print(f"❌ Failed to connect to server")
            print(f"   Error: {str(e)}")
            self.test_results['connectivity'] = False
            return False
    
    async def test_device_info(self):
        """Test getting device information"""
        print("\n📱 Testing device information...")
        try:
            if self.client is None:
                raise Exception("Client not initialized")
            devices = await self.client.get_devices()
            if devices.results:
                print(f"✅ Found {len(devices.results)} device(s)")
                for i, device in enumerate(devices.results):
                    print(f"   Device {i+1}: {device.name} ({device.device})")
                
                # Get bot's JID
                my_jid = await self.client.get_my_jid()
                print(f"   Bot JID: {my_jid.normalize_str()}")
                print(f"   Bot Number: {my_jid.user}")
                
                self.test_results['device_info'] = True
                return True
            else:
                print("❌ No devices found - may not be logged in")
                self.test_results['device_info'] = False
                return False
                
        except Exception as e:
            print(f"❌ Failed to get device info")
            print(f"   Error: {str(e)}")
            self.test_results['device_info'] = False
            return False
    
    async def test_group_listing(self):
        """Test listing WhatsApp groups"""
        print("\n👥 Testing group listing...")
        try:
            if self.client is None:
                raise Exception("Client not initialized")
            groups_response = await self.client.get_user_groups()
            
            if groups_response.results and groups_response.results.data:
                groups = groups_response.results.data
                print(f"✅ Found {len(groups)} group(s)")
                
                for i, group in enumerate(groups[:5]):  # Show first 5 groups
                    participants_count = len(group.Participants) if group.Participants else 0
                    admin_count = sum(1 for p in group.Participants if p.IsAdmin) if group.Participants else 0
                    
                    print(f"   Group {i+1}: {group.Name}")
                    print(f"      JID: {group.JID}")
                    print(f"      Topic: {group.Topic[:50]}..." if len(group.Topic) > 50 else f"      Topic: {group.Topic}")
                    print(f"      Participants: {participants_count} ({admin_count} admins)")
                    print(f"      Created: {group.GroupCreated}")
                
                if len(groups) > 5:
                    print(f"   ... and {len(groups) - 5} more groups")
                    
                self.test_results['group_listing'] = True
                return groups
            else:
                print("⚠️  No groups found - bot may not be in any groups")
                self.test_results['group_listing'] = False
                return []
                
        except Exception as e:
            print(f"❌ Failed to list groups")
            print(f"   Error: {str(e)}")
            self.test_results['group_listing'] = False
            return []
    
    async def test_send_message(self, test_groups):
        """Optionally test sending a message"""
        if not test_groups:
            print("\n💬 Skipping message test - no groups available")
            return False
            
        print(f"\n💬 Message sending test...")
        print("   Available groups for testing:")
        for i, group in enumerate(test_groups[:3]):  # Show first 3 groups
            print(f"      {i+1}. {group.Name}")
        
        # Ask user if they want to test message sending
        print("\n   Do you want to test sending a message? This will send a test message to a group.")
        response = input("   Enter 'yes' to continue, or anything else to skip: ").lower().strip()
        
        if response != 'yes':
            print("   Skipping message test")
            self.test_results['message_sending'] = 'skipped'
            return False
        
        # Let user choose group
        print("\n   Which group to send test message to?")
        try:
            choice = int(input(f"   Enter number (1-{min(3, len(test_groups))}): ")) - 1
            if choice < 0 or choice >= min(3, len(test_groups)):
                raise ValueError("Invalid choice")
                
            selected_group = test_groups[choice]
            test_message = "🤖 WhatsApp connectivity test - please ignore this message"
            
            print(f"   Sending test message to: {selected_group.Name}")
            
            send_request = SendMessageRequest(
                phone=selected_group.JID,
                message=test_message
            )
            
            if self.client is None:
                raise Exception("Client not initialized")
            response = await self.client.send_message(send_request)
            print(f"✅ Message sent successfully")
            if response.results:
                print(f"   Message ID: {response.results.message_id}")
                print(f"   Status: {response.results.status}")
            
            self.test_results['message_sending'] = True
            return True
            
        except ValueError:
            print("   Invalid input - skipping message test")
            self.test_results['message_sending'] = 'skipped'
            return False
        except Exception as e:
            print(f"❌ Failed to send message")
            print(f"   Error: {str(e)}")
            self.test_results['message_sending'] = False
            return False
    
    async def generate_report(self):
        """Generate final connectivity report"""
        print("\n" + "="*60)
        print("📊 WHATSAPP CONNECTIVITY TEST REPORT")
        print("="*60)
        
        total_tests = len([k for k in self.test_results.keys() if k != 'message_sending'])
        passed_tests = len([k for k, v in self.test_results.items() if v is True and k != 'message_sending'])
        
        print(f"Overall Status: {passed_tests}/{total_tests} core tests passed")
        print("")
        
        # Test details
        tests = [
            ('connectivity', 'Server Connectivity'),
            ('device_info', 'Device Information'),
            ('group_listing', 'Group Listing'),
        ]
        
        for key, name in tests:
            status = self.test_results.get(key, False)
            icon = "✅" if status else "❌"
            print(f"{icon} {name}: {'PASS' if status else 'FAIL'}")
        
        # Message sending (optional)
        msg_status = self.test_results.get('message_sending', 'not_tested')
        if msg_status == 'skipped':
            print("⏭️  Message Sending: SKIPPED")
        elif msg_status is True:
            print("✅ Message Sending: PASS")
        elif msg_status is False:
            print("❌ Message Sending: FAIL")
        
        print("\n" + "="*60)
        
        if passed_tests == total_tests:
            print("🎉 All core tests passed! WhatsApp connectivity is working properly.")
        else:
            print("⚠️  Some tests failed. Check the errors above for troubleshooting.")
            print("\nCommon issues:")
            print("- Make sure WhatsApp API server is running (docker compose up)")
            print("- Verify .env file has correct WHATSAPP_* settings")
            print("- Check if WhatsApp Web is properly authenticated/logged in")
        
        print("="*60)
    
    async def run_all_tests(self):
        """Run all connectivity tests"""
        print("🚀 Starting WhatsApp Connectivity Tests...")
        print("="*60)
        
        try:
            # Setup
            await self.setup_client()
            
            # Core connectivity tests
            if not await self.test_basic_connectivity():
                print("\n❌ Basic connectivity failed - stopping tests")
                await self.generate_report()
                return
            
            await self.test_device_info()
            test_groups = await self.test_group_listing()
            
            # Optional message test
            await self.test_send_message(test_groups)
            
            # Final report
            await self.generate_report()
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Tests interrupted by user")
        except Exception as e:
            print(f"\n❌ Unexpected error: {str(e)}")
        finally:
            if self.client:
                await self.client.close()
                print("\n🔒 WhatsApp client closed")

async def main():
    """Main entry point"""
    print("WhatsApp Connectivity Test Script")
    print("="*40)
    
    # Load configuration
    try:
        settings = TestSettings()
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        print("Make sure you have a .env file with WHATSAPP_* settings")
        sys.exit(1)
    
    # Configure logging to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Run tests
    tester = WhatsAppConnectivityTester(settings)
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
